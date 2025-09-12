from __future__ import annotations

import os
import subprocess
import sys
import threading as th
import time
from queue import Queue

import cv2
import numpy as np

username = str(sys.argv[3])
sys.path.insert(1, os.path.join("/home/" + username + "/FLASH_TV/python_wrapper"))
sys.path.insert(1, os.path.join("/home/" + username + "/flash-tv-scripts/python_scripts"))

from face_detector_YOLOv2 import YoloFace
from flash.face_verification import FLASHFaceVerification
from flash.face_processing import FaceModelv4 as FaceProcessing
from utils.bbox_utils import Bbox

IMAGE_SIZE = [1080, 1920]
DETECTED_IMAGE_SIZE = [342, 608]
BBOX_SCALE = [IMAGE_SIZE[i] / float(DETECTED_IMAGE_SIZE[i]) for i in range(2)]
HEIGHT_SCALE = BBOX_SCALE[0]
WIDTH_SCALE = BBOX_SCALE[1]


def extract_face_embedding(img, dbox, use_cache=True):
    """Extract face embedding for recognition using FLASH face verification"""
    global face_verification, face_processing, face_embedding_cache

    if face_verification is None or face_processing is None:
        return None

    try:
        # Create cache key based on face position and frame characteristics
        cache_key = f"{dbox['left']}_{dbox['top']}_{dbox['right']}_{dbox['bottom']}"

        # Check cache first for performance
        if use_cache and cache_key in face_embedding_cache:
            return face_embedding_cache[cache_key]

        # Convert YOLO detection coordinates to full resolution for face processing
        # YOLO detects on 608x342, but we need 1920x1080 coordinates
        scaled_dbox = {
            "left": dbox["left"] * WIDTH_SCALE,
            "top": dbox["top"] * HEIGHT_SCALE,
            "right": dbox["right"] * WIDTH_SCALE,
            "bottom": dbox["bottom"] * HEIGHT_SCALE,
            "prob": dbox["prob"],
        }

        # Process face exactly like FLASH main system
        bbox = Bbox(scaled_dbox)

        # Crop and align face using FLASH face processing
        face, bbox_ = face_processing.crop_face_from_frame(img, bbox)
        face, lmarks = face_processing.resize_face(face, bbox_)

        # Safety check for landmarks format
        if lmarks is None or len(lmarks) == 0:
            print("Warning: No landmarks detected for face")
            return None

        # Ensure landmarks are in correct format
        if lmarks.ndim == 1:
            lmarks = lmarks.reshape(5, 2)
        elif lmarks.ndim == 2 and lmarks.shape[0] != 5:
            print(f"Warning: Unexpected landmarks shape: {lmarks.shape}")
            return None

        facen = face_processing.get_normalized_face(face, lmarks.astype(np.int32).reshape(1, 5, 2), face=True)

        # Create pair: original + horizontally flipped (FLASH requirement)
        cropped_aligned_faces = []
        cropped_aligned_faces.append(facen)
        cropped_aligned_faces.append(facen[:, ::-1, :])  # Flipped version

        cropped_aligned_faces = np.array(cropped_aligned_faces)

        # Get embedding using FLASH verification
        det_emb, _ = face_verification.get_face_embeddings(cropped_aligned_faces)

        if det_emb is not None and len(det_emb) > 0 and det_emb[0] is not None:
            embedding = det_emb[0]
            # Cache the result
            if use_cache:
                face_embedding_cache[cache_key] = embedding
                # Limit cache size
                if len(face_embedding_cache) > 50:
                    # Remove oldest entries
                    keys = list(face_embedding_cache.keys())
                    for key in keys[:10]:
                        del face_embedding_cache[key]
            return embedding
        else:
            return None

    except Exception as e:
        print(f"Error extracting face embedding: {e}")
        return None


