import subprocess
import os
from glob import iglob
import re
from datetime import timedelta, datetime as dt
import tkinter as tk
from tkinter.simpledialog import askstring
from tkinter.messagebox import askokcancel
import json
import Pmw
from collections import defaultdict, namedtuple
import asyncio, aiofiles

# Define the AcknowledgedIssue named tuple
AcknowledgedIssue = namedtuple('AcknowledgedIssue', ['issue_type','issue', 'log_path', 'acknowledgement_reason'])

global deobfuscate
deobfuscate = ""

"""
Needs dependency Pmw, pip install Pmw
Must have at least ~1 GB of free space in home folder to download all FLASH-TV logs (tegrastats excluded)
Edit normal and warning strings in the 'find_all_logs_with_issues' function, anything else will be counted as an error
Edit device IDs and IPs in the __name__ == "__main__" condition
When prompted for the password, enter the password that is used to log_path in to the devices
Mouse over device square in the GUI to display the online/offline/warning/error tooltip
If a device is offline and not out on data collection, connect the device to the monitor and wireless keyboard/mouse and attempt to login
"""
def save_acknowledged_issue_to_file(issue_type, issue, log_path, acknowledgement_reason):

    # Create a new instance of AcknowledgedIssue
    new_acknowledged_issue = AcknowledgedIssue(issue_type, issue, log_path, acknowledgement_reason)

    acknowledged_issues_file = f"{deobfuscate.upper()}_acknowledged_issues.json"
    
    # Load existing acknowledged issues or create an empty list
    acknowledged_issues = load_acknowledged_issues_from_file()
    
    # Check if the issue is already in the list
    if new_acknowledged_issue not in acknowledged_issues:
        # Add the new instance to the list of acknowledged issues
        acknowledged_issues.append(new_acknowledged_issue)
        
    # Save the updated list to the JSON log_path
    with open(acknowledged_issues_file, 'w') as f:
        json.dump([item._asdict() for item in acknowledged_issues], f)

def load_acknowledged_issues_from_file():

    acknowledged_issues_file = f"{deobfuscate.upper()}_acknowledged_issues.json"
    
    try:
        with open(acknowledged_issues_file) as f:
            acknowledged_issues_data = json.load(f)
            # Convert JSON data to list of AcknowledgedIssue named tuples
            acknowledged_issues = [AcknowledgedIssue(**item) for item in acknowledged_issues_data]
        return acknowledged_issues
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def extract_device_id(log_path):

    return (
        device_id_match[0]
        if (
            device_id_match := re.search(
                r"(?<=123)(\d{3})(?=_data)", log_path
            )
        )
        else None
    )

def extract_log_start_time(log_path):
        
    return (
        dt.strptime(log_start_time_match[0], "%d_%b_%Y_%H-%M-%S_%Z")
        if (
            log_start_time_match := re.search(
                r"\d{2}_\w{3}_\d{4}_\d{2}-\d{2}-\d{2}_\w{3}", log_path
            )
        )
        else "Current"
    )

class DetailsDisplay:

    def __init__(self, parent, selected_device, *args, **kwargs):

        self.parent = parent
        self.selected_device = selected_device
        self.window = tk.Toplevel(parent)
        self.window.title("Device Details")

        x = parent.winfo_x() + (parent.winfo_width() - self.window.winfo_reqwidth()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.window.winfo_reqheight()) // 2

        self.window.geometry(f"+{x}+{y}")

        # Create and add widgets to the new window
        device_label = tk.Label(self.window, text=f"{self.selected_device.id}")
        device_label.grid(row=0, column=1)

        self.create_issue_labels_and_acknowledgement_buttons()
    
    def create_issue_labels_and_acknowledgement_buttons(self):

        if self.selected_device.issues:

            for index, (issue_type, issue, log_path) in enumerate(self.selected_device.issues):

                label_text = f"{issue_type}: {issue}"
                label = tk.Label(self.window, text=label_text)
                label.grid(row=index, column=0)

                acknowledge_button = tk.Button(
                        self.window, text=f"Acknowledge {issue_type}",
                        command=lambda idx=index: self.create_acknowledgement_entry_window(issue_type, issue, log_path))
                acknowledge_button.grid(row=index, column=2)
        
        else:
            
            label_text = "No issues for this device"
            label = tk.Label(self.window, text=label_text)
            label.grid(row=1, column=1)

    def create_acknowledgement_entry_window(self, issue_type, issue, log_path):
            
            device_id = extract_device_id(log_path)

            log_start_time = extract_log_start_time(log_path)

            prompt = (
                f"Please enter the reason for acknowledging the {issue_type}\n\n"
                f"{issue}\n\n"
                f"on the device:\n\n"
                f"{device_id}\n\n"
                f"in the {log_start_time} log:"
            )

            acknowledgement_reason = askstring(
                "Enter Acknowledgement Reason",
                prompt,
                show="*",
                parent=self.window,
            )

            if acknowledgement_reason is not None:
                if checked := askokcancel(
                    "Confirm Acknowledgement Reason",
                    f"Please Confirm Acknowledgement Reason:\n\n{acknowledgement_reason}",
                    parent=self.window):
                    save_acknowledged_issue_to_file(issue_type, issue, log_path, acknowledgement_reason)

