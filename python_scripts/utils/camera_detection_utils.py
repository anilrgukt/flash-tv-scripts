"""
Camera detection utilities for FLASH-TV system.
Properly identifies unique physical cameras and filters out duplicate video device nodes.
"""

import os
import re
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Tuple


def get_unique_cameras() -> List[Dict[str, str]]:
    """
    Detect unique physical cameras by filtering out duplicate video device nodes.
    
    USB UVC cameras typically create multiple video device nodes:
    - /dev/video0 - main capture device  
    - /dev/video1 - metadata device (same physical camera)
    
    This function identifies only the main capture devices for each unique camera.
    
    Returns:
        List of dictionaries containing camera information:
        - path: Device path (e.g., "/dev/video0")
        - name: Camera name/model
        - number: Device number
        - capabilities: Device capabilities (capture, metadata, etc.)
        - is_capture_device: True if this is the main capture device
    """
    cameras = []
    
    try:
        # First, get the list of all video devices and their associated camera names
        result = subprocess.run(
            ["v4l2-ctl", "--list-devices"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            print(f"Warning: v4l2-ctl --list-devices failed: {result.stderr}")
            return _fallback_camera_detection()
        
        # Parse the output to group devices by camera
        camera_groups = _parse_v4l2_list_devices(result.stdout)
        
        # For each camera group, identify the main capture device
        for camera_name, device_paths in camera_groups.items():
            main_device = _identify_main_capture_device(camera_name, device_paths)
            if main_device:
                cameras.append(main_device)
                
    except subprocess.TimeoutExpired:
        print("Warning: v4l2-ctl command timed out")
        return _fallback_camera_detection()
    except Exception as e:
        print(f"Warning: Error during camera detection: {e}")
        return _fallback_camera_detection()
    
    return cameras


def _parse_v4l2_list_devices(output: str) -> Dict[str, List[str]]:
    """
    Parse v4l2-ctl --list-devices output to group devices by camera name.
    
    Example output:
    Logitech Webcam C930e (usb-0000:00:14.0-1):
        /dev/video0
        /dev/video1
    
    Args:
        output: Raw output from v4l2-ctl --list-devices
        
    Returns:
        Dictionary mapping camera names to list of device paths
    """
    camera_groups = {}
    current_camera = None
    
    for line in output.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
            
        # Check if this is a camera name line (ends with colon)
        if line.endswith(':'):
            # Extract camera name (remove USB info in parentheses)
            camera_name = re.sub(r'\s*\([^)]*\):?$', '', line).strip()
            current_camera = camera_name
            camera_groups[current_camera] = []
        elif line.startswith('/dev/video') and current_camera:
            # This is a device path
            camera_groups[current_camera].append(line)
    
    return camera_groups


def _identify_main_capture_device(camera_name: str, device_paths: List[str]) -> Optional[Dict[str, str]]:
    """
    Identify the main capture device from a list of video devices for the same camera.
    
    Args:
        camera_name: Name of the camera
        device_paths: List of /dev/video* paths for this camera
        
    Returns:
        Dictionary with camera information for the main capture device, or None if not found
    """
    if not device_paths:
        return None
    
    # Sort devices by number to check them in order
    sorted_devices = sorted(device_paths, key=lambda x: int(re.search(r'\d+', x).group()))
    
    for device_path in sorted_devices:
        device_info = _get_device_capabilities(device_path)
        if device_info and device_info['is_capture_device']:
            device_number = re.search(r'video(\d+)', device_path).group(1)
            return {
                'path': device_path,
                'name': camera_name,
                'number': device_number,
                'capabilities': device_info['capabilities'],
                'is_capture_device': True
            }
    
    # Fallback: if no clear capture device found, use the first one
    if sorted_devices:
        device_path = sorted_devices[0]
        device_number = re.search(r'video(\d+)', device_path).group(1)
        return {
            'path': device_path,
            'name': camera_name,
            'number': device_number,
            'capabilities': 'unknown',
            'is_capture_device': True
        }
    
    return None


def _get_device_capabilities(device_path: str) -> Optional[Dict[str, any]]:
    """
    Get capabilities of a video device to determine if it's a capture device.
    
    Args:
        device_path: Path to video device (e.g., "/dev/video0")
        
    Returns:
        Dictionary with device capabilities and capture device status
    """
    try:
        result = subprocess.run(
            ["v4l2-ctl", "--device", device_path, "--all"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            return None
        
        output = result.stdout
        
        # Check for video capture capability
        is_capture = False
        capabilities = []
        
        for line in output.split('\n'):
            line = line.strip().lower()
            
            # Look for capability indicators
            if 'video capture' in line and 'video capture' not in capabilities:
                capabilities.append('video capture')
                is_capture = True
            elif 'video output' in line and 'video output' not in capabilities:
                capabilities.append('video output')
            elif 'metadata' in line and 'metadata' not in capabilities:
                capabilities.append('metadata')
                # Metadata devices are typically not the main capture device
                if not any('capture' in cap for cap in capabilities):
                    is_capture = False
        
        # Additional heuristics
        if not capabilities:
            # If we can't determine capabilities, assume it's a capture device
            # unless the device number suggests it's a metadata device
            device_num = int(re.search(r'video(\d+)', device_path).group(1))
            # Odd-numbered devices are often metadata devices
            is_capture = device_num % 2 == 0
            capabilities = ['assumed capture']
        
        return {
            'capabilities': ', '.join(capabilities),
            'is_capture_device': is_capture
        }
        
    except (subprocess.TimeoutExpired, Exception) as e:
        print(f"Warning: Could not get capabilities for {device_path}: {e}")
        return None


def _fallback_camera_detection() -> List[Dict[str, str]]:
    """
    Fallback camera detection when v4l2-ctl is not available or fails.
    Simply lists /dev/video* devices without duplicate filtering.
    
    Returns:
        List of basic camera information dictionaries
    """
    cameras = []
    video_dir = Path("/dev")
    
    for device in video_dir.glob("video*"):
        if device.is_char_device():
            device_num = device.name.replace("video", "")
            cameras.append({
                'path': str(device),
                'name': f"Camera {device_num}",
                'number': device_num,
                'capabilities': 'unknown',
                'is_capture_device': True
            })
    
    return cameras


def get_camera_by_name(camera_names: List[str]) -> Optional[Tuple[str, int]]:
    """
    Find a camera by name from a list of preferred camera names.
    This is compatible with the existing cam_id() function usage.
    
    Args:
        camera_names: List of camera names to search for (in order of preference)
        
    Returns:
        Tuple of (device_path, camera_index) or None if not found
    """
    cameras = get_unique_cameras()
    
    for preferred_name in camera_names:
        for camera in cameras:
            if preferred_name in camera['name']:
                device_path = camera['path']
                camera_index = int(camera['number'])
                print(f"CAMERA identified: {camera['name']} at {device_path} (index {camera_index})")
                return device_path, camera_index
    
    # If no preferred camera found, return the first available
    if cameras:
        first_camera = cameras[0]
        device_path = first_camera['path']
        camera_index = int(first_camera['number'])
        print(f"CAMERA identified (fallback): {first_camera['name']} at {device_path} (index {camera_index})")
        return device_path, camera_index
    
    print("No cameras detected")
    return None


def improved_cam_id() -> int:
    """
    Improved version of cam_id() function that properly handles duplicate video devices.
    Compatible replacement for the existing cam_id() function.
    
    Returns:
        Camera index for use with cv2.VideoCapture, or -1 if no camera found
    """
    # Preferred camera names (in order of preference)
    preferred_cameras = [
        "Logitech Webcam C930e",
        "Anker PowerConf C300: Anker Pow",
        "HD Pro Webcam C920"
    ]
    
    result = get_camera_by_name(preferred_cameras)
    
    if result:
        device_path, camera_index = result
        return camera_index
    else:
        return -1


# Compatibility function for existing code
def cam_id():
    """
    Compatibility wrapper for existing cam_id() usage.
    """
    return improved_cam_id()


if __name__ == "__main__":
    # Test the camera detection
    print("Testing camera detection...")
    cameras = get_unique_cameras()
    
    print(f"\nFound {len(cameras)} unique cameras:")
    for i, camera in enumerate(cameras, 1):
        print(f"{i}. {camera['name']}")
        print(f"   Device: {camera['path']}")
        print(f"   Capabilities: {camera['capabilities']}")
        print()
    
    # Test cam_id function
    cam_index = improved_cam_id()
    print(f"Camera index for capture: {cam_index}")