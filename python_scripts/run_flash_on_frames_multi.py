#!/usr/bin/env python3
"""
Multi-person gaze tracking for FLASH-TV frames

Usage:
    python run_flash_on_frames_multi.py <family_id> <frames_folder> <faces_folder> [options]

Example:
    # Basic usage - will auto-find log files
    python run_flash_on_frames_multi.py 123 /path/to/123_frames /path/to/123_faces
    
    # Specify a specific log file (recommended)
    python run_flash_on_frames_multi.py 123 \\
        /media/flashsys007/FLASH_SSD/123_frames \\
        /home/flashsys007/data/123_faces \\
        --log_file 123_flash_log_rot.txt \\
        --output_dir /home/flashsys007/results
    
    # Use existing FLASH log for accurate timestamps
    python run_flash_on_frames_multi.py 111 frames/ faces/ --log_file 111_flash_log_rot.txt
    
    # Generate synthetic timestamps if no log available
    python run_flash_on_frames_multi.py 123 frames/ faces/ --start_time "09:45:00"

Arguments:
    family_id       : Family ID (e.g., 123)
    frames_folder   : Path to folder containing frame images (000001.png, 000002.png, etc.)
    faces_folder    : Path to folder containing face gallery images for verification

Options:
    --output_dir    : Output directory for results (default: auto-generated)
    --log_file      : Path to timestamp log file (optional, for frame timing)
    --start_time    : Starting timestamp (format: "YYYY-MM-DD HH:MM:SS" or "HH:MM:SS")
    --save_images   : Save visualization images with gaze arrows
    --no_save_images: Don't save visualization images
    --display       : Show frames in real-time window during processing
"""

import os
import argparse
import glob

# import queue libraries
import subprocess
import sys
import threading as th

# time libs
import time
import traceback
from datetime import datetime, timedelta
from queue import Queue
import math

# computer vision libs
import cv2
import numpy as np

# custom libs
from flash_main import FLASHtv
from utils.flash_runtime_utils import cam_id, check_face_presence, correct_rotation, make_directories, write_log_file
from utils.rotate_frame import rotate_frame
from utils.visualizer import draw_gz, draw_rect_ver

# Parse command line arguments
parser = argparse.ArgumentParser(description="Multi-person gaze tracking on FLASH-TV frames")
parser.add_argument("family_id", type=str, help="Family ID (e.g., 123)")
parser.add_argument("frames_folder", type=str, help="Path to folder containing frame images")
parser.add_argument("faces_folder", type=str, help="Path to folder containing face gallery images")
parser.add_argument("--output_dir", type=str, default=None, help="Output directory for results (default: auto-generated)")
parser.add_argument("--log_file", type=str, default=None, help="Path to timestamp log file (optional)")
parser.add_argument("--start_time", type=str, default=None, help='Starting timestamp (format: "YYYY-MM-DD HH:MM:SS" or "HH:MM:SS" for today)')
parser.add_argument("--end_time", type=str, default=None, help='Ending timestamp for calculating frame rate (format: same as start_time)')
parser.add_argument("--fps", type=float, default=30.0, help='Frames per second (default: 30.0, auto-calculated if end_time provided)')
parser.add_argument("--save_images", action="store_true", help="Save visualization images")
parser.add_argument("--no_save_images", dest="save_images", action="store_false")
parser.add_argument("--display", action="store_true", help="Display frames in real-time window")
parser.set_defaults(save_images=True, display=False)

args = parser.parse_args()

# super variables
write_image_data = args.save_images
rotate_to_find_tc = False  # Disabled for multi-person tracking
famid = str(args.family_id)

# Identity mapping for readable output
# Note: This matches the order in face_verification.py: ["tc", "sib", "parent", "extra"]
IDENTITY_NAMES = {
    0: "tc",  # Target child
    1: "sib",  # Sibling
    2: "parent",  # Parent
    3: "extra",  # Extra/poster face (not tracked for gaze)
}