class DeviceSquare:

    def __init__(self, parent, device_set, id, ip, canvas, x, y, tooltip,
                *args, color='turquoise', radius=20, **kwargs):
        self.parent = parent
        self.device_set = device_set
        self.id = id
        self.ip = ip
        self._status = 'Updating...'
        self.canvas = canvas
        self.x = x
        self.y = y
        self.color = color
        self.tooltip = tooltip
        self.recent_logs_with_issues = {}
        self.issues = []
        self.square = self.canvas.create_rectangle(
            x - radius, y - radius, x + radius, y + radius, fill=self.color
        )
        self.canvas.tag_bind(self.square, "<Button-1>", self.device_handle_square_click)

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        self._status = value
        self.device_update_appearance()

    async def device_rsync(self, password, save_folder):
        
        try:
            
            self.status = 'Offline'

            rsync_command = [
                "sudo",
                "sshpass",
                "-p",
                f"{password}",
                "rsync",
                "-a",
                "-P",
                "--timeout=5",
                "-e",
                "ssh -o StrictHostKeyChecking=no",
                f"{deobfuscate}sys{self.id}@{self.ip}:data/123{self.id}_data",
                f"{save_folder}/{deobfuscate.upper()}_Internal_Testing_Logs/{self.device_set.replace(' ', '_')}",
            ]
            process = await asyncio.create_subprocess_exec(
                            *rsync_command,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE
                        )
            _, stderr = await process.communicate()

            if process.returncode != 0:
                print(
                    f'Error when trying to download from device {self.id} at {self.ip}: {process.returncode}: {stderr.decode("utf-8")}'
                )

            else:
                self.status = 'Online'

        except Exception as e:
            print(f"Exception occurred: {e}")

    async def device_process_recent_logs_with_issues(self, logs_with_acknowledged_issues, normal_lines, warning_lines):
        
        valid_log_paths = [
            log_path for log_path in self.recent_logs_with_issues.keys()
            if os.path.isfile(log_path)
            and log_path not in logs_with_acknowledged_issues.items()
        ]

        for log_path in valid_log_paths:

            async with aiofiles.open(log_path) as log:
                
                log_lines = await log.readlines()

            issues = [
                f"{log_line.strip()}\n"
                for log_line in log_lines
                if log_line
                and all(
                    normal_line not in log_line
                    for normal_line in normal_lines
                )
            ]

            self.issues.append([
                ('Warning', issue, log_path) 
                for issue in issues
                if any(
                    warning_line in issue
                    for warning_line in warning_lines)
            ])

            self.issues.append([
                ('Error', issue, log_path) 
                for issue in issues
                if issue not in self.issues
            ])

        if "Warning" in self.issues:
            self.status = 'Has Warnings'

        if "Error" in self.issues:
            self.status = 'Has Errors'

        if "Warning" in self.issues and "Error" in self.issues:
            self.status = 'Has Warnings and Errors'

    def device_handle_square_click(self, event):

        self.parent.update_after_device_selection(self)

    def device_update_appearance(self):

        status_color_map = {
            'Offline' : 'gray',
            'Online' : 'green',
            'Has Warnings' : 'yellow',
            'Has Errors' : 'red',
            'Has Warnings and Errors' : 'red'
        }
        
        self.color = status_color_map[self.status]

        self.canvas.itemconfig(self.square, self.color)
        self.tooltip.tagbind(self.canvas, self.square, self.status)