def find_matching_face(target_embedding, current_frame_img, dboxes, threshold=0.436, use_recognition=True):
    """Find face in current frame that matches target embedding with performance optimizations"""
    global last_matched_face, frame_skip_counter, face_recognition_interval, face_verification

    if target_embedding is None:
        return None

    # Performance optimization: Skip face recognition on some frames
    frame_skip_counter += 1
    if not use_recognition or frame_skip_counter % face_recognition_interval != 0:
        # Use position-based fallback for performance
        if last_matched_face is not None:
            for dbox in dboxes:
                if (
                    dbox["prob"] > 0.1
                    and area(dbox) > 35.00
                    and abs(dbox["left"] - last_matched_face["left"]) < 15
                    and abs(dbox["top"] - last_matched_face["top"]) < 15
                ):
                    return dbox
        return None

    best_match = None
    best_similarity = float("inf")

    # Limit number of faces to check for performance
    sorted_faces = sorted([d for d in dboxes if d["prob"] > 0.1 and area(d) > 35.00], key=lambda x: x["prob"], reverse=True)[
        :3
    ]  # Only check top 3 faces

    for dbox in sorted_faces:
        # Extract embedding for this face
        current_embedding = extract_face_embedding(current_frame_img, dbox, use_cache=True)

        if current_embedding is not None:
            # Calculate similarity (distance)
            similarity = np.linalg.norm(target_embedding - current_embedding)

            if similarity < threshold and similarity < best_similarity:
                best_similarity = similarity
                best_match = dbox

    # Cache the result for position-based fallback
    if best_match is not None:
        last_matched_face = best_match

    return best_match


def mouse_click_callback(event, x, y, flags, param):
    global mouse_x, mouse_y, selected_face_box, selected_face_data, selected_face_embedding, current_faces, current_frame_img

    if event == cv2.EVENT_LBUTTONDOWN:
        mouse_x, mouse_y = x, y
        # Check if click is within any face bounding box
        for i, dbox in enumerate(current_faces):
            if dbox["prob"] > 0.1:
                # Scale coordinates back to display size
                left = int(dbox["left"] * WIDTH_SCALE)
                right = int(dbox["right"] * WIDTH_SCALE)
                top = int(dbox["top"] * HEIGHT_SCALE)
                bottom = int(dbox["bottom"] * HEIGHT_SCALE)

                if left <= x <= right and top <= y <= bottom:
                    selected_face_box = dbox
                    selected_face_data = i

                    # Extract face embedding for recognition-based tracking
                    print(f"Extracting face embedding for recognition...")
                    selected_face_embedding = extract_face_embedding(current_frame_img, dbox)

                    if selected_face_embedding is not None:
                        print(f"Selected face {i + 1} - Face recognition active - Now saving backup frames")
                    else:
                        print(f"Selected face {i + 1} - Using position tracking (embedding failed)")
                    break
        else:
            selected_face_box = None
            selected_face_data = None
            selected_face_embedding = None
            print("No face selected")

    elif event == cv2.EVENT_RBUTTONDOWN:
        # Right-click to unselect current face
        if selected_face_box is not None:
            print("Face unselected - backup saving stopped")
            selected_face_box = None
            selected_face_data = None
            selected_face_embedding = None
        else:
            print("No face was selected")


def save_selected_face(img, face_num):
    global selected_face_box, show_face, face_collection, participant_id, imsave_dir, current_faces, selected_face_embedding

    if selected_face_box is None or show_face is None:
        print("No face selected or category not set")
        return

    # Find the current frame's detection of the selected face using face recognition
    matched_face = None

    # Use face recognition if available and embedding exists
    if selected_face_embedding is not None and face_verification is not None:
        matched_face = find_matching_face(selected_face_embedding, img, current_faces, use_recognition=True)

    # Fallback to position-based matching if face recognition failed or unavailable
    if matched_face is None:
        for detface in current_faces:
            if (
                area(detface) > 35.00
                and detface["prob"] >= 0.11
                and abs(detface["left"] - selected_face_box["left"]) < 15
                and abs(detface["top"] - selected_face_box["top"]) < 15
            ):
                matched_face = detface
                break

    if matched_face is not None:
        # Use CURRENT frame coordinates from face recognition
        [x1, x2, y1, y2] = get_face(matched_face)
        face = img[y1:y2, x1:x2, :]
        face = cv2.resize(face, (160, 160))

        # Determine category and filename
        category_map = {"TC": "tc", "Sib": "sib", "Parent": "parent", "Extra": "extra"}
        category = category_map[show_face]

        # Save face with proper naming convention directly to main faces folder
        filename = f"{participant_id}_{category}{face_num + 1}.png"
        output_path = os.path.join(imsave_dir, filename)  # Save directly to main folder

        cv2.imwrite(output_path, face)

        # Store in face collection for verification panel
        face_collection[category][face_num] = face

        print(f"Saved {filename} in {category}_selected folder using face recognition")
    else:
        print("Selected face not found in current frame - try again when face is visible")

    # Don't clear selection - let user save multiple numbered faces of same person