# Set paths from arguments
frames_read_path = os.path.abspath(args.frames_folder)
faces_gallery_path = os.path.abspath(args.faces_folder)

# Validate that paths exist
if not os.path.exists(frames_read_path):
    print(f"Error: Frames folder does not exist: {frames_read_path}")
    sys.exit(1)

if not os.path.exists(faces_gallery_path):
    print(f"Error: Faces gallery folder does not exist: {faces_gallery_path}")
    sys.exit(1)

# Handle log file - check multiple possible sources
log_found = False
q = []

# Priority 1: User-provided log file (highest priority)
if args.log_file:
    fname_log_read = os.path.abspath(args.log_file)
    if os.path.exists(fname_log_read):
        print(f"Using user-specified log file: {fname_log_read}")
        log_found = True
    else:
        print(f"ERROR: Specified log file not found: {fname_log_read}")
        sys.exit(1)  # Exit if user explicitly specified a file that doesn't exist

# Priority 2: Look for existing FLASH log files from single-gaze processing
if not log_found:
    # Check for log files in current directory and common locations
    # Prioritize rot/reg logs as they start when gaze detection actually begins
    possible_log_locations = [
        f"{famid}_flash_log_rot.txt",  # Rotation-corrected log (preferred - starts with actual detection)
        f"{famid}_flash_log_reg.txt",  # Secondary model log (also starts with actual detection)
        f"{famid}_flash_log.txt",  # Main log file (may have extra frames at beginning)
        f"./{famid}_flash_log.txt",
        f"/home/flashsys007/code_test/flash_old_logs/txt_logs/{famid}_flash_log_sub_sort.txt"
    ]
    
    for log_path in possible_log_locations:
        if os.path.exists(log_path):
            fname_log_read = log_path
            print(f"Found existing FLASH log file: {fname_log_read}")
            log_found = True
            break

# Read and parse FLASH log file if found
if log_found:
    with open(fname_log_read, "r") as a:
        lines = a.readlines()
    
    # Parse FLASH log format: timestamp frameNum numFaces tcPresent ...
    for line in lines:
        parts = line.strip().split()
        if len(parts) >= 3:  # Need at least date, time, frameNum
            try:
                date_str = parts[0]
                time_str = parts[1]
                frame_num = parts[2]  # Keep as string with leading zeros
                
                # Reconstruct the timestamp line for queue
                q.append(f"{date_str} {time_str} {frame_num}")
            except (ValueError, IndexError):
                continue  # Skip malformed lines
    
    if q:
        print(f"Loaded {len(q)} timestamps from existing FLASH log")
        q = q[::-1]  # Reverse to match expected order (process oldest first)
    else:
        print("Warning: Log file found but no valid timestamps extracted")
        log_found = False

if not log_found:
    print("No existing FLASH log found. Will generate timestamps.")