class InternalTestingMonitor(tk.Tk):

    INITIAL_Y = 75
    INITIAL_X = 75
    SQUARE_SPACING = 60

    def __init__(
        self,
        *args,
        devices_and_ips: dict,
        normal_lines: list,
        warning_lines: list,
        recent_timespan: int = (3 + 1),  # In days, default interval of 3 days plus 1 extra in case checked next day
        update_interval: int = 300,  # In seconds, default interval of 300 seconds (5 minutes)
        save_folder = f'{os.path.expanduser("~")}',  # The default save folder is the home folder
        **kwargs,
    ):
        super().__init__()

        self.devices_and_ips = devices_and_ips
        self.normal_lines = normal_lines
        self.warning_lines = warning_lines
        self.recent_timespan = recent_timespan
        self.save_folder = save_folder
        self.update_interval = update_interval

        self.selected_device = None

        self.offline_devices = []
        self.logs_with_issues = []
        self.logs_with_acknowledged_issues = load_acknowledged_issues_from_file()
        self.recent_issues = defaultdict(list)

        self.tooltip = Pmw.Balloon(self) # type: ignore
        self.device_squares = {}  # Initialize the device_squares dictionary

        self.create_widgets()

        self.password = None

        self.get_and_confirm_password(self.update_devices('async'))

    def create_device_sets(self):

        y = InternalTestingMonitor.INITIAL_Y

        for device_set_name, device_dict in self.devices_and_ips.items():

            for index, (device_id, device_ip) in enumerate(device_dict.items()):

                x = InternalTestingMonitor.INITIAL_X + index * InternalTestingMonitor.SQUARE_SPACING
                device_square = DeviceSquare(
                    parent=self,
                    device_set=device_set_name,
                    id=device_id,
                    ip=device_ip,
                    status='Offline',
                    canvas=self.canvas,
                    x=x,
                    y=y,
                    radius=20,
                    tooltip=self.tooltip,
                )

                self.device_squares[device_id] = device_square

            self.update_canvas_size()
            self.canvas.create_text(self.canvas.winfo_width() / 2, y - 40, text=device_set_name)
            y += 100

    def create_sidebar(self):
        # Create the sidebar frame
        self.sidebar = tk.Frame(self, bg='lightgray')
        self.sidebar.grid(row=0, column=1, sticky='nsew')

        self.warning_label_var = tk.StringVar(value="Warnings: Click a device")
        self.warning_label = tk.Label(self.sidebar, textvariable=self.warning_label_var)
        self.warning_label.pack()

        self.error_label_var = tk.StringVar(value="Errors: Click a Device")
        self.error_label = tk.Label(self.sidebar, textvariable=self.error_label_var)
        self.error_label.pack()

        self.details_window_button = tk.Button(
            self.sidebar,
            text="Open Details",
            command=self.create_details_window,
            state='disabled')
        self.details_window_button.pack()

    def create_widgets(self):
          
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        # Create the canvas
        self.canvas = tk.Canvas(self, bg='white')
        self.canvas.grid(row=0, column=0, sticky='nsew')

        self.create_device_sets()

        self.create_sidebar()

        # Create last_updated element
        self.last_updated = self.canvas.create_text(
            self.canvas.winfo_width() / 2, 250, text="Waiting for password entry..."
        )

    def monitor_update_device_status(self):

        return

        self.rsync_devices()

        self.find_issues()

        for device_id, device_square in self.device_squares.items():
            pass

        self.update_last_updated_time()
        self.after(self.update_interval * 1000, self.monitor_update_device_status)

    def create_details_window(self):

        if hasattr(self, 'details_display') and self.details_display:
            self.details_display.window.destroy()

        self.details_display = DetailsDisplay(self, self.selected_device)

    def update_after_device_selection(self, device_square):

        self.selected_device = device_square  # Update selected_device

        warning_count = sum(item[0] == 'Warning' for item in self.selected_device.issues)
        error_count = sum(item[0] == 'Error' for item in self.selected_device.issues)

        self.warning_label_var.set(f"Warnings: {warning_count}")
        self.error_label_var.set(f"Errors: {error_count}")

        # Enable the button when selected_device is not None
        if self.selected_device is not None:
            self.details_window_button.config(state='normal')
        else:
            self.details_window_button.config(state='disabled')

    def update_canvas_size(self):

        self.update()
        if bbox := self.canvas.bbox("all"):
            width = max(bbox[2], bbox[0]) + InternalTestingMonitor.INITIAL_X*2
            height = max(bbox[3], bbox[1]) + InternalTestingMonitor.INITIAL_Y
            self.geometry(f"{width}x{height}")
        self.update()

    def rsync_devices(self):
            
        for name, device_dict in self.devices_and_ips.items():
            
            for device_id, ip in device_dict.items():

                self.offline_devices.append(device_id)
        
                print(f"Proceeding with rsync for device {device_id} at {ip}")

                rsync_command = [
                    "sudo",
                    "sshpass",
                    "-p",
                    f"{self.password}",
                    "rsync",
                    "-a",
                    "-P",
                    "--timeout=5",
                    "-e",
                    "ssh -o StrictHostKeyChecking=no",
                    f"{deobfuscate}sys{device_id}@{ip}:data/123{device_id}_data",
                    f"{self.save_folder}/{deobfuscate.upper()}_Internal_Testing_Logs/{name.replace(' ', '_')}",
                ]

                try:
                    subprocess.run(
                        rsync_command,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        check=True,
                    )
                    self.offline_devices.remove(device_id)
                    
                except subprocess.CalledProcessError as e:
                    print(
                        f'Error when trying to download from device {device_id} at {ip}: {e.returncode}: {e.stderr.decode("utf-8")}'
                    )
                    continue
    
    def find_issues(self): 

        def find_all_logs_with_issues():

            valid_log_paths = [
                log_path
                for log_path in iglob(
                    f"{self.save_folder}/**/123*_{deobfuscate}_logstderr.log_path",
                    recursive=True,
                )
                if os.path.isfile(log_path)
                and all(log_path not in acknowledged_issue.log_path for acknowledged_issue in self.logs_with_acknowledged_issues)
            ]

            for log_path in valid_log_paths:

                with open(log_path) as log:

                    log_lines = log.readlines()
                    
                issues = [
                    f"{log_line.strip()}\n"
                    for log_line in log_lines
                    if log_line
                    and all(
                        normal_line not in log_line
                        for normal_line in self.normal_lines
                    )
                ]

                warnings = [
                    issue
                    for issue in issues
                    if any(
                        warning_line in issues
                        for warning_line in self.warning_lines)
                ]

                errors = [
                    issue 
                    for issue in issues
                    if issue not in warnings
                ]

                if warnings or errors:
                    self.logs_with_issues.append(log_path)

        def find_recent_issues():

            for log in self.logs_with_issues:
                
                device_id = extract_device_id(log)

                log_start_time = extract_log_start_time(log)

                test_time = log_start_time if isinstance(log_start_time, dt) else dt.now()

                time_difference = (dt.now() - test_time).total_seconds()

                if time_difference <= self.recent_timespan * 24 * 3600:

                    self.device_squares[device_id].recent_logs_with_issues.append(
                        ("Errors", log_start_time, log)
                    )

        find_all_logs_with_issues()

        find_recent_issues()
   
    def get_and_confirm_password(self, callback, *args, **kwargs):

        if self.password is None:
            password = askstring(
                "Enter Password",
                "Please enter the password to connect to the devices:",
                show="*",
                parent=self,
            )

            if password is not None:
                if checked := askokcancel(
                    "Please confirm entered password:",
                    f"Confirm Entered Password:\n\n{password}\n\nWarning: If the password is incorrect the application will fail to run",
                    parent=self,
                ):
                    self.password = password
                    self.canvas.itemconfig(self.last_updated, text="Updating...")
                    self.after(
                        100, callback, *args, **kwargs
                    )
                    return

        return self.get_and_confirm_password(callback, *args, **kwargs)

    def update_last_updated_time(self):
        self.canvas.itemconfig(self.last_updated, text=f"Last updated: {dt.now()}")

    async def update_devices_async(self):
        
        rsync_tasks = [
            asyncio.create_task(device_square.device_rsync(self.password, self.save_folder)) for device_square in self.device_squares.values()
        ]
        
        await asyncio.gather(*rsync_tasks)

        process_log_tasks = [
            device_square.device_process_recent_logs_with_issues(self.logs_with_acknowledged_issues, self.normal_lines, self.warning_lines) for device_square in self.device_squares.values()
        ]
        
        await asyncio.gather(*process_log_tasks)

    def update_devices(self, update_type):
        if update_type == 'async':
            asyncio.run(self.update_devices_async())
        else:
            self.monitor_update_device_status()