def create_face_verification_panel(show_face, width=1920, height=250):
    global face_collection, participant_id

    panel = np.zeros((height, width, 3), dtype=np.uint8)

    if show_face is None:
        # No category selected - show empty panel
        return panel

    # Map display names to internal names
    category_map = {"TC": "tc", "Sib": "sib", "Parent": "parent", "Extra": "extra"}
    category_display_map = {"TC": "TARGET CHILD", "Sib": "SIBLING", "Parent": "PARENT", "Extra": "EXTRA"}

    if show_face not in category_map:
        return panel

    cat = category_map[show_face]
    display_name = category_display_map[show_face]

    # Calculate centered positioning for 5 faces
    box_size = 160  # Match saved face size
    spacing = 20  # Space between boxes
    total_width = (box_size * 5) + (spacing * 4)
    start_x = (width - total_width) // 2  # Center horizontally

    # Vertical positioning with space for labels
    top_margin = 60  # Space for category label and position labels
    y1 = top_margin
    y2 = y1 + box_size

    # Draw category label centered above faces
    category_y = 15
    label_text = f"{display_name}"
    text_size = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
    label_x = start_x + (total_width - text_size[0]) // 2
    cv2.putText(panel, label_text, (label_x, category_y), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

    # Face position labels
    position_labels = ["Straight", "Left or Right", "Up or Down", "Position 1", "Position 2"]

    # Draw face boxes
    for j in range(5):
        x1 = start_x + j * (box_size + spacing)
        x2 = x1 + box_size

        # Draw position label above each box
        label_text = position_labels[j]
        label_font_scale = 0.7
        label_thickness = 2
        label_size = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, label_font_scale, label_thickness)[0]
        label_x = x1 + (box_size - label_size[0]) // 2
        label_y = y1 - 20
        cv2.putText(panel, label_text, (label_x, label_y), cv2.FONT_HERSHEY_SIMPLEX, label_font_scale, (200, 200, 200), label_thickness)

        # Draw subtitle for "Left or Right" label only
        if j == 1:  # Only for the second box (Left or Right)
            subtitle_text = "(eyes visible)"
            subtitle_y = y1 - 5
            cv2.putText(panel, subtitle_text, (label_x, subtitle_y), cv2.FONT_HERSHEY_SIMPLEX, label_font_scale, (150, 150, 150), label_thickness)

        if face_collection[cat][j] is not None:
            # Show saved face (already 160x160)
            panel[y1:y2, x1:x2] = face_collection[cat][j]
            cv2.rectangle(panel, (x1, y1), (x2, y2), (0, 255, 0), 2)  # Green border
        else:
            # Empty placeholder
            cv2.rectangle(panel, (x1, y1), (x2, y2), (128, 128, 128), 1)  # Gray border
            # Number in center
            num_text = f"{j + 1}"
            num_size = cv2.getTextSize(num_text, cv2.FONT_HERSHEY_SIMPLEX, 1.5, 2)[0]
            num_x = x1 + (box_size - num_size[0]) // 2
            num_y = y1 + (box_size + num_size[1]) // 2
            cv2.putText(panel, num_text, (num_x, num_y), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (128, 128, 128), 2)

    return panel