# Only generate synthetic timestamps if no log was found
if not q:
    # If no log file, create entries from frame files
    frame_files = sorted(glob.glob(os.path.join(frames_read_path, "*.png")))
    if not frame_files:
        frame_files = sorted(glob.glob(os.path.join(frames_read_path, "*.jpg")))

    q = []
    
    # Parse start time if provided
    if args.start_time:
        try:
            # Try full datetime format first
            if ' ' in args.start_time:
                base_time = datetime.strptime(args.start_time, "%Y-%m-%d %H:%M:%S")
            else:
                # If only time provided, use today's date
                time_only = datetime.strptime(args.start_time, "%H:%M:%S").time()
                base_time = datetime.combine(datetime.now().date(), time_only)
            print(f"Using specified start time: {base_time}")
        except ValueError:
            print(f"Warning: Invalid time format '{args.start_time}'. Using current time.")
            print("Expected format: 'YYYY-MM-DD HH:MM:SS' or 'HH:MM:SS'")
            base_time = datetime.now()
    else:
        base_time = datetime.now()
        print(f"Using current time as start: {base_time}")
    
    # Extract all frame numbers first to understand the pattern
    frame_numbers = []
    for frame_file in frame_files:
        frame_name = os.path.basename(frame_file)
        try:
            frame_num = int(os.path.splitext(frame_name)[0])
            frame_numbers.append(frame_num)
        except:
            continue
    
    if not frame_numbers:
        print("Error: Could not extract frame numbers from files")
        sys.exit(1)
    
    # Get the first and last frame numbers
    first_frame_num = frame_numbers[0]
    last_frame_num = frame_numbers[-1]
    
    # Calculate actual frame rate if end_time is provided
    seconds_per_frame = 1.0 / args.fps  # Default to provided fps
    
    if args.end_time and args.start_time:
        try:
            # Parse end time
            if ' ' in args.end_time:
                end_time = datetime.strptime(args.end_time, "%Y-%m-%d %H:%M:%S")
            else:
                time_only = datetime.strptime(args.end_time, "%H:%M:%S").time()
                end_time = datetime.combine(base_time.date(), time_only)
            
            # Calculate actual duration and frame rate
            actual_duration = (end_time - base_time).total_seconds()
            frame_span = last_frame_num - first_frame_num
            
            if frame_span > 0 and actual_duration > 0:
                seconds_per_frame = actual_duration / frame_span
                calculated_fps = 1.0 / seconds_per_frame
                print(f"Auto-calculated frame rate: {calculated_fps:.2f} fps")
                print(f"Actual duration: {actual_duration:.1f} seconds ({actual_duration/60:.1f} minutes)")
            else:
                print(f"Warning: Could not calculate frame rate. Using default {args.fps} fps")
        except ValueError as e:
            print(f"Warning: Could not parse end time. Using default {args.fps} fps")
    else:
        print(f"Using frame rate: {args.fps} fps")
    
    # Process frames in pairs (since they come as pairs like 14,15 then 73,74)
    # We'll use every other frame as the primary frame for the pair
    for i in range(0, len(frame_numbers) - 1, 2):  # Step by 2 to handle pairs
        frame_num = frame_numbers[i]
        next_frame_num = frame_numbers[i + 1] if i + 1 < len(frame_numbers) else frame_num + 1
        
        # Calculate actual time offset based on frame number
        # This ensures gaps in frame numbers translate to gaps in time
        frame_offset = frame_num - first_frame_num
        timestamp = (base_time + timedelta(seconds=frame_offset * seconds_per_frame)).strftime("%Y-%m-%d %H:%M:%S.%f")
        
        # Store timestamp with the first frame of the pair
        q.append(f"{timestamp} {frame_num}")
    
    q = q[::-1]  # Reverse to match expected order
    
    # Calculate expected duration based on actual frame numbers and rate
    if len(frame_numbers) > 1:
        total_frame_span = last_frame_num - first_frame_num
        duration_seconds = total_frame_span * seconds_per_frame
        duration_minutes = duration_seconds / 60
        print(f"Created queue with {len(q)} frame pairs to process")
        print(f"Frame range: {first_frame_num} to {last_frame_num} (span of {total_frame_span} frames)")
        print(f"Expected duration: {duration_minutes:.1f} minutes ({duration_seconds:.1f} seconds)")
        print(f"Processing {len(q)} pairs from {len(frame_files)} total files")

# Set output paths
if args.output_dir:
    save_path = os.path.abspath(args.output_dir)
else:
    save_path = "/home/" + os.getlogin() + "/code_test/data"

# Create output directory (only for test results, not frames)
frames_save_path = os.path.join(save_path, str(famid) + "_test_res_multi")
if not os.path.exists(frames_save_path):
    os.makedirs(frames_save_path, exist_ok=True)


tmp_fname = str(datetime.now().strftime("%Y-%m-%d %H-%M-%S"))
tmp_fname = "_".join(tmp_fname.split(" "))

log_path = os.path.join(save_path, str(famid) + "_flash_log_multi_" + tmp_fname + ".txt")
log_path_detailed = os.path.join(save_path, str(famid) + "_flash_log_multi_detailed_" + tmp_fname + ".txt")

