import os

# import queue libraries
import subprocess
import sys
import threading as th

# time libs
import time
import traceback
from datetime import datetime
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

# super variables
write_image_data = True
rotate_to_find_tc = False  # Disabled for multi-person tracking
famid = sys.argv[1]

# Identity mapping for readable output
IDENTITY_NAMES = {
    0: "tc",      # Target child
    1: "parent1", # Parent 1
    2: "parent2", # Parent 2
    3: "sib1"     # Sibling 1
}

famid = str(famid)
frames_read_path = "/media/flashsys007/FLASH_SSD/" + famid + "_frames"
fname_log_read = "/home/flashsys007/code_test/flash_old_logs/txt_logs/" + famid + "_flash_log_sub_sort.txt"
a = open(fname_log_read, "r")
q = a.readlines()
q = [line.strip() for line in q]
q = q[::-1]


save_path = "/home/" + os.getlogin() + "/code_test/data"
frames_path = os.path.join(save_path, str(famid) + "_frames")
frames_save_path = os.path.join(save_path, str(famid) + "_test_res_multi")
frames_path, frames_save_path = make_directories(save_path, famid, frames_path, frames_save_path)


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
flash_tv = FLASHtv(username, family_id=str(famid), num_identities=num_identities, data_path=save_path, frame_res_hw=None, output_res_hw=None)

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
print("-" * 60)

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
            
            # Process each identity
            for person_id in range(num_identities):
                person_name = IDENTITY_NAMES.get(person_id, f"person{person_id}")
                
                if person_id in persons_gaze_results and persons_gaze_results[person_id]["present"]:
                    result = persons_gaze_results[person_id]
                    gaze_data = result["gaze_data"]
                    bbox = result["bboxes"][0]  # Use first bbox if multiple
                    
                    # Extract gaze values
                    o1, e1, o2, e2 = gaze_data
                    gaze_vals1 = list(o1[0]) + [e1[0][0]]  # pitch, yaw, confidence
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
                        
                        # Add confidence score
                        confidence = o1[0, 2]
                        conf_text = f"Conf: {confidence:.2f}"
                        cv2.putText(img_vis, conf_text,
                                  (left, bottom + 15),
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
                
                # Save the visualization
                cv2.imwrite(save_path_img, img_vis)

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
        break

# Write remaining logs
if log_lines:
    write_multi_log_file(log_path, log_lines)
if log_lines_detailed:
    write_multi_log_file(log_path_detailed, log_lines_detailed)

print("\n" + "="*60)
print("Processing complete!")
print(f"Summary log: {log_path}")
print(f"Detailed log: {log_path_detailed}")
print(f"Visualizations: {frames_save_path}/")