def draw_rect(img, dboxes, show, save_file=None, face_lost=False):
    global selected_face_box
    cv_img = np.copy(img)
    tmp_channel = np.copy(cv_img[:, :, 0])
    cv_img[:, :, 0] = cv_img[:, :, 2]
    cv_img[:, :, 2] = tmp_channel
    colors = {"TC": (0, 255, 0), "Sib": (255, 0, 0), "Parent": (255, 255, 0), "Extra": (255, 255, 255)}
    color = colors[show] if show is not None else (0, 0, 255)

    for i, dbox in enumerate(dboxes):
        if dbox["prob"] > 0.1:
            # Check if this is the selected face
            if selected_face_box is not None and dbox == selected_face_box:
                # Draw thick border for selected face
                cv2.rectangle(cv_img, (int(dbox["left"]), int(dbox["top"])), (int(dbox["right"]), int(dbox["bottom"])), (0, 255, 255), 2)
            else:
                # Normal face detection box
                cv2.rectangle(cv_img, (int(dbox["left"]), int(dbox["top"])), (int(dbox["right"]), int(dbox["bottom"])), color, 1)

    # cv2.imwrite(save_file, cv_img)

    # Enhanced visual feedback with corner positioning and smaller text
    font = cv2.FONT_HERSHEY_SIMPLEX

    # Top-right: Mode indicator (if selected)
    if show is not None:
        mode_text = f"Mode: {show}"
        fontScale = 0.5
        thickness = 1
        text_size, _ = cv2.getTextSize(mode_text, font, fontScale, thickness)
        text_w, text_h = text_size

        # Position in top-right corner
        x = cv_img.shape[1] - text_w - 20
        y = 30

        # Semi-transparent background
        overlay = cv_img.copy()
        cv2.rectangle(overlay, (x - 5, y - text_h - 5), (x + text_w + 5, y + 5), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, cv_img, 0.3, 0, cv_img)
        cv2.putText(cv_img, mode_text, (x, y), font, fontScale, (255, 255, 255), thickness)

    # Top-left: Instructions
    if show is not None:
        if selected_face_box is not None:
            if not face_lost:
                instruction = f"Press 1-5 to save"
                textColor = (0, 255, 0)  # Green
            else:
                instruction = f"Face lost - Click to reselect"
                textColor = (0, 0, 255)  # Red
        else:
            instruction = f"Click face to select"
            textColor = (255, 255, 0)  # Yellow
    else:
        instruction = "Press T/S/P/E for mode"
        textColor = (200, 200, 200)  # Light gray

    fontScale = 0.5
    thickness = 1
    x, y = 20, 30

    # Semi-transparent background
    text_size, _ = cv2.getTextSize(instruction, font, fontScale, thickness)
    text_w, text_h = text_size
    overlay = cv_img.copy()
    cv2.rectangle(overlay, (x - 5, y - text_h - 5), (x + text_w + 5, y + 5), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.7, cv_img, 0.3, 0, cv_img)
    cv2.putText(cv_img, instruction, (x, y), font, fontScale, textColor, thickness)

    # Bottom-right: Keyboard shortcuts
    help_text = "T/S/P/E=Mode | 1-5=Save | R=Unselect | Q=Quit"
    fontScale = 0.4
    thickness = 1
    text_size, _ = cv2.getTextSize(help_text, font, fontScale, thickness)
    text_w, text_h = text_size

    x = cv_img.shape[1] - text_w - 20
    y = cv_img.shape[0] - 10

    # Semi-transparent background
    overlay = cv_img.copy()
    cv2.rectangle(overlay, (x - 5, y - text_h - 5), (x + text_w + 5, y + 5), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.7, cv_img, 0.3, 0, cv_img)
    cv2.putText(cv_img, help_text, (x, y), font, fontScale, (180, 180, 180), thickness)

    return cv_img


def area(boxA):
    boxAArea = (boxA["right"] - boxA["left"] + 1) * (boxA["bottom"] - boxA["top"] + 1)
    return boxAArea


def get_face(detface):
    offset = 7
    det_left = detface["left"] - offset
    det_right = detface["right"] + offset
    det_top = detface["top"] - offset
    det_bottom = detface["bottom"] + offset

    width = det_right - det_left
    h = det_bottom - det_top

    width = width * WIDTH_SCALE
    h = h * HEIGHT_SCALE

    width_offset = 0  # max((100-w)/2.0, 0)
    height_offset = 0  # max((100-h)/2.0, 0)

    y1 = max(0, int(det_top * HEIGHT_SCALE - height_offset))
    y2 = min(int(det_bottom * HEIGHT_SCALE + height_offset), 1080)
    x1 = max(0, int(det_left * WIDTH_SCALE - width_offset))
    x2 = min(int(det_right * WIDTH_SCALE + width_offset), 1920)
    # face = img[y1:y2, x1:x2, :]
    # face = skimage.transform.resize(face, [160, 160])
    return [x1, x2, y1, y2]


