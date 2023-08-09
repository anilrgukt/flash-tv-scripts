import subprocess
import os
from glob import iglob
import re
from datetime import datetime as dt
import tkinter as tk
from tkinter.simpledialog import askstring
from tkinter.messagebox import askokcancel
#import json as serializer
import Pmw
from collections import defaultdict

"""
Needs dependency Pmw, pip install Pmw
Must have at least ~1 GB of free space in home folder to download all FLASH-TV logs (tegrastats excluded)
Edit normal and warning strings in the 'record_issues' function, anything else will be counted as an error
Edit device IDs and IPs in the __name__ == "__main__" condition
When prompted for the password, enter the password that is used to log in to the devices
Mouse over device square in the GUI to display the online/offline/warning/error tooltip
If a device is offline and not out on data collection, connect the device to the monitor and wireless keyboard/mouse and attempt to login
"""

def rsync_devices(devices: dict, password):

    offline_devices = []
    
    for name, dict in devices.items():

        if not os.path.isdir(f'FLASH_Internal_Testing_Logs/{name}/'):
            os.makedirs(f'FLASH_Internal_Testing_Logs/{name}/')

        for id, ip in dict.items():
                
                print(f"Proceeding with rsync for device {id} at {ip}")
                
                for rsync in [
                                subprocess.run(["sudo", "sshpass", "-p", f"{password}", "rsync", "-a", "--exclude", "*tegrastats*", "-P", "--timeout=5", "-e", 'ssh -o StrictHostKeyChecking=no', f"flashsys{id}@{ip}:~/data/123{id}_data", f"{os.path.expanduser('~')}/FLASH_Internal_Testing_Logs/{name}"],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE),
                            ]:
                    try: 

                        run = rsync
                        
                        run.check_returncode()
                        
                    except subprocess.CalledProcessError as e:

                        print(f'Error when trying to download from device {id} at {ip}: {e.returncode}: {e.stderr.decode("utf-8")}')

                        offline_devices.append(id)

                        continue

    return(offline_devices)

def record_issues(main_data_directory: str):
    
    #ignore = []

    files = [f for f in iglob(f'{main_data_directory}/**', recursive=True)
    if os.path.isfile(f)
    and re.match("^[\s\S]*123\d{3}_flash_logstderr.log", f)
    #and not any(ignored in f for ignored in ignore)
    ]
    
    # Add warning strings to this list
    warnings = [
                    "Corrupt JPEG data",
                    "DeprecationWarning",
                    "UserWarning",
                    "Deprecated in NumPy 1.20",
                    "Failed to load image Python extension",
                    ]
    
    # Add normal strings to this list
    normal = [
                    "Loading symbol saved by previous version",
                    "Symbol successfully upgraded!",
                    "Running performance tests",
                    "Resource temporarily unavailable",
                    ]
    
    # All other lines will be considered to be errors

    record = []

    for file in files:

        log_start_time = re.search("\d{2}_\w{3}_\d{4}_\d{2}-\d{2}-\d{2}_\w{3}", os.path.dirname(file))
        
        device_id = re.search("(?<=123)(\d{3})(?=_data)", file)[0]

        with open (file) as f:
        
            lines = f.readlines()

            filtered_lines = [line.strip() for line in lines if re.search("|".join(normal), line) == None and line]
        
            warnings = [line for line in filtered_lines if re.search("|".join(warnings), line) != None]

            errors = [line for line in filtered_lines if line not in warnings]
            
            if warnings or errors:

                if log_start_time != None:
                    
                    log_start_time = dt.strptime(log_start_time[0], "%d_%b_%Y_%H-%M-%S_%Z")

                else:

                    log_start_time = "current"

                record.append((device_id, log_start_time, warnings, errors))

    return(record)

def find_recent_issues(error_record: tuple, *args, logging=False, **kwargs):

    recent_warnings = defaultdict(list)
    recent_errors = defaultdict(list)

    for error_info in error_record:

        device, log_start_time, warnings, errors = error_info

        if log_start_time == "current":
            
            test_time = dt.now()

        else:

            test_time = log_start_time

        # 3 days defined as recent due to current protocol
        if (dt.today() - test_time).days <= 3:

            if logging == True:

                print(device, log_start_time, warnings, errors, "\n")
        
            if warnings:
                
                recent_warnings[device].append((log_start_time, list(set(warnings))))

            if errors:
                
                recent_errors[device].append((log_start_time, list(set(errors))))

    return (recent_warnings, recent_errors)

