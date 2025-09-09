#!/usr/bin/env python3
"""
Multi-person gaze tracking for FLASH-TV frames

Usage:
    python run_flash_on_frames_multi.py <family_id> <frames_folder> <faces_folder> [options]

Example:
    python run_flash_on_frames_multi.py 123 /path/to/123_frames /path/to/123_faces
    
    python run_flash_on_frames_multi.py 123 \\
        /media/flashsys007/FLASH_SSD/123_frames \\
        /home/flashsys007/data/123_faces \\
        --output_dir /home/flashsys007/results \\
        --log_file /path/to/timestamp_log.txt \\
        --save_images

Arguments:
    family_id       : Family ID (e.g., 123)
    frames_folder   : Path to folder containing frame images (000001.png, 000002.png, etc.)
    faces_folder    : Path to folder containing face gallery images for verification

Options:
    --output_dir    : Output directory for results (default: auto-generated)
    --log_file      : Path to timestamp log file (optional, for frame timing)
    --save_images   : Save visualization images with gaze arrows
    --no_save_images: Don't save visualization images
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
parser = argparse.ArgumentParser(description='Multi-person gaze tracking on FLASH-TV frames')
parser.add_argument('family_id', type=str, help='Family ID (e.g., 123)')
parser.add_argument('frames_folder', type=str, help='Path to folder containing frame images')
parser.add_argument('faces_folder', type=str, help='Path to folder containing face gallery images')
parser.add_argument('--output_dir', type=str, default=None, help='Output directory for results (default: auto-generated)')
parser.add_argument('--log_file', type=str, default=None, help='Path to timestamp log file (optional)')
parser.add_argument('--save_images', action='store_true', help='Save visualization images')
parser.add_argument('--no_save_images', dest='save_images', action='store_false')
parser.add_argument('--display', action='store_true', help='Display frames in real-time window')
parser.set_defaults(save_images=True, display=False)

args = parser.parse_args()

# super variables
write_image_data = args.save_images
rotate_to_find_tc = False  # Disabled for multi-person tracking
famid = str(args.family_id)

# Identity mapping for readable output
# Note: This matches the order in face_verification.py: ["tc", "sib", "parent", "extra"]
IDENTITY_NAMES = {
    0: "tc",      # Target child
    1: "sib",     # Sibling
    2: "parent",  # Parent
    3: "extra"    # Extra/poster face (not tracked for gaze)
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

# Handle log file - either use provided or try to find one
if args.log_file:
    fname_log_read = os.path.abspath(args.log_file)
    if not os.path.exists(fname_log_read):
        print(f"Warning: Log file not found: {fname_log_read}")
        print("Will process frames in alphabetical order without timestamps")
        q = []
else:
    # Try to find a log file in standard location
    fname_log_read = f"/home/flashsys007/code_test/flash_old_logs/txt_logs/{famid}_flash_log_sub_sort.txt"
    if os.path.exists(fname_log_read):
        print(f"Using log file: {fname_log_read}")
    else:
        print("No log file provided or found. Processing frames in alphabetical order.")
        q = []

# Read log file if it exists
if 'fname_log_read' in locals() and os.path.exists(fname_log_read):
    with open(fname_log_read, "r") as a:
        q = a.readlines()
        q = [line.strip() for line in q]
        q = q[::-1]
else:
    # If no log file, create entries from frame files
    frame_files = sorted(glob.glob(os.path.join(frames_read_path, "*.png")))
    if not frame_files:
        frame_files = sorted(glob.glob(os.path.join(frames_read_path, "*.jpg")))
    
    q = []
    base_time = datetime.now()
    for i in range(len(frame_files) - 1):  # Skip last frame since we need pairs
        # Extract frame number from filename (assuming format like 000001.png)
        frame_name = os.path.basename(frame_files[i])
        try:
            frame_num = int(os.path.splitext(frame_name)[0])
        except:
            frame_num = i + 1
        # Create timestamp with small increments
        timestamp = (base_time + timedelta(seconds=i*0.033)).strftime("%Y-%m-%d %H:%M:%S.%f")
        q.append(f"{timestamp} {frame_num}")
    q = q[::-1]  # Reverse to match expected order
    print(f"Created queue with {len(q)} frame pairs to process")

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
    """Write log file for multi-person gaze tracking."""
    with open(log_path, 'a') as f:
        for line in log_lines:
            f.write(','.join(str(x) for x in line) + '\n')


username = get_flash_username()
# Use the faces_gallery_path provided as argument
flash_tv = FLASHtv(username, family_id=str(famid), num_identities=num_identities, data_path=os.path.dirname(faces_gallery_path), frame_res_hw=None, output_res_hw=None)

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
            print(f"Warning: Could not read frame {frame_num} or {frame_num+1}, skipping...")
            continue

        batch7_list = [[imgv1_1, frame_num, time_stamp] for i in range(7)]
        batch7_list[4][0] = imgv1_2

        batch_count += 1
        batch_write = True
        processed_frames += 1
        
        # Show progress every 10 frames
        if processed_frames % 10 == 0:
            print(f"Progress: {processed_frames}/{total_frames} frames processed ({100*processed_frames/total_frames:.1f}%)")

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
            
            # Count total faces detected
            total_faces = sum(len(bbox_ls) for bbox_ls in frame_bbox_ls)
            
            # Process results for each person
            print(f"\nFrame {frame_counts[3]} at {timestamp}")
            print(f"Total faces detected: {total_faces}")
            print("-" * 40)
            
            # Create summary log line
            summary_line = [timestamp, str(frame_counts[3]).zfill(6), total_faces]
            
            # Process each identity (skip poster face at index 3)
            for person_id in range(num_identities):
                person_name = IDENTITY_NAMES.get(person_id, f"person{person_id}")
                
                # Skip poster face (identity 3)
                if person_id == 3:
                    continue
                    
                if person_id in persons_gaze_results and persons_gaze_results[person_id]["present"]:
                    result = persons_gaze_results[person_id]
                    gaze_data = result["gaze_data"]
                    bbox = result["bboxes"][0]  # Use first bbox if multiple
                    
                    # Extract gaze values
                    o1, e1, o2, e2 = gaze_data
                    # Handle case where confidence might not be in o1
                    if o1.shape[1] > 2:
                        gaze_vals1 = list(o1[0])  # pitch, yaw, confidence already included
                    else:
                        gaze_vals1 = list(o1[0]) + [e1[0][0]]  # append error as confidence
                    
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
                    
                    # Add to summary (simplified)
                    summary_line.extend([person_name, 1, gaze_vals1[0], gaze_vals1[1], gaze_vals1[2]])
                    
                    # Detailed log line for this person
                    detailed_line = [timestamp, str(frame_counts[3]).zfill(6), person_name, 1] + gaze_vals1 + [angle] + pos
                    log_lines_detailed.append(detailed_line)
                else:
                    print(f"  {person_name}: Not detected")
                    summary_line.extend([person_name, 0, None, None, None])
                    
                    # Detailed log line for missing person
                    detailed_line = [timestamp, str(frame_counts[3]).zfill(6), person_name, 0, None, None, None, None, None, None, None, None]
                    log_lines_detailed.append(detailed_line)
            
            log_lines.append(summary_line)
            
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
                        cv2.putText(img_vis, person_name, 
                                  (left, top - 10),
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                        
                        # Add confidence score if available
                        # Check if confidence value exists (3rd element)
                        if o1.shape[1] > 2:
                            confidence = o1[0, 2]
                            conf_text = f"Conf: {confidence:.2f}"
                            cv2.putText(img_vis, conf_text,
                                      (left, bottom + 15),
                                      cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
                
                # Save the visualization
                if write_image_data:
                    cv2.imwrite(save_path_img, img_vis)
                
                # Display in real-time if requested
                if args.display:
                    cv2.imshow('Multi-Person Gaze Tracking', img_vis)
                    # Wait 1ms and check for 'q' key to quit
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        print("\nDisplay window closed by user")
                        q = []  # Clear queue to stop processing
                        break

        else:
            print(f"\nFrame {frame_counts[3]} at {timestamp}")
            print("No faces detected")
            
            # Log no faces for all identities
            summary_line = [timestamp, str(frame_counts[3]).zfill(6), 0]
            for person_id in range(num_identities):
                person_name = IDENTITY_NAMES.get(person_id, f"person{person_id}")
                summary_line.extend([person_name, 0, None, None, None])
            log_lines.append(summary_line)

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

print("\n" + "="*60)
print("Processing complete!")
print(f"Summary log: {log_path}")
print(f"Detailed log: {log_path_detailed}")
if write_image_data:
    print(f"Visualizations: {frames_save_path}/")