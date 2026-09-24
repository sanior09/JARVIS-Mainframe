"""
Purpose: check iPhone battery level
Created: 2026-08-16 22:48:28.894702
"""

import subprocess

def check_iphone_battery():
    try:
        # Use the `ideviceinfo` command to get the battery level
        output = subprocess.check_output(['ideviceinfo', '-q', 'com.apple.mobile.battery']).decode('utf-8')
        # Parse the output to get the battery level
        battery_level = int(output.split("\n")[0].split(": ")[1])
        return battery_level
    except Exception as e:
        print(f"An error occurred: {e}")
        return None