class InternalTestingMonitor(tk.Tk):

    def __init__(self, device_ips: dict):

        super().__init__()

        def check_password():

            password = askstring('Enter Password', 'Please enter the password to connect to the FLASH-TV devices:', show="*", parent=self)
            checked = askokcancel('Please confirm entered password:', f'Confirm Entered Password:\n\n{password}\n\nWarning: If the password is incorrect the application will fail to run', parent=self)

            if checked:
                
                canvas.itemconfig(last_updated, text=f"Updating...")

                return(password)
            
            else:

                return check_password()

        def update_device_status(password):

            offline_devices = rsync_devices(all_device_ips, password)

            recent_warnings, recent_errors = find_recent_issues(record_issues(f'{os.path.expanduser("~")}/FLASH_Internal_Testing_Logs'))

            #print(recent_warnings)

            #print(recent_errors)

            #print(offline_devices)

            for device_id, square in squares.items():

                if device_id in offline_devices:

                    canvas.itemconfig(square, fill='gray')

                    tooltip.tagbind(canvas, square, "Offline")

                else:

                    tooltip_text = ""

                    if device_id in list(recent_warnings.keys()):

                        for i, warning_tuple in enumerate(recent_warnings[device_id]):

                            warning_time, warnings = warning_tuple

                            displayed_warnings = "\n".join(w[0:150] for w in warnings)

                            canvas.itemconfig(square, fill='yellow')

                            tooltip_text += (f"Warnings from the {warning_time} log:\n{displayed_warnings}")

                        if device_id in list(recent_errors.keys()):

                            for i, error_tuple in enumerate(recent_errors[device_id]):

                                error_time, errors = error_tuple

                                displayed_errors = "\n".join(e[0:150] for e in errors)

                                canvas.itemconfig(square, fill='red')

                                tooltip_text += (f"Errors for log from time {error_time}:\n{displayed_errors}")

                        tooltip.tagbind(canvas, square, tooltip_text)

                    else:

                        canvas.itemconfig(square, fill='green')
                        tooltip.tagbind(canvas, square, "Online")

            canvas.itemconfig(last_updated, text=f"Last updated: {dt.now()}")

            # Call this function again after a delay (in milliseconds) to keep updating the colors
            self.after(5*60*1000, update_device_status)

        def update_canvas_size():

            # Calculate the bounding box of all items on the canvas
            self.update()
            bbox = canvas.bbox("all")
            if bbox:
                # Set the window size to fit the canvas content
                width = max(bbox[2], bbox[0]) + 80
                height = max(bbox[3], bbox[1]) + 30
                self.geometry(f"{width}x{height}")

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        # Create a canvas
        canvas = tk.Canvas(self, bg='white')
        canvas.pack(fill=tk.BOTH, expand=True)

        squares = {}

        old_devices = list(device_ips["Old_Devices"].keys())
        new_devices = list(device_ips["New_Devices"].keys())

        initial_y = 25
        initial_x = 100
        square_radius = 20
        square_spacing = 60

        tooltip = Pmw.Balloon(self)

        for initial_y, device_set in [(initial_y+50, old_devices), (initial_y+150, new_devices)]:
            for idx, device_id in enumerate(device_set):
                x = initial_x + idx * square_spacing
                square = canvas.create_rectangle(x - square_radius, initial_y - square_radius,
                                            x + square_radius, initial_y + square_radius, fill='turquoise')
                squares[device_id] = square
                tooltip.tagbind(canvas, square, "Waiting for data download")
                device_label = canvas.create_text(x, initial_y + square_radius + 10, text=device_id)
                update_canvas_size()

        old_device_label = canvas.create_text(canvas.winfo_width() / 2, 35, text="Old Devices")

        new_device_label = canvas.create_text(canvas.winfo_width() / 2, 135, text="New Devices")

        last_updated = canvas.create_text(canvas.winfo_width() / 2, 250, text="Waiting for password entry...")

        update_canvas_size()
                        
        self.title("FLASH-TV Internal Testing Monitor")

        self.deiconify()
        self.attributes('-topmost', 1)
        self.attributes('-topmost', 0)

        password = check_password()

        self.after(1000, lambda: update_device_status(password))

if __name__ == "__main__":

    old_device_ips = {
                    "001" : "10.51.20.10",
                    "004" : "10.51.21.7",
                    "007" : "10.23.6.39",
                    "008" : "10.51.27.131",
                    "014" : "10.51.17.49",
                }

    new_device_ips = {
                    "002" : "10.51.23.129",
                    "003" : "10.51.17.235",
                    "006" : "10.51.25.56",
                    "009" : "10.23.5.69",
                    "013" : "10.51.16.16", 
                    "015" : "10.51.23.213",
                }

    all_device_ips = {"Old_Devices" : old_device_ips,
                "New_Devices" : new_device_ips}

    app = InternalTestingMonitor(all_device_ips)

    app.mainloop()


