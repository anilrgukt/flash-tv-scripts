#!/usr/bin/env python3
"""
WiFi connection setup script that checks for existing credentials
in .bashrc and prompts for password if not found.
Supports multiple hotspots (HOTSPOT1, HOTSPOT2, HOTSPOT3).
"""

import os
import sys
import subprocess
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QInputDialog, QMessageBox


# Configuration - Define your hotspots here
HOTSPOT_CONFIG = {
    1: {"ssid": "HomeNetwork"},      # Primary network
    2: {"ssid": "MobileHotspot"},    # Secondary network  
    3: {"ssid": ""},                  # Reserved for future use
}


def get_hotspot_credentials_from_bashrc(hotspot_num):
    """Check if hotspot credentials exist in .bashrc"""
    bashrc_path = Path.home() / '.bashrc'
    ssid_var = f"HOTSPOT{hotspot_num}_SSID"
    psk_var = f"HOTSPOT{hotspot_num}_PSK"
    
    if bashrc_path.exists():
        # Source .bashrc and get environment variables
        try:
            result = subprocess.run(
                ['bash', '-c', f'source {bashrc_path} && echo "${{{ssid_var}}}|${{{psk_var}}}"'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                output = result.stdout.strip()
                if '|' in output:
                    ssid, psk = output.split('|', 1)
                    return ssid if ssid else None, psk if psk else None
        except Exception as e:
            print(f"Error reading .bashrc: {e}")
    
    return None, None


def save_hotspot_credentials_to_bashrc(hotspot_num, ssid, psk):
    """Save hotspot credentials to .bashrc"""
    bashrc_path = Path.home() / '.bashrc'
    ssid_var = f"HOTSPOT{hotspot_num}_SSID"
    psk_var = f"HOTSPOT{hotspot_num}_PSK"
    
    try:
        # Check if header exists
        with open(bashrc_path, 'r') as f:
            content = f.read()
            has_header = "# WiFi Hotspot Configuration" in content
        
        with open(bashrc_path, 'a') as f:
            if not has_header:
                f.write('\n')
                f.write('# WiFi Hotspot Configuration (added by setup_wifi_connection.py)\n')
            f.write(f'export {ssid_var}="{ssid}"\n')
            f.write(f'export {psk_var}="{psk}"\n')
        return True
    except Exception as e:
        print(f"Error saving to .bashrc: {e}")
        return False


def create_network_connection(hotspot_num, ssid, psk):
    """Create NetworkManager connection using nmcli only if it doesn't exist"""
    connection_name = f"FlashTV-Hotspot{hotspot_num}"
    
    # Check if connection already exists
    check_cmd = ['nmcli', 'connection', 'show', connection_name]
    result = subprocess.run(check_cmd, capture_output=True)
    
    if result.returncode == 0:
        print(f"Connection '{connection_name}' already exists. Skipping creation.")
        
        # Check if password needs updating
        get_psk_cmd = ['nmcli', '-s', '-g', 'wifi-sec.psk', 'connection', 'show', connection_name]
        psk_result = subprocess.run(get_psk_cmd, capture_output=True, text=True)
        existing_psk = psk_result.stdout.strip() if psk_result.returncode == 0 else ""
        
        if existing_psk != psk:
            print(f"Updating password for existing connection...")
            modify_cmd = ['nmcli', 'connection', 'modify', connection_name, 'wifi-sec.psk', psk]
            subprocess.run(modify_cmd)
        
        return True
    
    # Connection doesn't exist, create it
    print(f"Creating connection for Hotspot {hotspot_num}...")
    
    # Set priority (higher number = higher priority)
    # Hotspot 1 gets highest priority, then 2, then 3
    priority = 11 - hotspot_num
    
    # Create new connection
    create_cmd = [
        'nmcli', 'connection', 'add',
        'type', 'wifi',
        'con-name', connection_name,
        'ssid', ssid,
        'wifi-sec.key-mgmt', 'wpa-psk',
        'wifi-sec.psk', psk,
        'connection.autoconnect', 'yes',
        'connection.autoconnect-priority', str(priority)
    ]
    
    result = subprocess.run(create_cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"Hotspot {hotspot_num} connection created successfully!")
        return True
    else:
        print(f"Failed to create Hotspot {hotspot_num} connection: {result.stderr}")
        return False


def prompt_for_password_gui(hotspot_num, ssid):
    """GUI prompt for WiFi password using PyQt6"""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    # Create input dialog without password masking
    password, ok = QInputDialog.getText(
        None,
        "WiFi Password Required",
        f"Enter password for Hotspot {hotspot_num}: {ssid}\n\n"
        "Note: Password will be visible as you type",
        echo=QInputDialog.EchoMode.Normal  # Show password as typed
    )
    
    if ok and password:
        # Ask if user wants to save
        reply = QMessageBox.question(
            None,
            "Save Password",
            f"Save password for {ssid} to .bashrc for future use?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        save_to_bashrc = reply == QMessageBox.StandardButton.Yes
        return password, save_to_bashrc
    
    return None, False


def prompt_for_password_cli(hotspot_num, ssid):
    """CLI prompt for WiFi password"""
    print(f"\nPassword for Hotspot {hotspot_num} '{ssid}' not found in .bashrc")
    print("Note: Password will be visible as you type")
    password = input(f"Enter password for {ssid}: ")
    
    if password:
        save_response = input("Save password to .bashrc for future use? (y/n): ")
        save_to_bashrc = save_response.lower().startswith('y')
        return password, save_to_bashrc
    
    return None, False


def setup_hotspot(hotspot_num):
    """Setup a single hotspot connection"""
    # Get SSID from config or bashrc
    ssid_from_bashrc, psk = get_hotspot_credentials_from_bashrc(hotspot_num)
    
    # Use configured SSID or from bashrc
    ssid = ssid_from_bashrc or HOTSPOT_CONFIG.get(hotspot_num, {}).get("ssid", "")
    
    if not ssid:
        print(f"Hotspot {hotspot_num} not configured (no SSID)")
        return False
    
    print(f"\nSetting up Hotspot {hotspot_num}: {ssid}")
    
    # If no password found, prompt for it
    if not psk:
        # Try GUI first, fall back to CLI
        try:
            # Check if we're in a GUI environment
            if os.environ.get('DISPLAY'):
                psk, save_to_bashrc = prompt_for_password_gui(hotspot_num, ssid)
            else:
                psk, save_to_bashrc = prompt_for_password_cli(hotspot_num, ssid)
        except:
            # Fallback to CLI if GUI fails
            psk, save_to_bashrc = prompt_for_password_cli(hotspot_num, ssid)
        
        if not psk:
            print(f"No password entered for Hotspot {hotspot_num}. Skipping...")
            return False
        
        # Save to .bashrc if requested
        if save_to_bashrc:
            if save_hotspot_credentials_to_bashrc(hotspot_num, ssid, psk):
                print(f"Password for Hotspot {hotspot_num} saved to .bashrc")
            else:
                print(f"Warning: Could not save password for Hotspot {hotspot_num}")
    else:
        print(f"Using credentials from .bashrc for Hotspot {hotspot_num}")
    
    # Create network connection
    return create_network_connection(hotspot_num, ssid, psk)


def try_connect_to_available_hotspot():
    """Try to connect to any available hotspot in cyclical order with retries"""
    import time
    
    print("\nAttempting to connect to available networks...")
    
    MAX_ATTEMPTS = 10  # Maximum number of cycles to try
    attempt = 0
    
    while attempt < MAX_ATTEMPTS:
        attempt += 1
        print(f"\nConnection attempt cycle {attempt} of {MAX_ATTEMPTS}")
        
        for i in [1, 2, 3]:
            connection_name = f"FlashTV-Hotspot{i}"
            
            # Check if connection profile exists
            check_cmd = ['nmcli', 'connection', 'show', connection_name]
            result = subprocess.run(check_cmd, capture_output=True)
            
            if result.returncode == 0:
                print(f"  Trying Hotspot {i}...")
                connect_cmd = ['nmcli', 'connection', 'up', connection_name]
                connect_result = subprocess.run(connect_cmd, capture_output=True, text=True)
                
                if connect_result.returncode == 0:
                    print(f"  ✓ Successfully connected to Hotspot {i}!")
                    return True
                else:
                    print(f"    Hotspot {i} not available")
            else:
                print(f"    Hotspot {i} not configured")
            
            # Wait 5 seconds before trying next hotspot
            if i < 3:
                print("    Waiting 5 seconds before trying next hotspot...")
                time.sleep(5)
        
        # If still not connected after trying all hotspots, wait before next cycle
        if attempt < MAX_ATTEMPTS:
            print("  No hotspots available. Waiting 5 seconds before retry...")
            time.sleep(5)
    
    print(f"\nCould not connect to any hotspot after {MAX_ATTEMPTS} attempts.")
    print("Networks will continue trying to auto-connect in the background.")
    return False


def main():
    print("=== WiFi Multi-Hotspot Setup ===")
    
    # Setup all hotspots
    configured_count = 0
    for hotspot_num in [1, 2, 3]:
        if setup_hotspot(hotspot_num):
            configured_count += 1
    
    if configured_count == 0:
        print("\nError: No hotspots configured!")
        sys.exit(1)
    
    # Try to connect to an available network
    if try_connect_to_available_hotspot():
        print("\nSetup complete! Connected to network.")
    else:
        print("\nSetup complete! Configured hotspots will auto-connect when available.")
        print("Priority order: Hotspot 1 > Hotspot 2 > Hotspot 3")
    
    sys.exit(0)


if __name__ == "__main__":
    main()