def cam_id():
    """
    Improved camera identification that handles duplicate video devices properly.
    Compatible with existing cv2_capture_automate usage.
    """
    try:
        # Try to use the improved camera detection utils
        from utils.camera_detection_utils import improved_cam_id
        return improved_cam_id()
    except ImportError:
        # Fallback to original implementation if utils not available
        print("Warning: Using fallback camera detection")
        return _original_cam_id_cv2()


def _original_cam_id_cv2():
    """
    Original cam_id implementation for cv2_capture_automate kept as fallback.
    """
    dev_list = subprocess.Popen("v4l2-ctl --list-devices".split(), shell=False, stdout=subprocess.PIPE)
    out, err = dev_list.communicate()
    out = out.decode()
    dev_paths = out.split("\n")
    dev_path = None

    # WEBCAM_NAME = 'HD Pro Webcam C920' # Logitech Webcam C930e
    WEBCAM_NAME1 = "Logitech Webcam C930e"
    # WEBCAM_NAME2 = 'USB  Live camera: USB  Live cam'
    WEBCAM_NAME2 = "Anker PowerConf C300: Anker Pow"

    # dev_name = {WEBCAM_NAME1: "C930e", WEBCAM_NAME2: "C300"}

    # which_webcam = None
    for i in range(len(dev_paths)):
        # print(i, dev_paths[i])
        if WEBCAM_NAME1 in dev_paths[i]:
            dev_path = dev_paths[i + 1].strip()
            # which_webcam = WEBCAM_NAME1
            break
            # print(dev_path, dev_path[-1])
        elif WEBCAM_NAME2 in dev_paths[i]:
            dev_path = dev_paths[i + 1].strip()
            # which_webcam = WEBCAM_NAME2
            break

    cam_idx = int(dev_path[-1]) if dev_path is not None else -1

    print("CAMERA identified at: ", cam_idx)
    return cam_idx


def frame_write(q, frm_count, yolo) -> None:
    idx = cam_id()
    cap = cv2.VideoCapture(idx, cv2.CAP_V4L2)
    codec = cv2.VideoWriter_fourcc("M", "J", "P", "G")
    # codec = cv2.VideoWriter_fourcc(*'MP4V')
    cap.set(6, codec)
    cap.set(5, 10)

    cap.set(3, 1920)
    cap.set(4, 1080)

    fps = int(cap.get(5))
    print("FPS: ", fps)

    count = frm_count

    global stop_capture
    stop_capture = False

    t_st = time.time()

    while cap.isOpened() and not stop_capture:
        ret, frame = cap.read()
        frame_time = cap.get(cv2.CAP_PROP_POS_MSEC)

        if not ret:
            break
        if count % 10 in [0, 1]:
            imgrgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            imgrgb = cv2.resize(imgrgb, (608, 342))
            dboxes = yolo.yolo_detect_face(imgrgb)
            a = q.put([frame, count, imgrgb, dboxes])

        count += 1

        if (count + 1) % 100 == 0:
            tmp = 10
            print("time for capturing 100 images:::: ", time.time() - t_st)
            t_st = time.time()
            # break

    print("The cam for batch processing is stopped.")
    cap.release()
    cv2.destroyAllWindows()


print("starting the YoLo Face model")

yolo_model = YoloFace(
    os.path.join("/home/" + username + "/FLASH_TV/darknet_face_release"),
    config_path=os.path.join("/home/" + username + "/FLASH_TV/darknet_face_release/cfg/face-shallow-size608-anchor5.cfg"),
    weight_path=os.path.join("/home/" + username + "/FLASH_TV/darknet_face_release/trained_models/face-shallow-size608-anchor5.weights"),
)

print("starting the FLASH Face Verification model")