if __name__ == "__main__":
    # Add devices running old code to this list
    old_devices_and_ips = {
        "001": "10.51.20.10",
        "004": "10.51.21.7",
        "007": "10.23.6.39",
        "008": "10.51.27.131",
        "014": "10.51.17.49",
    }

    # Add devices running new code to this list
    new_devices_and_ips = {
        "002": "10.51.23.129",
        "003": "10.51.17.235",
        "006": "10.51.25.56",
        "009": "10.23.5.69",
        "013": "10.51.16.16",
        "015": "10.51.23.213",
    }

    # Edit this if necessary to ignore devices with old code or new code
    all_devices_and_ips = {
        "Old Devices": old_devices_and_ips,
        "New Devices": new_devices_and_ips,
    }

    # Add warning strings to this list
    warnings = [
        "Corrupt JPEG data",
        "DeprecationWarning",
        "UserWarning",
        "Deprecated in NumPy 1.20",
        "Failed to load image Python extension",
    ]

    # Add normal strings to this list
    normals = [
        "Loading symbol saved by previous version",
        "Symbol successfully upgraded!",
        "Running performance tests",
        "Resource temporarily unavailable",
    ]

    app = InternalTestingMonitor(
        devices_and_ips=all_devices_and_ips,
        normal_lines=normals,
        warning_lines=warnings,
        recent_timespan=(3 + 1),
        update_interval=300,
        save_folder=f'{os.path.expanduser("~")}',
    )
    app.mainloop()

