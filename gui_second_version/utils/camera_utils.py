"""Camera detection and management utilities for FLASH-TV GUI Setup Wizard.

This module provides reusable camera detection and testing functionality,
eliminating code duplication between camera_setup_step and gaze_detection_testing_step.
"""

from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def list_available_cameras() -> List[Tuple[int, str]]:
    """List all available camera devices on the system.

    This function scans /dev/video* devices and returns a list of
    available cameras with their indices and device paths.

    Returns:
        List of (index, device_path) tuples, sorted by index

    Example:
        >>> cameras = list_available_cameras()
        >>> for index, path in cameras:
        ...     print(f"Camera {index}: {path}")
        Camera 0: /dev/video0
        Camera 2: /dev/video2

    Notes:
        - Only devices that match /dev/video[0-9]+ are included
        - Returns empty list if no cameras found
        - Devices are sorted numerically by index
    """
    cameras = []

    try:
        # Check /dev/video* devices
        video_devices = Path("/dev").glob("video*")

        for device in sorted(video_devices):
            # Extract index from device name
            match = re.search(r"video(\d+)", device.name)
            if match:
                index = int(match.group(1))
                cameras.append((index, str(device)))

        logger.info(f"Found {len(cameras)} camera devices: {cameras}")

    except Exception as e:
        logger.error(f"Error listing cameras: {e}", exc_info=True)

    return cameras


def get_camera_info(camera_index: int) -> Optional[Dict[str, Any]]:
    """Get detailed information about a camera device.

    Uses v4l2-ctl to query camera capabilities including supported
    pixel formats and resolutions.

    Args:
        camera_index: Camera index (e.g., 0 for /dev/video0)

    Returns:
        Dictionary containing camera info, or None if not accessible:
        {
            'index': int,
            'device': str,
            'formats': List[str],
            'resolutions': List[str]
        }

    Example:
        >>> info = get_camera_info(0)
        >>> if info:
        ...     print(f"Formats: {info['formats']}")
        ...     print(f"Resolutions: {info['resolutions']}")
        Formats: ['MJPG', 'YUYV']
        Resolutions: ['1920x1080', '1280x720', '640x480']

    Notes:
        - Requires v4l2-ctl to be installed
        - Returns None if camera is not accessible
        - Timeout set to 10 seconds to prevent hanging
    """
    device_path = f"/dev/video{camera_index}"

    try:
        logger.debug(f"Querying camera info for {device_path}")

        result = subprocess.run(
            ["v4l2-ctl", "--device", device_path, "--list-formats-ext"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            logger.warning(f"Camera {camera_index} not accessible: {result.stderr}")
            return None

        # Parse output to extract formats and resolutions
        formats = []
        resolutions = []

        for line in result.stdout.split("\n"):
            # Look for pixel format lines
            if "Pixel Format" in line:
                match = re.search(r"'(\w+)'", line)
                if match:
                    formats.append(match.group(1))

            # Look for resolution lines
            elif "Size:" in line:
                match = re.search(r"(\d+)x(\d+)", line)
                if match:
                    resolutions.append(f"{match.group(1)}x{match.group(2)}")

        camera_info = {
            "index": camera_index,
            "device": device_path,
            "formats": list(set(formats)),  # Remove duplicates
            "resolutions": list(set(resolutions)),
        }

        logger.debug(f"Camera {camera_index} info: {camera_info}")
        return camera_info

    except subprocess.TimeoutExpired:
        logger.error(f"Timeout getting info for camera {camera_index}")
        return None
    except FileNotFoundError:
        logger.error("v4l2-ctl not found - please install v4l-utils")
        return None
    except Exception as e:
        logger.error(
            f"Error getting camera info for {camera_index}: {e}", exc_info=True
        )
        return None


def test_camera_capture(camera_index: int, timeout_seconds: int = 5) -> bool:
    """Test if a camera can capture frames.

    Attempts to open the camera with OpenCV and capture a single frame
    to verify the camera is functional.

    Args:
        camera_index: Camera index to test
        timeout_seconds: Maximum time to wait for camera (default: 5)

    Returns:
        True if camera can capture frames, False otherwise

    Example:
        >>> if test_camera_capture(0):
        ...     print("Camera 0 is working!")
        ... else:
        ...     print("Camera 0 failed")
        Camera 0 is working!

    Notes:
        - Requires OpenCV (cv2) to be installed
        - Camera is released immediately after test
        - Returns False if camera cannot be opened or frame capture fails
    """
    try:
        import cv2

        logger.debug(f"Testing camera {camera_index}")

        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            logger.warning(f"Camera {camera_index} could not be opened")
            return False

        # Try to read a frame
        ret, frame = cap.read()
        cap.release()

        if ret and frame is not None:
            logger.info(f"Camera {camera_index} test successful")
            return True
        else:
            logger.warning(f"Camera {camera_index} failed to capture frame")
            return False

    except ImportError:
        logger.error("OpenCV (cv2) not installed - cannot test camera")
        return False
    except Exception as e:
        logger.error(f"Error testing camera {camera_index}: {e}", exc_info=True)
        return False


def find_working_camera() -> Optional[int]:
    """Find the first working camera on the system.

    Scans all available cameras and returns the index of the first
    camera that can successfully capture frames.

    Returns:
        Index of first working camera, or None if no cameras work

    Example:
        >>> camera_index = find_working_camera()
        >>> if camera_index is not None:
        ...     print(f"Found working camera at index {camera_index}")
        ... else:
        ...     print("No working cameras found")
        Found working camera at index 0

    Notes:
        - Tests cameras in numerical order
        - Stops at first working camera found
        - Returns None if no cameras are found or none work
    """
    logger.info("Searching for working camera...")

    cameras = list_available_cameras()

    if not cameras:
        logger.warning("No cameras found on system")
        return None

    for index, device_path in cameras:
        logger.debug(f"Testing camera {index} at {device_path}")
        if test_camera_capture(index):
            logger.info(f"Found working camera: index {index}")
            return index

    logger.warning("No working cameras found")
    return None


def get_camera_display_name(camera_index: int) -> str:
    """Get a display-friendly name for a camera.

    Args:
        camera_index: Camera index

    Returns:
        Human-readable camera name

    Example:
        >>> name = get_camera_display_name(0)
        >>> print(name)
        Camera 0 (/dev/video0)
    """
    return f"Camera {camera_index} (/dev/video{camera_index})"


def format_camera_info(info: Dict[str, Any]) -> str:
    """Format camera information for display.

    Args:
        info: Camera info dictionary from get_camera_info()

    Returns:
        Formatted string for display

    Example:
        >>> info = get_camera_info(0)
        >>> print(format_camera_info(info))
        Camera 0 (/dev/video0)
        Formats: MJPG, YUYV
        Resolutions: 1920x1080, 1280x720
    """
    if not info:
        return "Camera information not available"

    lines = [f"Camera {info['index']} ({info['device']})"]

    if info.get("formats"):
        lines.append(f"Formats: {', '.join(info['formats'])}")

    if info.get("resolutions"):
        # Show first few resolutions
        resolutions = info["resolutions"][:5]
        if len(info["resolutions"]) > 5:
            resolutions.append("...")
        lines.append(f"Resolutions: {', '.join(resolutions)}")

    return "\n".join(lines)
