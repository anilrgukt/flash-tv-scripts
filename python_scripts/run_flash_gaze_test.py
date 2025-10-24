#!/usr/bin/env python3
"""
Real-time FLASH-TV gaze testing script
Combines the robust FLASHtv pipeline with live visualization for testing purposes.

Shows colored gaze arrows:
- Green arrow: Gaze detected (looking at TV)
- Red arrow: No gaze detected (not looking at TV)
- Face rectangles: Different colors for different family members

Usage: python run_flash_gaze_test.py <participant_id> <data_path> <save-image> <username>
Press 'q' to quit the test.
"""

import os
import sys
import time
from datetime import datetime

import cv2
import numpy as np

# Import FLASH-TV components
from flash_main import FLASHtv
from flash.gaze_estimation import eval_thrshld, get_lims, load_limits
from utils.flash_runtime_utils import cam_id
from utils.visualizer import draw_gz, draw_rect_ver

def process_frame(frame_rgb, bbox_list, flash_tv, loc_lims, num_locs, current_time, frame_count):
    """Process a frame and return display frame and status text"""
    
    if bbox_list:
        # Step 2: Face Verification (identify family members)
        bbox_list = flash_tv.run_verification(cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR), bbox_list)
        
        # Step 3: Gaze Estimation (only for target child)
        tc_present, gaze_data, tc_bboxes, tc_frame_id, _ = flash_tv.run_gaze([frame_rgb], [bbox_list])
        
        if tc_present:
            # Target child detected - check if we can estimate gaze
            tc_bbox = tc_bboxes[0]
            
            if gaze_data is not None:
                # CASE 1 & 2: Gaze estimation successful
                # Extract gaze data
                o1, e1, o2, e2 = gaze_data
                
                # Convert to numpy arrays - handle both tensors and numpy arrays
                if hasattr(o1, 'cpu'):  # PyTorch tensor
                    o1 = o1.cpu().data.numpy()
                    e1 = e1.cpu().data.numpy()
                    o2 = o2.cpu().data.numpy()
                    e2 = e2.cpu().data.numpy()
                elif hasattr(o1, 'asnumpy'):  # MXNet NDArray
                    o1 = o1.asnumpy()
                    e1 = e1.asnumpy()
                    o2 = o2.asnumpy()
                    e2 = e2.asnumpy()
                # If already numpy arrays, leave them as is
                
                # Combine models (same weighting as demo script)
                combined_gaze = 0.9 * o1 + 0.1 * o2
                
                # Determine if looking at TV using proper thresholds
                if loc_lims is not None:
                    # Use proper TV gaze evaluation (same as demo script)
                    lims_idx = get_lims(tc_bbox, num_locs, H=342, W=608)
                    _, _, gaze_est, _, _ = eval_thrshld(
                        np.array([combined_gaze[0, 0]]), 
                        np.array([combined_gaze[0, 1]]), 
                        gt_lab=np.array([0]), 
                        lims=loc_lims[lims_idx]
                    )
                    looking_at_tv = gaze_est[0]
                else:
                    # Fallback simple threshold if limits file not found
                    gaze_confidence = e1[0][0] if len(e1[0]) > 0 else 0.5
                    looking_at_tv = int(gaze_confidence > 0.3)
                
                # Print status - split into the two gaze categories
                if looking_at_tv:
                    status = "Gaze-det-TV"
                    color_name = "GREEN arrow"
                    arrow_color = 1  # Green in draw_gz
                else:
                    status = "Gaze-det-no-TV"
                    color_name = "BLUE arrow"
                    arrow_color = None  # Will draw blue manually
                
                # Draw the gaze arrow with color coding
                try:
                    # Ensure gaze data has correct shape for draw_gz
                    if combined_gaze.shape[-1] == 2:
                        # Add a dummy third dimension (confidence) if missing
                        gaze_for_drawing = np.concatenate([combined_gaze, np.ones((combined_gaze.shape[0], 1))], axis=1)
                    else:
                        gaze_for_drawing = combined_gaze

                    if looking_at_tv:
                        # GREEN arrow for looking at TV
                        display_frame, _ = draw_gz(
                            frame_rgb,
                            gaze_for_drawing.reshape(1, 3),
                            tc_bbox,
                            save_path=None,
                            gz_label=1,  # Green arrow
                            write_img=False,
                            scale=[480, 854]
                        )
                    else:
                        # BLUE arrow for gaze detected but not looking at TV
                        display_frame, _ = draw_gz(
                            frame_rgb,
                            gaze_for_drawing.reshape(1, 3),
                            tc_bbox,
                            save_path=None,
                            gz_label=None,  # This will draw with default blue color
                            write_img=False,
                            scale=[480, 854]
                        )
                except Exception as draw_error:
                    print(f"Warning: Could not draw gaze arrow: {draw_error}")
                    # Fallback to just showing the detection box
                    display_frame = draw_rect_ver(
                        frame_rgb,
                        bbox_list,
                        None,
                        save_path=None,
                        write_img=False,
                        scale=[480, 854]
                    )
                
                gaze_x, gaze_y = combined_gaze[0, 0], combined_gaze[0, 1]
                status_text = f"{status} ({color_name}) | Gaze: ({gaze_x:.3f}, {gaze_y:.3f})"
                print(f"{current_time.strftime('%H:%M:%S')} | Frame {frame_count:04d} | {status_text}")
                
            else:
                # CASE 3: Target child detected but no gaze estimation
                display_frame = draw_rect_ver(
                    frame_rgb, 
                    bbox_list, 
                    None, 
                    save_path=None, 
                    write_img=False, 
                    scale=[480, 854]
                )
                
                # Add RED overlay to indicate "gaze-no-det"
                display_frame_bgr = cv2.cvtColor(display_frame, cv2.COLOR_RGB2BGR)
                # Draw RED rectangle around target child
                for box in bbox_list:
                    if box.get("idx") == 0:  # Target child ID
                        # Scale coordinates for display
                        scale_w, scale_h = 854 / 608.0, 480 / 342.0
                        left = int(box["left"] * scale_w)
                        top = int(box["top"] * scale_h)
                        right = int(box["right"] * scale_w)
                        bottom = int(box["bottom"] * scale_h)
                        cv2.rectangle(display_frame_bgr, 
                                    (left, top), (right, bottom), 
                                    (0, 0, 255), 8)  # RED thick border
                display_frame = cv2.cvtColor(display_frame_bgr, cv2.COLOR_BGR2RGB)
                
                status_text = "Gaze-no-det (RED box)"
                print(f"{current_time.strftime('%H:%M:%S')} | Frame {frame_count:04d} | {status_text}")
            
        else:
            # CASE 4: No target child detected (but other faces may be present)
            display_frame = draw_rect_ver(
                frame_rgb, 
                bbox_list, 
                None, 
                save_path=None, 
                write_img=False, 
                scale=[480, 854]
            )
            status_text = "Gaze-no-det (target child not detected)"
            print(f"{current_time.strftime('%H:%M:%S')} | Frame {frame_count:04d} | {status_text}")
    else:
        # CASE 4: No faces detected at all - no overlay
        display_frame = cv2.resize(frame_rgb, (854, 480))
        status_text = "No-face-detected"
        print(f"{current_time.strftime('%H:%M:%S')} | Frame {frame_count:04d} | {status_text}")
    
    # Convert to BGR for OpenCV display and add basic info
    display_frame_bgr = cv2.cvtColor(display_frame, cv2.COLOR_RGB2BGR)
    
    # Add text overlay with instructions
    cv2.putText(display_frame_bgr, "FLASH-TV Gaze Test", (10, 30), 
               cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    cv2.putText(display_frame_bgr, f"Frame: {frame_count}", (10, 110), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    return display_frame_bgr, status_text

def main():
    # Parse command line arguments (same as data collection script)
    if len(sys.argv) != 5:
        print("Usage: python run_flash_gaze_test.py <participant_id> <data_path> <save-image> <username>")
        print("Example: python run_flash_gaze_test.py 123A /home/user/data save-image flashsys028")
        sys.exit(1)
    
    participant_id = sys.argv[1]
    data_path = sys.argv[2] 
    save_images = sys.argv[3] == "save-image"  # Not used in testing but kept for compatibility
    username = sys.argv[4]
    
    print(f"=== FLASH-TV Real-time Gaze Testing ===")
    print(f"Participant ID: {participant_id}")
    print(f"Data Path: {data_path}")
    print(f"Username: {username}")
    print(f"Press 'q' to quit the test")
    print()
    print("Status Categories:")
    print("   GREEN arrow = Gaze-det-TV (target child gaze looking at TV)")
    print("   BLUE arrow = Gaze-det-no-TV (target child gaze NOT looking at TV)")
    print("   RED box = Gaze-no-det (target child detected but no gaze estimation)")
    print("   No overlay = No-face-detected (no faces found)")
    print()
    
    # Initialize FLASH-TV system
    print("Initializing FLASH-TV models (this may take a few minutes)...")
    num_identities = 4  # parents, siblings, target child
    
    try:
        flash_tv = FLASHtv(
            username=username,
            family_id=participant_id,
            num_identities=num_identities,
            data_path=data_path,
            frame_res_hw=None,
            output_res_hw=None
        )
        print("FLASH-TV models loaded successfully!")
    except Exception as e:
        print(f"Error initializing FLASH-TV: {e}")
        print("Please check that all model files are properly installed.")
        sys.exit(1)
    
    # Load TV gaze thresholds (spatial limits for determining TV viewing)
    print("Loading TV gaze thresholds...")
    try:
        # Use absolute path based on script location
        script_dir = os.path.dirname(os.path.abspath(__file__))
        limits_file = os.path.join(script_dir, "4331_v3r50reg_reg_testlims_35_53_7_9.npy")

        loc_lims = load_limits(
            file_path=limits_file,
            setting="center-big-med"
        )
        num_locs = loc_lims.shape[0]
        print(f"TV gaze thresholds loaded ({num_locs} spatial regions)")
    except Exception as e:
        print(f"Could not load location limits file: {e}")
        print("Using fallback simple threshold...")
        loc_lims = None
        num_locs = 0
    
    # Initialize camera
    print("Initializing camera...")
    try:
        camera_idx = cam_id()
        cap = cv2.VideoCapture(camera_idx, cv2.CAP_V4L2)
        
        # Set camera properties
        codec = cv2.VideoWriter_fourcc('M', 'J', 'P', 'G')
        cap.set(cv2.CAP_PROP_FOURCC, codec)
        cap.set(cv2.CAP_PROP_FPS, 30)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        
        if not cap.isOpened():
            raise Exception("Could not open camera")
            
        print(f"Camera initialized (device: /dev/video{camera_idx})")
    except Exception as e:
        print(f"Error initializing camera: {e}")
        sys.exit(1)
    
    # Frame buffer setup
    frame_buffer = []  # Store processed frames with metadata
    max_buffer_size = 1000  # Keep last 1000 frames (~33 seconds at 30fps)
    current_frame_idx = -1  # -1 means live streaming
    is_paused = False
    
    # Create output directory for frame saving (optional)
    output_dir = os.path.join(data_path, f"{participant_id}_gaze_test_frames")
    os.makedirs(output_dir, exist_ok=True)
    
    # Main testing loop
    print("\nStarting real-time gaze detection test...")
    print("Look at different areas to test gaze detection")
    print()
    print("Controls:")
    print("   SPACE = Pause/Resume streaming")
    print("   LEFT ARROW = Previous frame (when paused)")
    print("   RIGHT ARROW = Next frame (when paused)")
    print("   HOME = Jump to oldest buffered frame")
    print("   END = Jump to newest frame")
    print("   ESC/R = Return to live streaming")
    print("   Q = Quit")
    print()
    
    frame_count = 0
    start_time = time.time()
    
    try:
        while True:
            # Handle keyboard input
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q'):
                print("\nTest stopped by user")
                break
            elif key == ord(' '):  # Space bar - pause/resume
                is_paused = not is_paused
                if is_paused:
                    current_frame_idx = len(frame_buffer) - 1 if frame_buffer else 0
                    print(f"PAUSED - Frame {current_frame_idx + 1}/{len(frame_buffer)}")
                else:
                    current_frame_idx = -1
                    print("RESUMED - Live streaming")
                continue
            elif key == 27 or key == ord('r'):  # ESC or R - return to live
                if is_paused:
                    is_paused = False
                    current_frame_idx = -1
                    print("RESUMED - Live streaming")
                continue
            elif key == 83 and is_paused:  # Right arrow - next frame
                if current_frame_idx < len(frame_buffer) - 1:
                    current_frame_idx += 1
                    print(f"Frame {current_frame_idx + 1}/{len(frame_buffer)}")
            elif key == 81 and is_paused:  # Left arrow - previous frame
                if current_frame_idx > 0:
                    current_frame_idx -= 1
                    print(f"Frame {current_frame_idx + 1}/{len(frame_buffer)}")
            elif key == 80 and is_paused:  # Home - first frame
                if frame_buffer:
                    current_frame_idx = 0
                    print(f"First frame - Frame {current_frame_idx + 1}/{len(frame_buffer)}")
            elif key == 87 and is_paused:  # End - last frame
                if frame_buffer:
                    current_frame_idx = len(frame_buffer) - 1
                    print(f"Last frame - Frame {current_frame_idx + 1}/{len(frame_buffer)}")
            
            # Display logic
            if is_paused and frame_buffer and 0 <= current_frame_idx < len(frame_buffer):
                # Show buffered frame
                frame_data = frame_buffer[current_frame_idx]
                display_frame_bgr = frame_data['display_frame']
                frame_count = frame_data['frame_count']
                current_time = frame_data['timestamp']
                status_text = frame_data['status']
                
                # Add navigation info to display
                nav_text = f"PAUSED - Frame {current_frame_idx + 1}/{len(frame_buffer)} | {status_text}"
                cv2.putText(display_frame_bgr, nav_text, (10, 150), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                
            elif not is_paused:
                # Live streaming mode - capture and process new frame
                ret, frame = cap.read()
                if not ret:
                    print("Failed to capture frame from camera")
                    break

                frame_count += 1
                current_time = datetime.now()

                try:
                    # Convert BGR to RGB for processing
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                    # Step 1: Face Detection
                    bbox_list = flash_tv.run_detector(frame)

                    # Process frame and create display
                    display_frame_bgr, status_text = process_frame(
                        frame_rgb, bbox_list, flash_tv, loc_lims, num_locs, current_time, frame_count
                    )

                    # Save frame to buffer
                    frame_data = {
                        'frame_count': frame_count,
                        'timestamp': current_time,
                        'display_frame': display_frame_bgr.copy(),
                        'status': status_text,
                        'raw_frame': frame.copy(),
                        'bbox_list': bbox_list
                    }

                    frame_buffer.append(frame_data)

                    # Limit buffer size
                    if len(frame_buffer) > max_buffer_size:
                        frame_buffer.pop(0)

                    # Add live streaming indicator
                    cv2.putText(display_frame_bgr, "LIVE", (10, 150),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                except Exception as frame_error:
                    print(f"Warning: Error processing frame {frame_count}: {frame_error}")
                    # Continue with a fallback display
                    display_frame_bgr = cv2.resize(frame, (854, 480))
                    cv2.putText(display_frame_bgr, f"PROCESSING ERROR - Frame {frame_count}", (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    cv2.putText(display_frame_bgr, "LIVE", (10, 150),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            else:
                # Skip if paused and no buffered frame to show
                continue
            
            # Show the frame
            cv2.imshow("FLASH-TV Gaze Detection Test", display_frame_bgr)
            
            # Print summary every 100 frames (only in live mode)
            if not is_paused and frame_count % 100 == 0:
                elapsed = time.time() - start_time
                fps = frame_count / elapsed
                print(f"\nSummary: {frame_count} frames processed in {elapsed:.1f}s (avg {fps:.1f} FPS)")

    except KeyboardInterrupt:
        print("\nTest interrupted by user (Ctrl+C)")
    except Exception as e:
        print(f"\nError during testing: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        print("\nCleaning up...")
        cap.release()
        cv2.destroyAllWindows()

        elapsed = time.time() - start_time
        if elapsed > 0:
            avg_fps = frame_count / elapsed
            print(f"Final stats: {frame_count} frames in {elapsed:.1f}s (avg {avg_fps:.1f} FPS)")

        print("FLASH-TV gaze test completed")

if __name__ == "__main__":
    main()