try:
    import torch

    # Check GPU availability
    if not torch.cuda.is_available():
        print("WARNING: CUDA not available, face recognition may be slow or fail")

    # Try multiple possible model paths
    possible_paths = [
        f"/home/{username}/Desktop/FLASH_TV_v3/AdaFace/pretrained/adaface_ir101_webface12m.ckpt",
        f"/home/{username}/AdaFace/pretrained/adaface_ir101_webface12m.ckpt",
        f"/home/{username}/models/adaface_ir101_webface12m.ckpt",
    ]

    model_path = None
    for path in possible_paths:
        if os.path.exists(path):
            model_path = path
            print(f"Found face verification model at: {path}")
            break

    if model_path is None:
        print("WARNING: Face verification model not found, falling back to position-based tracking")
        print(f"Searched paths: {possible_paths}")
        face_verification = None
        face_processing = None
    else:
        face_verification = FLASHFaceVerification(model_path, num_identities=4)

        # Initialize face processing for verification
        face_processing = FaceProcessing(
            frame_resolution=[1080, 1920],
            detector_resolution=[342, 608],
            face_size=112,
            face_crop_offset=16,
            small_face_padding=7,
            small_face_size=65,
        )
        print("Face verification model loaded successfully")

except Exception as e:
    print(f"Error initializing face verification: {e}")
    print("Falling back to position-based tracking")
    face_verification = None
    face_processing = None

# Declare global variables for module scope
globals()["face_verification"] = face_verification
globals()["face_processing"] = face_processing


print("starting the batch cam")
q = Queue(maxsize=100)
stop_capture = False
frm_counter = 0
p1 = th.Thread(target=frame_write, args=(q, frm_counter, yolo_model))
p1.start()

# Note: participant_id here already includes device_id if present (e.g., "P1-3999001")
participant_id = sys.argv[1]
save_path = sys.argv[2]  # This is the full data directory path from GUI (e.g., /home/user/data/P1-3999028_data)

# Create directories inside the data directory path
# save_path is already the full data directory (e.g., /home/user/data/P1-3999028_data)
if not os.path.exists(save_path):
    os.makedirs(save_path)

# Using participant_id which already includes device_id from GUI
imsave_dir = os.path.join(save_path, str(participant_id) + "_faces")  # Gallery inside data directory
if not os.path.exists(imsave_dir):
    os.makedirs(imsave_dir)

frmsave_dir = os.path.join(save_path, str(participant_id) + "_face_frames")
if not os.path.exists(frmsave_dir):
    os.makedirs(frmsave_dir)

# Images are now saved directly to the main faces folder with correct naming
# No need for separate category folders anymore

show_face = None
sub_count = {"TC": 0, "Sib": 0, "Parent": 0, "Extra": 0}

selected_face_box = None
selected_face_data = None
selected_face_embedding = None
current_faces = []
current_frame_img = None
face_collection = {
    "tc": [None, None, None, None, None],
    "sib": [None, None, None, None, None],
    "parent": [None, None, None, None, None],
    "extra": [None, None, None, None, None],
}
mouse_x, mouse_y = 0, 0

frame_skip_counter = 0
face_recognition_interval = 3
face_embedding_cache = {}
last_matched_face = None


cv2.namedWindow("video_frames", cv2.WINDOW_NORMAL)
cv2.resizeWindow("video_frames", 1920, 1280)  # Increased height to accommodate panel
cv2.setMouseCallback("video_frames", mouse_click_callback)