num_identities = 4


# Get actual username even when running as root
def get_flash_username():
    # Try SUDO_USER first (set when using sudo)
    if "SUDO_USER" in os.environ:
        return os.environ["SUDO_USER"]

    # Try to extract from existing hardcoded paths
    import re

    try:
        # Extract from the hardcoded path pattern
        match = re.search(r"/home/(flashsys\d+)/", frames_read_path)
        if match:
            return match.group(1)
    except:
        pass

    # Fallback: try to detect from /home directory
    try:
        home_dirs = [d for d in os.listdir("/home") if d.startswith("flashsys")]
        if home_dirs:
            return home_dirs[0]  # Use first match
    except:
        pass

    # Ultimate fallback
    return "flashsys"


def write_multi_log_file(log_path, log_lines):
    """Write log file for multi-person gaze tracking using standard FLASH-TV format."""
    # Use the standard write_log_file from utils which uses spaces as separator
    write_log_file(log_path, log_lines)


username = get_flash_username()
# Use the faces_gallery_path provided as argument
flash_tv = FLASHtv(
    username,
    family_id=str(famid),
    num_identities=num_identities,
    data_path=os.path.dirname(faces_gallery_path),
    frame_res_hw=None,
    output_res_hw=None,
)

frame_counter = 1
log_file = [log_path, frame_counter]

frame_counter = log_file[1]
log_path = log_file[0]
face_seen_last_time = datetime.now()

# PROCESS the QUEUE
batch_count = 0
time_batch_start = time.time()
batch_write = True

log_lines = []
log_lines_detailed = []

print("Starting multi-person gaze tracking for family:", famid)
print("Processing frames from:", frames_read_path)
print("Saving results to:", frames_save_path)
print(f"Total frames to process: {len(q)}")
print("-" * 60)

total_frames = len(q)
processed_frames = 0

