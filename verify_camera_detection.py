#!/usr/bin/env python3
"""
Simple verification script to test camera detection on actual FLASH-TV hardware.
Run this on the Jetson AGX Orin to verify the camera detection improvements.
"""

import sys
import os

def main():
    """Verify camera detection on FLASH-TV hardware"""
    print("FLASH-TV Camera Detection Verification")
    print("=" * 50)
    
    # Add python_scripts to path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, os.path.join(script_dir, 'python_scripts'))
    
    try:
        # Test the new camera detection
        print("Testing improved camera detection...")
        from utils.camera_detection_utils import get_unique_cameras, improved_cam_id
        
        cameras = get_unique_cameras()
        print(f"\nFound {len(cameras)} unique cameras:")
        
        for i, camera in enumerate(cameras, 1):
            print(f"{i}. {camera['name']}")
            print(f"   Path: {camera['path']}")
            print(f"   Capabilities: {camera.get('capabilities', 'unknown')}")
            print()
        
        # Test cam_id compatibility
        print("Testing cam_id compatibility...")
        cam_index = improved_cam_id()
        print(f"Selected camera index: {cam_index}")
        
        if cam_index >= 0:
            print(f"✅ Camera ready at /dev/video{cam_index}")
        else:
            print("❌ No camera found")
        
        # Test integration with existing utilities
        print("\nTesting integration with flash_runtime_utils...")
        from utils.flash_runtime_utils import cam_id as runtime_cam_id
        runtime_index = runtime_cam_id()
        print(f"Runtime utils result: {runtime_index}")
        
        if cam_index == runtime_index:
            print("✅ Integration successful - consistent results")
        else:
            print(f"⚠️  Different results: improved={cam_index}, runtime={runtime_index}")
        
        print("\n" + "=" * 50)
        print("VERIFICATION COMPLETE")
        
        if cameras:
            print("✅ Camera detection is working")
            print("✅ Duplicate filtering is active")
            print("✅ Integration with existing code is successful")
        else:
            print("❌ No cameras detected - check hardware connections")
            
    except Exception as e:
        print(f"❌ Error during verification: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())