record_frame = False
while True:
    if not q.empty():
        img, c, imgrgb, dboxes = q.get()
        # cv2.imwrite('/media/FLASH_SSD/523_face_frames/'+str(c).zfill(6)+'.png', img)

        # Store current faces and frame for mouse callback and face recognition
        current_faces = dboxes
        current_frame_img = img

        if c % 60 == 0:
            print(c)

        # BACKUP SAVING: Enhanced backup saving logic
        face_lost = False  # Track if face is lost

        if show_face is not None:  # Mode is active (T/S/P/E)
            if selected_face_box is not None:
                # Try to find and save the selected face
                matched_face = None

                # Use face recognition if available and embedding exists
                if selected_face_embedding is not None and face_verification is not None:
                    matched_face = find_matching_face(selected_face_embedding, img, dboxes, use_recognition=True)

                # Fallback to position-based matching if face recognition failed or unavailable
                if matched_face is None:
                    for detface in dboxes:
                        if (
                            area(detface) > 35.00
                            and detface["prob"] >= 0.11
                            and abs(detface["left"] - selected_face_box["left"]) < 15
                            and abs(detface["top"] - selected_face_box["top"]) < 15
                        ):
                            matched_face = detface
                            break

                if matched_face is not None:
                    # Save the matched face as backup
                    [x1, x2, y1, y2] = get_face(matched_face)
                    face = img[y1:y2, x1:x2, :]
                    face = cv2.resize(face, (160, 160))

                    # Save to backup folder
                    backup_output_path = os.path.join(
                        imsave_dir, show_face.lower(), str(c).zfill(6) + "_backup_" + str(sub_count[show_face]) + ".png"
                    )
                    cv2.imwrite(backup_output_path, face)

                    if record_frame:
                        fid = open(os.path.join(imsave_dir, show_face.lower() + "_frames.txt"), "a")
                        fid.write(str(c).zfill(6) + "\n")
                        fid.close()
                        record_frame = False

                    sub_count[show_face] += 1
                    face_lost = False
                else:
                    face_lost = True  # Face not found in current frame

            # If no face selected OR selected face is lost, save ALL detected faces as backup
            if selected_face_box is None or face_lost:
                face_idx = 0
                for detface in dboxes:
                    if area(detface) > 35.00 and detface["prob"] >= 0.11:
                        [x1, x2, y1, y2] = get_face(detface)
                        face = img[y1:y2, x1:x2, :]
                        face = cv2.resize(face, (160, 160))

                        # Save with face index to distinguish multiple faces
                        backup_output_path = os.path.join(
                            imsave_dir, show_face.lower(), f"{str(c).zfill(6)}_backup_face{face_idx}_{str(sub_count[show_face])}.png"
                        )
                        cv2.imwrite(backup_output_path, face)
                        face_idx += 1

                if face_idx > 0:  # At least one face was saved
                    if record_frame:
                        fid = open(os.path.join(imsave_dir, show_face.lower() + "_frames.txt"), "a")
                        fid.write(str(c).zfill(6) + "\n")
                        fid.close()
                        record_frame = False

                    sub_count[show_face] += 1
        else:
            record_frame = True

        # Draw rectangles with face tracking status
        imgrgbd = draw_rect(imgrgb, dboxes, show_face, face_lost=face_lost)
        imgrgbd_resized = cv2.resize(imgrgbd, (1920, 1080))

        # Create face verification panel
        face_panel = create_face_verification_panel(show_face)

        # Combine video frame and face panel
        combined_display = np.vstack([imgrgbd_resized, face_panel])

        cv2.imshow("video_frames", combined_display)
        cv2.setWindowTitle("video_frames", "video_frames:  " + str(c).zfill(6))

        # print(q.qsize(), q.empty())
        #
        pressed_key = cv2.waitKey(1) & 0xFF
        if pressed_key == ord("q"):
            stop_capture = True
            break
        elif pressed_key == ord("t"):
            show_face = "TC"
            print("TC mode selected - Click a face, then press 1-5 to save")
        elif pressed_key == ord("s"):
            show_face = "Sib"
            print("Sib mode selected - Click a face, then press 1-5 to save")
        elif pressed_key == ord("p"):
            show_face = "Parent"
            print("Parent mode selected - Click a face, then press 1-5 to save")
        elif pressed_key == ord("e"):
            show_face = "Extra"
            print("Extra mode selected - Click a face, then press 1-5 to save")
        elif pressed_key == ord("u"):
            show_face = None
            selected_face_box = None
            print("Unselected - Choose a category first")
        elif pressed_key == ord("r"):
            # R key to unselect current face (alternative to right-click)
            if selected_face_box is not None:
                print("Face unselected - backup saving stopped")
                selected_face_box = None
                selected_face_data = None
            else:
                print("No face was selected")
        # Handle 1-5 key presses for face numbering
        elif pressed_key >= ord("1") and pressed_key <= ord("5") and show_face is not None and selected_face_box is not None:
            face_num = pressed_key - ord("1")  # Convert to 0-4 index
            save_selected_face(img, face_num)
        elif pressed_key >= ord("1") and pressed_key <= ord("5") and (show_face is None or selected_face_box is None):
            print("Please select a category (T/S/P/E) and click on a face first")
    else:
        print("Queue is EMPTY")
        time.sleep(0.65)