while True:
    if (batch_count + 1) % 100 == 0:  # to capture the time for frame capture
        if batch_write:
            print("############################################################")
            print("Time for processing 100 batches: ", time.time() - time_batch_start)
            print("############################################################")
            time_batch_start = time.time()
        batch_write = False

    for idx in range(num_identities):
        time_diff = datetime.now() - flash_tv.fv.gal_updated_time[idx]
        if time_diff.total_seconds() >= 150.0:
            flash_tv.fv.gal_update[idx] = True

    if len(q) > 0:
        data_line = q.pop()
        data_line = data_line.split(" ")
        datetime_ = data_line[0] + " " + data_line[1]
        time_stamp = datetime.strptime(datetime_, "%Y-%m-%d %H:%M:%S.%f")
        frame_num = int(data_line[2])

        imgv1_1 = cv2.imread(os.path.join(frames_read_path, str(frame_num).zfill(6) + ".png"))
        imgv1_2 = cv2.imread(os.path.join(frames_read_path, str(frame_num + 1).zfill(6) + ".png"))

        if imgv1_1 is None or imgv1_2 is None:
            print(f"Warning: Could not read frame {frame_num} or {frame_num + 1}, skipping...")
            continue

        batch7_list = [[imgv1_1, frame_num, time_stamp] for i in range(7)]
        batch7_list[4][0] = imgv1_2

        batch_count += 1
        batch_write = True
        processed_frames += 1

        # Show progress every 10 frames
        if processed_frames % 10 == 0:
            print(f"Progress: {processed_frames}/{total_frames} frames processed ({100 * processed_frames / total_frames:.1f}%)")

        frame_1080p_ls = [b[0] for b in batch7_list]
        frame_counts = [b[1] for b in batch7_list]
        frame_stamps = [b[2] for b in batch7_list]

        frame_counter = frame_counts[-1]
        tdet = time.time()

        frame_1080p_ls = [cv2.cvtColor(img1080, cv2.COLOR_BGR2RGB) for img1080 in frame_1080p_ls]
        frame_608p_ls = [cv2.resize(img1080, (608, 342)) for img1080 in frame_1080p_ls]

        frame_1080p_ls = [frame_1080p_ls[3], frame_1080p_ls[4]]  # analyze only two images
        frame_608p_ls = [frame_608p_ls[3], frame_608p_ls[4]]

        timestamp = frame_stamps[3]

        # Detect faces in frames
        frame_bbox_ls = [flash_tv.run_detector(img[:, :, ::-1]) for img in frame_1080p_ls]

        if any(frame_bbox_ls):
            face_seen_last_time = datetime.now()

            # Run face verification
            frame_bbox_ls = [flash_tv.run_verification(img[:, :, ::-1], bbox_ls) for img, bbox_ls in zip(frame_1080p_ls, frame_bbox_ls)]

            # Run multi-person gaze estimation
            persons_gaze_results = flash_tv.run_multi_gaze(frame_1080p_ls, frame_bbox_ls)

            # Count total UNIQUE faces detected (not duplicates across frames)
            # Since we process 2 frames, we should count unique faces, not sum
            # Use the frame with more faces as the count (typically they're similar)
            total_faces = max(len(bbox_ls) for bbox_ls in frame_bbox_ls) if frame_bbox_ls else 0

            # Process results for each person
            print(f"\nFrame {frame_counts[3]} at {timestamp}")
            print(f"Total faces detected: {total_faces}")
            print("-" * 40)

            # Track if we have target child (for proper tag assignment)
            tc_present = 0 in persons_gaze_results and persons_gaze_results[0]["present"]

            # Process ALL family members with qualified tags
            for person_id in range(3):  # tc=0, sib=1, parent=2
                person_name = IDENTITY_NAMES.get(person_id, f"person{person_id}")

                if person_id in persons_gaze_results and persons_gaze_results[person_id]["present"]:
                    result = persons_gaze_results[person_id]
                    gaze_data = result["gaze_data"]
                    bbox = result["bboxes"][0]

                    # Extract gaze values
                    o1, e1, o2, e2 = gaze_data
                    if o1.shape[1] > 2:
                        gaze_vals1 = list(o1[0])
                    else:
                        gaze_vals1 = list(o1[0]) + [e1[0][0]]

                    if o2.shape[1] > 2:
                        gaze_vals2 = list(o2[0])
                    else:
                        gaze_vals2 = list(o2[0]) + [e2[0][0]]

                    # Get position
                    pos = [bbox["top"], bbox["left"], bbox["bottom"], bbox["right"]]
                    angle = bbox["angle"]

                    # Correct rotation if needed
                    gaze_vals1_rot = correct_rotation(gaze_vals1, angle) if abs(angle) >= 30 else gaze_vals1

                    print(f"  {person_name}: Gaze detected - Pitch: {gaze_vals1[0]:.3f}, Yaw: {gaze_vals1[1]:.3f}, Conf: {gaze_vals1[2]:.3f}")

                    # Use qualified tags for ALL members including tc
                    tag = f"Gaze-det-{person_name}"
                    log_line = [timestamp, str(frame_counts[3]).zfill(6), total_faces, 1] + gaze_vals1 + [angle] + pos + [tag]
                    log_lines.append(log_line)

                    # Also create rotated version for detailed log
                    log_line_rot = (
                        [timestamp, str(frame_counts[3]).zfill(6), total_faces, 1] + gaze_vals1_rot + [angle] + pos + [f"Gaze-det-{person_name}-rot"]
                    )
                    log_lines_detailed.append(log_line_rot)

                    # Model 2 version if it's tc
                    if person_id == 0:
                        log_line_reg = (
                            [timestamp, str(frame_counts[3]).zfill(6), total_faces, 1] + gaze_vals2 + [angle] + pos + [f"Gaze-det-{person_name}-m2"]
                        )
                        log_lines_detailed.append(log_line_reg)
                else:
                    # Person not detected but faces exist - use qualified "Gaze-no-det" tag
                    print(f"  {person_name}: Not detected")
                    tag = f"Gaze-no-det-{person_name}"
                    log_line = [timestamp, str(frame_counts[3]).zfill(6), total_faces, 0, None, None, None, None, None, None, None, None, tag]
                    log_lines.append(log_line)

            # Visualization (if enabled)
            if write_image_data:
                save_path_img = os.path.join(frames_save_path, str(frame_counts[3]).zfill(6) + ".png")

                # Convert to BGR for OpenCV and resize
                img_vis = frame_1080p_ls[0][:, :, ::-1].copy()
                img_vis = cv2.resize(img_vis, (854, 480))

                # Draw gaze arrows for each person using the standard formula from draw_gz
                for person_id, result in persons_gaze_results.items():
                    # Skip poster face (identity 3)
                    if person_id == 3:
                        continue

                    if result["present"]:
                        person_name = IDENTITY_NAMES.get(person_id, f"person{person_id}")
                        bbox = result["bboxes"][0]
                        gaze_data = result["gaze_data"]
                        o1 = gaze_data[0]  # numpy array with gaze angles

                        # Extract gaze angles
                        s0 = o1[0, 0]  # pitch
                        s1 = o1[0, 1]  # yaw

                        # Scale bounding box coordinates to output resolution
                        scale_x = 854 / 608.0
                        scale_y = 480 / 342.0

                        # Calculate center point in scaled coordinates
                        sx = (bbox["left"] + bbox["right"]) / 2 * scale_x
                        sy = (bbox["top"] + bbox["bottom"]) / 2 * scale_y

                        # Use the same gaze arrow calculation as draw_gz
                        x = -40 * math.cos(s1) * math.sin(s0)
                        y = -40 * math.sin(s1)

                        start = (int(sx), int(sy))
                        end = (int(sx + x), int(sy + y))

                        # Person-specific color
                        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)]
                        color = colors[person_id % 4]

                        # Draw gaze arrow using standard parameters
                        cv2.arrowedLine(img_vis, start, end, color, 3, tipLength=0.5)

                        # Draw bounding box
                        left = int(bbox["left"] * scale_x)
                        top = int(bbox["top"] * scale_y)
                        right = int(bbox["right"] * scale_x)
                        bottom = int(bbox["bottom"] * scale_y)

                        cv2.rectangle(img_vis, (left, top), (right, bottom), color, 2)

                        # Add person label
                        cv2.putText(img_vis, person_name, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

                        # Add confidence score if available
                        # Check if confidence value exists (3rd element)
                        if o1.shape[1] > 2:
                            confidence = o1[0, 2]
                            conf_text = f"Conf: {confidence:.2f}"
                            cv2.putText(img_vis, conf_text, (left, bottom + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

                # Save the visualization
                if write_image_data:
                    cv2.imwrite(save_path_img, img_vis)

                # Display in real-time if requested
                if args.display:
                    cv2.imshow("Multi-Person Gaze Tracking", img_vis)
                    # Wait 1ms and check for 'q' key to quit
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord("q"):
                        print("\nDisplay window closed by user")
                        q = []  # Clear queue to stop processing
                        break

        else:
            print(f"\nFrame {frame_counts[3]} at {timestamp}")
            print("No faces detected")

            # Create standard log line for no faces detected
            # [timestamp, frameNum, num_faces, person_present, phi, theta, sigma, rotation, top, left, bottom, right, tag]
            tag = "No-face-detected"
            log_line = [timestamp, str(frame_counts[3]).zfill(6), 0, 0, None, None, None, None, None, None, None, None, tag]
            log_lines.append(log_line)

        # Write logs periodically
        if len(log_lines) >= 5:
            write_multi_log_file(log_path, log_lines)
            write_multi_log_file(log_path_detailed, log_lines_detailed)
            log_lines = []
            log_lines_detailed = []
    else:
        # Queue is empty, check if we should continue
        if len(q) == 0:
            print("\nFinished processing all frames in queue")
        break

# Write remaining logs
if log_lines:
    write_multi_log_file(log_path, log_lines)
if log_lines_detailed:
    write_multi_log_file(log_path_detailed, log_lines_detailed)

# Clean up display window if it was open
if args.display:
    cv2.destroyAllWindows()

print("\n" + "=" * 60)
print("Processing complete!")
print(f"Summary log: {log_path}")
print(f"Detailed log: {log_path_detailed}")

if write_image_data:
    print(f"Visualizations: {frames_save_path}/")

    # Generate video from output frames
    print("\nGenerating video from output frames...")

    # Get list of output images
    output_images = sorted(glob.glob(os.path.join(frames_save_path, "*.png")))

    if output_images:
        # Output video path
        video_path = os.path.join(save_path, f"{famid}_gaze_tracking_multi.mp4")

        # Method 1: Using ffmpeg (H.264 compatible with Windows Media Player)
        try:
            # Build ffmpeg command for Windows-compatible H.264
            ffmpeg_cmd = [
                "ffmpeg",
                "-y",  # Overwrite output
                "-framerate",
                "30",  # 30 fps
                "-pattern_type",
                "glob",
                "-i",
                f"{frames_save_path}/*.png",
                "-c:v",
                "libx264",  # H.264 codec
                "-crf",
                "18",  # High quality (visually lossless)
                "-preset",
                "medium",  # Balanced speed/compression
                "-pix_fmt",
                "yuv420p",  # Windows Media Player compatible pixel format
                "-movflags",
                "+faststart",  # Enable streaming/quick playback
                video_path,
            ]

            print(f"Running: {' '.join(ffmpeg_cmd)}")
            result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)

            if result.returncode == 0:
                print(f"Video saved successfully: {video_path}")
                # Get video file size
                video_size = os.path.getsize(video_path) / (1024 * 1024)  # Convert to MB
                print(f"Video size: {video_size:.2f} MB")
            else:
                print(f"FFmpeg failed: {result.stderr}")
                print("Falling back to OpenCV method...")
                raise Exception("FFmpeg failed")

        except Exception as e:
            # Method 2: Fallback to OpenCV (if ffmpeg not available)
            print("Using OpenCV to create video...")

            # Read first image to get dimensions
            first_img = cv2.imread(output_images[0])
            height, width, layers = first_img.shape

            # Define codec and create VideoWriter - using lossless codec
            # Try different codecs in order of preference
            codecs_to_try = [
                ("mp4v", ".mp4"),  # MPEG-4
                ("MJPG", ".avi"),  # Motion JPEG (good quality)
                ("XVID", ".avi"),  # Xvid
            ]

            video_written = False
            for codec_str, ext in codecs_to_try:
                try:
                    video_path = os.path.join(save_path, f"{famid}_gaze_tracking_multi{ext}")
                    fourcc = cv2.VideoWriter_fourcc(*codec_str)
                    video_writer = cv2.VideoWriter(video_path, fourcc, 30.0, (width, height))

                    if video_writer.isOpened():
                        # Write frames to video
                        for i, img_path in enumerate(output_images):
                            if i % 100 == 0:
                                print(f"  Adding frame {i}/{len(output_images)}...")
                            img = cv2.imread(img_path)
                            video_writer.write(img)

                        video_writer.release()
                        video_written = True
                        print(f"Video saved successfully: {video_path}")
                        video_size = os.path.getsize(video_path) / (1024 * 1024)
                        print(f"Video size: {video_size:.2f} MB")
                        break
                except Exception as codec_error:
                    print(f"  Codec {codec_str} failed: {codec_error}")
                    continue

            if not video_written:
                print("Warning: Could not create video with OpenCV")
                print("You can manually create a video using:")
                print(
                    f"  ffmpeg -framerate 30 -pattern_type glob -i '{frames_save_path}/*.png' -c:v libx264 -crf 18 -preset medium -pix_fmt yuv420p -movflags +faststart output.mp4"
                )
    else:
        print("No output images found to create video")
