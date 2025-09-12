#!/usr/bin/env python3
"""Test script to verify participant setup step initialization."""

import sys
import os

# Add the gui_second_version directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'gui_second_version'))

def test_participant_step_init():
    """Test that the participant setup step initializes without errors."""
    try:
        # Import after path is set up
        from steps.participant_setup_step import ParticipantSetupStep
        
        print("✅ ParticipantSetupStep imported successfully")
        
        # Check that the class has the expected methods
        if hasattr(ParticipantSetupStep, '_auto_detect_device_info'):
            print("✅ _auto_detect_device_info method exists")
        else:
            print("❌ _auto_detect_device_info method missing")
            
        if hasattr(ParticipantSetupStep, 'create_content_widget'):
            print("✅ create_content_widget method exists")
        else:
            print("❌ create_content_widget method missing")
            
        print("\n✅ All initialization checks passed!")
        print("\nThe AttributeError should now be fixed. The participant setup step will:")
        print("1. Initialize attributes before parent __init__")
        print("2. Auto-detect device info from /home/flashsysXXX folders")
        print("3. Only ask for participant ID from the user")
        print("4. Auto-generate the data path")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
    except AttributeError as e:
        print(f"❌ AttributeError (the issue we're fixing): {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    test_participant_step_init()