"""
Has some non-standard dependencies, install with pip
Must have at least ~1 GB of free space in home folder to download all logs
Edit normal and warning strings in the __name__ == "__main__" condition, anything else will be counted as an error
Edit device IDs and IPs in the __name__ == "__main__" condition
When prompted for the password, enter the password that is used to log_path in to the devices
Mouse over device square in the GUI to display the online/offline/warning/error tooltip
If a device is offline and not out on data collection, connect the device to the monitor and wireless keyboard/mouse and attempt to login
"""

global DEOBFUSCATE
DEOBFUSCATE = "flash"

global NUMBER_OF_MONITORS
NUMBER_OF_MONITORS = 2

global RSYNC_TIMEOUT
RSYNC_TIMEOUT = 5

import subprocess
import os
from glob import iglob
import re
from datetime import timedelta, datetime as dt
import tkinter as tk
from tkinter.simpledialog import askstring
from tkinter.messagebox import askokcancel
from tkinter import ttk
import json
import Pmw
from collections import defaultdict, namedtuple
import asyncio, aiofiles
import threading
#import concurrent.futures
from functools import partial
import platform
import logging

logging.basicConfig(
    level=logging.ERROR,  # Set the desired logging level (e.g., ERROR or higher)
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename=f"{DEOBFUSCATE.upper()}_Internal_Testing_Logs/{DEOBFUSCATE.upper()}_internal_testing_errors.log",  # Specify the log file name
)

# Define the AcknowledgedIssue named tuple
AcknowledgedIssue = namedtuple('AcknowledgedIssue', ['device_id', 'log_start_time','issue_type','issue', 'log_path', 'acknowledgement_reason'])

def load_devices_and_ips_from_file():

    devices_and_ips_file = f"{DEOBFUSCATE.upper()}_Internal_Testing_Logs/{DEOBFUSCATE.upper()}_devices_and_ips.json"

    try:

        with open(devices_and_ips_file, "r") as json_file:
            
            devices_and_ips = json.load(json_file)
        
        return devices_and_ips
    
    except (FileNotFoundError, json.JSONDecodeError) as e:

        logging.exception(f"{dt.now()} An exception occurred when trying to load {devices_and_ips_file}: {e}")

        print(f"{dt.now()} An exception occurred when trying to load {devices_and_ips_file}: {e}")

        print(f"\nCreating new file for manual entry. Please open {devices_and_ips_file} and enter all device ID and IP values manually")

        devices_and_ips_placeholder_dict_dict = {
            "Device Category Placeholder 1": {
                "XXX": "1.1.1.1",
                "YYY": "2.2.2.2",
                "..." : "..."
            },
            "Device Category Placeholder 2": {
                "ZZZ": "3.3.3.3",
                "AAAA": "4.4.4.4",
                "..." : "..."
            },
            "Device Category Placeholder ..." : {
                "..." : "..."
            }
        }

        with open(devices_and_ips_file, "w") as json_file:
            json.dump(devices_and_ips_placeholder_dict_dict, json_file, indent=4)

        exit()

def load_acknowledged_issues_from_file():

    acknowledged_issues_file = f"{DEOBFUSCATE.upper()}_Internal_Testing_Logs/{DEOBFUSCATE.upper()}_internal_testing_acknowledged_issues.json"
    
    acknowledged_issues = set()  # Use a set to prevent duplicates

    try:

        with open(acknowledged_issues_file) as f:
            acknowledged_issues_data = json.load(f)
            for item in acknowledged_issues_data:
                log_start_time = dt.fromisoformat(item['log_start_time']) if item['log_start_time'] != "Current" else item['log_start_time']
                acknowledged_issues.add(
                    AcknowledgedIssue(
                        device_id=item['device_id'],
                        log_start_time=log_start_time,
                        issue_type=item['issue_type'],
                        issue=item['issue'],
                        log_path=item['log_path'],
                        acknowledgement_reason=item['acknowledgement_reason']
                    )
                )

        return acknowledged_issues

    except (FileNotFoundError, json.JSONDecodeError) as e:

        logging.exception(f"{dt.now()} An exception occurred when trying to load {acknowledged_issues_file}: {e}")

        return set()

def save_acknowledged_issue_to_file(device_id, log_start_time, issue_type, issue, log_path, acknowledgement_reason):

    acknowledged_issues_file = f"{DEOBFUSCATE.upper()}_Internal_Testing_Logs/{DEOBFUSCATE.upper()}_internal_testing_acknowledged_issues.json"

    new_acknowledged_issue = AcknowledgedIssue(device_id, log_start_time, issue_type, issue, log_path, acknowledgement_reason)

    acknowledged_issues = load_acknowledged_issues_from_file()

    # Check for duplicates with the same fields (except 'acknowledgement_reason')
    duplicate_issue = None
    for existing_issue in acknowledged_issues:
        if (
            existing_issue.device_id == device_id and
            existing_issue.log_start_time == log_start_time and
            existing_issue.issue_type == issue_type and
            existing_issue.issue == issue and
            existing_issue.log_path == log_path
        ):
            duplicate_issue = new_acknowledged_issue
            break

    if duplicate_issue:

        # Update the 'acknowledgement_reason' for the existing entry
        # acknowledged_issues.remove(duplicate_issue)  # Remove the old entry
        # duplicate_issue.acknowledgement_reason = acknowledgement_reason  # Update the acknowledgement_reason
        # acknowledged_issues.add(duplicate_issue)  # Add the updated entry back to the set
        print("Duplicate acknowledged issue not entered")
        return 
    
    else:
        acknowledged_issues.add(new_acknowledged_issue)  # Add the new entry to the set

    acknowledged_issues_data = [
        {
            'device_id': item.device_id,
            'log_start_time': item.log_start_time.isoformat() if isinstance(item.log_start_time, dt) else item.log_start_time,
            'issue_type': item.issue_type,
            'issue': item.issue,
            'log_path': item.log_path,
            'acknowledgement_reason': item.acknowledgement_reason
        }
        for item in acknowledged_issues
    ]

    with open(acknowledged_issues_file, 'w') as f:
        json.dump(acknowledged_issues_data, f)

class AcknowledgementDialog(tk.Toplevel):

    def __init__(self, parent, title, *args, header_text="", body_text="", footer_text="", **kwargs):
        super().__init__(parent, *args, **kwargs)  # Initialize the parent class

        self.parent = parent

        self.title = title

        self.header_text = header_text
        self.body_text = body_text
        self.footer_text = footer_text 

        self.result = None

        self.horizontal_padding = 10
        self.max_width = 0
        self.max_height = 0

        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self.initialize()

    def initialize(self):
        self.withdraw()
        self.setup_window()
        self.deiconify()
        self.text_widget.focus_force()
        self.wait_window()
        return self.result

    def setup_canvas_and_frame(self):

        self.canvas = tk.Canvas(self)
        self.canvas.grid(row=1, column=0, padx=10, pady=10, sticky='nsew')

        self.frame = tk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.frame, anchor='nw')

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.frame.grid_rowconfigure(0, weight=1)
        self.frame.grid_columnconfigure(0, weight=1)

        return self.canvas, self.frame

    def setup_window(self):

        self.create_header()
        self.canvas, self.frame = self.setup_canvas_and_frame()

        self.create_body()
        self.scrollbar = self.create_scrollbar()
        self.create_footer()

        self.update_canvas()

    def create_header(self):

        self.header_label = tk.Label(self, text=self.header_text, font=('Helvetica', 12))
        self.header_label.grid(row=0, column=0)
        self.max_height += self.header_label.winfo_reqheight()

    def create_scrollbar(self):
        self.scrollbar = tk.Scrollbar(self, command=self.canvas.yview)
        self.scrollbar.grid(row=1, column=1, sticky='ns')
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.bind_all("<MouseWheel>", self.canvas.yview_scroll)
        return self.scrollbar

    def create_body(self):

        self.body_label = tk.Label(self.frame, text=self.body_text, justify='center', wraplength=600)
        self.body_label.pack(padx=10, pady=10, fill='both')
        self.max_width += max(self.header_label.winfo_reqwidth(), self.body_label.winfo_reqwidth()) + 4*10
        self.max_height += self.body_label.winfo_reqheight() + 4*10

    def create_footer(self):

        self.text_widget = tk.Text(self, wrap=tk.WORD, height=4, width=30)  # Larger text area
        self.text_widget.grid(row=2, column=0, columnspan=3, padx=10, pady=10)
        self.max_height += 2*self.text_widget.winfo_reqheight() + 2*10

        button_frame = tk.Frame(self)  # Create a frame to hold the buttons
        button_frame.grid(row=3, column=0, pady=10)  # Place the frame under the text entry box

        self.ok_button = tk.Button(button_frame, text="OK", command=self.choose_ok)
        self.ok_button.grid(row=0, column=0, padx=10)  # Place the "OK" button in the frame

        self.cancel_button = tk.Button(button_frame, text="Cancel", command=self.choose_cancel)
        self.cancel_button.grid(row=0, column=1, padx=10)  # Place the "Cancel" button next to the "OK" button

    def update_canvas(self):
        self.canvas.update_idletasks()
        self.canvas.config(scrollregion=self.canvas.bbox("all"))
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - self.winfo_reqwidth()) // (2 * NUMBER_OF_MONITORS)
        y = (screen_height - self.winfo_reqheight()) // (2 * NUMBER_OF_MONITORS)
        self.geometry(f"{self.max_width}x{min(screen_height // 2, self.max_height)}+{x}+{y}")

    def choose_ok(self):
        self.result = self.text_widget.get("1.0", tk.END).strip()
        self.destroy()

    def choose_cancel(self):
        self.result = None
        self.destroy()

class DetailsWindow(tk.Toplevel):
    LABEL_WIDTH = 300
    BUTTON_WIDTH = 15
    CHECKBOX_COLUMN = 3

    def __init__(self, parent, selected_device, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)  # Initialize the parent class
        self.parent = parent
        self.selected_device = selected_device
        self.title(f"{DEOBFUSCATE}sys{self.selected_device.id} Details")
        self.horizontal_padding = 10
        self.max_width = 0
        self.max_height = 0
        self.scrollbar = None
        self.checkbox_vars = {}

        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self.withdraw()
        self.setup_window()
        self.deiconify()

    def setup_canvas_and_frame(self):
        self.canvas = tk.Canvas(self)
        self.canvas.grid(row=1, column=1, padx=10, pady=10, sticky='nsew')

        self.frame = tk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.frame, anchor='nw')

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.frame.grid_rowconfigure(0, weight=1)
        self.frame.grid_columnconfigure(0, weight=1)

        return self.canvas, self.frame

    def setup_window(self):
        self.create_title_label()
        self.canvas, self.frame = self.setup_canvas_and_frame()

        if self.selected_device.issues:
            self.scrollbar = self.setup_scrollbar()
            self.create_header_labels()
            self.create_widgets_with_separators(self.selected_device.issues)
        else:
            self.create_no_issues_label()

        self.update_canvas()

    def create_title_label(self):
        title = f"Issues on {DEOBFUSCATE}sys{self.selected_device.id}"
        device_label = tk.Label(self, text=title, font=('Helvetica', 16))
        device_label.grid(row=0, column=1)
        self.max_width += device_label.winfo_reqwidth()
        self.max_height += 100

    def create_header_labels(self):
        header_labels = ["Log Start Time", "Issue Type", "Issue", "Acknowledge?"]
        for col, header_text in enumerate(header_labels):
            header_label = tk.Label(self.frame, text=header_text, justify='center')
            header_label.grid(row=0, column=col * 2 + 2, sticky='ew', padx=self.horizontal_padding)
        self.max_height += 50

    def setup_scrollbar(self):
        self.scrollbar = tk.Scrollbar(self, command=self.canvas.yview)
        self.scrollbar.grid(row=1, column=2, sticky='ns')
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.bind_all("<MouseWheel>", self.canvas.yview_scroll)
        return self.scrollbar

    def create_widgets_with_separators(self, items):
        for index, item in enumerate(items, start=1):
            self.create_separator(index * 2)
            self.create_widgets_for_row(index * 2 + 1, item)
            self.max_height += 50

        self.create_separator((len(items) + 1) * 2)
        self.create_acknowledge_button()

    def create_separator(self, index):
        separator = ttk.Separator(self.frame, orient='horizontal')
        separator.grid(column=1, row=index, columnspan=9, sticky='ew', pady=5, padx=self.horizontal_padding)
        self.max_height += separator.winfo_reqheight() + 2 * 5

    def create_widgets_for_row(self, index, item):
        labels = [str(item[1]), item[2], item[3]]
        row_width = 0
        
        def open_log_folder(log_path, parent_window):

            parent_folder = os.path.dirname(log_path)

            if "microsoft" in platform.uname().release:
                open_command = "wslview"

            elif "Linux" in platform.system():
                open_command = "xdg-open"
            
            else:
                print("Requires a Linux system to open files (for now)")
                return

            try:
                parent_window.lower()

                subprocess.run([open_command, parent_folder], check=True)
                
            except subprocess.CalledProcessError as e:
                logging.exception(f"{dt.now()} An exception occurred when opening the log {log_path}: {e}")

        open_log_folder_button = self.create_button("Open Log Folder", partial(open_log_folder, item[4], self), index, 0)
        row_width += open_log_folder_button.winfo_reqwidth() + 4 * self.horizontal_padding

        for col, label_text in enumerate(labels):
            if col > 0:
                self.create_vertical_separator(index, (col * 2) + 1)
                row_width += 8

            label = self.create_label(label_text)
            label.grid(row=index, column=col * 2 + 2, sticky='nsew', pady=10, padx=self.horizontal_padding)  # Adjust column for label
            row_width += label.winfo_reqwidth() + 4 * self.horizontal_padding

        checkbox_var = tk.BooleanVar()
        checkbox = tk.Checkbutton(self.frame, variable=checkbox_var)
        checkbox.grid(row=index, column=(self.CHECKBOX_COLUMN * 2) + 2, sticky='ew', padx=self.horizontal_padding)  # Adjust column for checkbox
        self.checkbox_vars[(index-1)//2] = checkbox_var
        self.create_vertical_separator(index, (self.CHECKBOX_COLUMN * 2) + 1)  # Adjust column for separator
        row_width += checkbox.winfo_reqwidth() + 4 * self.horizontal_padding 
        
        row_width += 50

        self.max_width = max(self.max_width, row_width)

    def create_vertical_separator(self, index, column):
        separator = ttk.Separator(self.frame, orient='vertical')
        separator.grid(row=index, column=column, sticky='ns', padx=2, pady=10)

    def create_acknowledge_button(self):
        acknowledge_button = tk.Button(self, text="Acknowledge Selected", command=self.perform_acknowledgement)
        acknowledge_button.grid(row=2, column=1, padx=self.horizontal_padding, pady=10)
        self.max_height += 30

    def create_label(self, text):
        return tk.Label(
            self.frame, text=text, wraplength=self.LABEL_WIDTH, justify='center'
        )

    def create_button(self, text, command, index, column):
        button = tk.Button(self.frame, text=text, command=command, width=self.BUTTON_WIDTH)
        button.grid(row=index, column=column, sticky='w', padx=self.horizontal_padding)
        return button

    def create_no_issues_label(self):
        label_text = "No unacknowledged issues for this device"
        label = tk.Label(self, text=label_text)
        label.grid(row=1, column=1, columnspan=3, sticky='nsew', padx=self.horizontal_padding, pady=10)
        self.max_width += label.winfo_reqwidth()
    
    def update_canvas(self):
        self.canvas.update_idletasks()
        self.canvas.config(scrollregion=self.canvas.bbox("all"))
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - self.winfo_reqwidth()) // (2 * NUMBER_OF_MONITORS)
        y = (screen_height - self.winfo_reqheight()) // (2 * NUMBER_OF_MONITORS)
        self.geometry(f"{self.max_width}x{min(screen_height // 2, self.max_height)}+{x}+{y}")

        if self.scrollbar:
            self.scrollbar.config(command=self.canvas.yview)

    def perform_acknowledgement(self):
        
        issues_being_acknowledged = []

        # Iterate through the selected_device's issues and extract relevant information
        for index, (device_id, log_start_time, issue_type, issue, log_path) in enumerate(self.selected_device.issues, start=1):
            checkbox_var = self.checkbox_vars[index]
            if checkbox_var.get():
                issues_being_acknowledged.append((device_id, log_start_time, issue_type, issue, log_path))

        # Show the acknowledgement prompt window
        self.show_acknowledgement_prompt_window(issues_being_acknowledged)

    def show_acknowledgement_prompt_window(self, issues_being_acknowledged):

        selected_issue_text = ""

        for index, (device_id, log_start_time, issue_type, issue, log_path) in enumerate(issues_being_acknowledged):

            selected_issue_text += f"{issue_type}:{issue} in the {log_start_time} log"

            if index < len(issues_being_acknowledged) - 1:
                selected_issue_text += "\n\n"
            
        prompt_text = f"Please enter the reason for acknowledging the issue(s)\n on the device {DEOBFUSCATE}sys{device_id} below:"

        acknowledgment_reason = AcknowledgementDialog(
            self, "Enter Acknowledgement Reason", header_text=prompt_text, body_text=selected_issue_text).result
        if acknowledgment_reason:
            issues_being_acknowledged = []
            for index, (device_id, log_start_time, issue_type, issue, log_path) in enumerate(self.selected_device.issues, start=1):
                checkbox_var = self.checkbox_vars[index]
                if checkbox_var.get():
                    issues_being_acknowledged.append((device_id, log_start_time, issue_type, issue, log_path))
            self.save_acknowledged_issues_and_close_window(issues_being_acknowledged, acknowledgment_reason)

    def save_acknowledged_issues_and_close_window(self, issues_being_acknowledged, acknowledgment_reason):
        for device_id, log_start_time, issue_type, issue, log_path in issues_being_acknowledged:
            save_acknowledged_issue_to_file(device_id, log_start_time, issue_type, issue, log_path, acknowledgment_reason)
        
        self.parent.start_update_cycle()
        self.parent.deiconify()
        self.destroy()

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
        self.recent_logs_with_issues = []
        self.issues = set()
        self.acknowledged_issues = set()
        self.square = self.canvas.create_rectangle(
            x - radius, y - radius, x + radius, y + radius, fill=self.color
        )
        self.canvas.tag_bind(self.square, "<Button-1>", self.device_handle_square_click)

    def device_handle_square_click(self, event):
        if self.parent.updating == False:
            self.parent.update_gui_after_device_selection(self)

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        self._status = value
        self.device_update_appearance()

    async def device_rsync(self, password, save_folder):
        
        try:

            if not os.path.isdir(f'{save_folder}/{DEOBFUSCATE.upper()}_Internal_Testing_Logs/{self.device_set.replace(" ", "_")}/'):
                os.makedirs(f'{save_folder}/{DEOBFUSCATE.upper()}_Internal_Testing_Logs/{self.device_set.replace(" ", "_")}/')
            
            self.status = 'Offline'

            f'Attempting to download from device {self.id} at {self.ip}'

            rsync_command = [
                "sudo",
                "sshpass",
                "-p",
                f"{password}",
                "rsync",
                "-a",
                "-P",
                f"--timeout={RSYNC_TIMEOUT}",
                "-e",
                "ssh -o StrictHostKeyChecking=no",
                f"{DEOBFUSCATE}sys{self.id}@{self.ip}:data/123{self.id}_data",
                f"{save_folder}/{DEOBFUSCATE.upper()}_Internal_Testing_Logs/{self.device_set.replace(' ', '_')}",
            ]
            process = await asyncio.create_subprocess_exec(
                            *rsync_command,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE
                        )
            _, stderr = await process.communicate()

            if process.returncode != 0:
                logging.exception(f"{dt.now()} An error occurred when trying to rsync from device {self.id} at {self.ip}: {process.returncode}: {stderr.decode('utf-8')}")
                print(
                    f"{dt.now()} An error occurred when trying to rsync from device {self.id} at {self.ip}: {process.returncode}: {stderr.decode('utf-8')}"
                )

            else:
                self.status = 'Online'

        except Exception as e:
            logging.exception(f"{dt.now()} An exception occurred when trying to rsync from device {self.id} at {self.ip}: {e}")

    async def device_find_and_process_issues(self, acknowledged_issues, normal_lines, warning_lines):

        self.issues = set()
        self.acknowledged_issues = set()

        def extract_log_start_time(log_path):
            log_start_time_match = re.search(r"\d{2}_\w{3}_\d{4}_\d{2}-\d{2}-\d{2}_\w{3}", log_path)
            return (
                dt.strptime(log_start_time_match[0], "%d_%b_%Y_%H-%M-%S_%Z")
                if log_start_time_match
                else "Current"
            )

        def extract_device_id(log_path):
            device_id_match = re.search(r"(?<=123)(\d{3})(?=_data)", log_path)
            return device_id_match[0] if device_id_match else None

        def check_log_start_time_difference(log_path):
            log_start_time = extract_log_start_time(log_path)
            test_time = log_start_time if isinstance(log_start_time, dt) else dt.now()
            time_difference = (dt.now() - test_time).total_seconds()
            return time_difference

        valid_log_paths = [
            log_path
            for log_path in self.parent.logs_with_issues
            if extract_device_id(log_path) == self.id
            and check_log_start_time_difference(log_path) <= self.parent.recent_timespan * 24 * 3600
        ]

        for log_path in valid_log_paths:
            async with aiofiles.open(log_path) as log:
                log_lines = await log.readlines()

                issues = [
                    log_line.strip()
                    for log_line in log_lines
                    if log_line.strip() and all(normal_line not in log_line for normal_line in normal_lines)
                ]

            log_start_time = extract_log_start_time(log_path)

            for issue in issues:

                issue_type = 'Warning' if any(warning_line in issue for warning_line in warning_lines) else 'Error'

                if acknowledged_issues:

                    is_acknowledged = False
                    for ai in acknowledged_issues:
                        if ai.device_id == self.id and ai.log_start_time == log_start_time and ai.issue == issue and ai.log_path == log_path:
                            is_acknowledged = True
                            break

                    if is_acknowledged:
                        
                        self.acknowledged_issues.add((self.id, log_start_time, issue_type, issue, log_path))

                    else:
                        self.issues.add((self.id, log_start_time, issue_type, issue, log_path))

        def sort_key(item):
            _, log_start_time, error_type, issue, _ = item

            if log_start_time == "Current":
                log_start_time = dt.now()

            return (-log_start_time.timestamp(), error_type, issue)

        if self.issues:

            self.issues = sorted(self.issues, key=sort_key)

            issue_types = [item[2].lower() for item in self.issues]
            if "warning" in issue_types:
                self.status = f'{self.status} Has Warnings'
            if "error" in issue_types:
                self.status = f'{self.status} and Has Errors'

        if self.acknowledged_issues:
            self.status = f'{self.status} and Has Acknowledged Issues'

    def device_update_appearance(self):

        status_color_map = {
            'Offline' : 'gray',
            'Online' : 'green',
            'Has Warnings' : 'yellow',
            'Has Errors' : 'red'
        }

        for key_status in status_color_map:
            if key_status in self.status:
                self.color = status_color_map[key_status]

        self.canvas.itemconfig(self.square, fill=self.color)
        self.tooltip.tagbind(self.canvas, self.square, self.status)

class InternalTestingMonitor(tk.Tk):

    INITIAL_Y = 75
    SQUARE_SPACING = 60
    SQUARE_RADIUS = 20

    def __init__(
        self,
        *args,
        devices_and_ips: dict = load_devices_and_ips_from_file(),
        normal_lines: list,
        warning_lines: list,
        recent_timespan: int = (3 + 1),  # In days, default interval of 3 days plus 1 extra in case checked next day
        save_folder = f'{os.path.expanduser("~")}',  # The default save folder is the home folder
        **kwargs,
    ):
        super().__init__()

        self.protocol("WM_DELETE_WINDOW", self.wait_for_loop_before_closing)

        self.devices_and_ips = devices_and_ips
        self.normal_lines = normal_lines
        self.warning_lines = warning_lines
        self.recent_timespan = recent_timespan
        self.save_folder = save_folder

        self.updating = False
        self.loop = None
        self.want_rsync = True

        self.selected_device = None

        self.offline_devices = []
        self.logs_with_issues = []
        self.acknowledged_issues = None

        self.tooltip = Pmw.Balloon(self) # type: ignore
        self.device_squares = {}  # Initialize the device_squares dictionary

        self.setup_window()

        self.password = None

        self.after(1, self.get_and_confirm_password, self.start_update_cycle)

    def setup_window(self):

        self.title(f"{DEOBFUSCATE.upper()} Internal Testing Monitor")
          
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        # Create the canvas
        self.canvas = tk.Canvas(self, bg='white')
        self.canvas.grid(row=0, column=0, sticky='nsew')

        self.create_device_sets()

        self.create_sidebar()

        # Create last_updated element
        self.last_updated = self.canvas.create_text(
            self.canvas.winfo_width() // 2, self.canvas.winfo_height() - 10, text="Waiting for password entry..."
        )

        self.update_canvas_size()

        self.update_idletasks()

        # Get the screen width and height
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # Calculate the x and y coordinates to center the window
        x = (screen_width - self.winfo_reqwidth()) // (2* NUMBER_OF_MONITORS)
        y = (screen_height - self.winfo_reqheight()) // (2*NUMBER_OF_MONITORS)

        # Set the window's geometry
        self.geometry(f"+{x}+{y}")
        
        self.update_idletasks()

    def create_device_sets(self):

        y = InternalTestingMonitor.INITIAL_Y

        self.total_canvas_width = 0
        for device_set_name, device_dict in self.devices_and_ips.items():
            num_devices = len(device_dict)
            x_start = InternalTestingMonitor.SQUARE_SPACING
            total_canvas_width = (num_devices) * (x_start) * 2

            for index, (device_id, device_ip) in enumerate(device_dict.items()):
                x = x_start + index * InternalTestingMonitor.SQUARE_SPACING

                device_square = DeviceSquare(
                    parent=self,
                    device_set=device_set_name,
                    id=device_id,
                    ip=device_ip,
                    status='Offline',
                    canvas=self.canvas,
                    x=x,
                    y=y,
                    radius=InternalTestingMonitor.SQUARE_RADIUS,
                    tooltip=self.tooltip,
                )

                # Create a label for the device
                label = tk.Label(self.canvas, text=device_id, background='white')

                # Calculate the position of the label
                label_x = x
                label_y = y + 40  # Adjust the y-coordinate as needed

                # Place the label on the canvas using create_window
                self.canvas.create_window(label_x, label_y, window=label)

                self.device_squares[device_id] = device_square

            self.update()
            self.canvas.create_text(self.canvas.winfo_width() / 2, y - 40, text=device_set_name)
            y += 110
            self.total_canvas_width = max(total_canvas_width, self.total_canvas_width)

    def create_sidebar(self):

        self.sidebar = tk.Frame(self, bg="lightgray")
        self.sidebar.grid(row=0, column=1, sticky='nsew')

        self.sidebar_canvas = tk.Canvas(self.sidebar, bg="lightgray")
        self.sidebar_canvas.pack(fill="both", expand=True)
        
        self.click_a_device_label_var = tk.StringVar(value="Please click a device")
        self.device_id_label_var = tk.StringVar(value="Device ID:")
        self.device_ip_label_var = tk.StringVar(value="Device IP:")
        self.warning_label_var = tk.StringVar(value="Warnings:")
        self.error_label_var = tk.StringVar(value="Errors:")
        self.acknowledged_label_var = tk.StringVar(value="Acknowledged:")

        label_vars = [
            self.click_a_device_label_var,
            self.device_id_label_var,
            self.device_ip_label_var,
            self.warning_label_var,
            self.error_label_var,
            self.acknowledged_label_var
        ]

        for label_var in label_vars:
            label = tk.Label(self.sidebar_canvas, textvariable=label_var, anchor='center', background='lightgray')
            label.pack(fill='x', padx=10, pady=(10, 0))  # Add vertical padding to the top

        self.update_button = tk.Button(
            self.sidebar_canvas,
            text="Update",
            command=self.start_update_cycle,
            state='disabled',
            anchor='center',
            background='lightgray'
        )

        self.update_button.pack(padx=10, pady=(10, 0))  # Add vertical padding to the top

        def create_details_window():

            if hasattr(self, 'details_display') and self.details_display:
                self.details_display.destroy()

            self.details_display = DetailsWindow(self, self.selected_device)

        self.details_window_button = tk.Button(
        self.sidebar_canvas,
        text="Open Details",
        command=create_details_window,
        state='disabled',
        anchor='center',
        background='lightgray'
        )

        self.details_window_button.pack(padx=10, pady=(10, 0))  # Add vertical padding to the top

        # Center the canvas vertically within the sidebar
        self.sidebar.update_idletasks()
        sidebar_height = self.sidebar.winfo_height()
        canvas_height = self.sidebar_canvas.winfo_reqheight()
        y_position = (sidebar_height - canvas_height) // 2
        self.sidebar_canvas.place(relx=0.5, rely=y_position / sidebar_height, anchor="n")

    def update_canvas_size(self):

        self.update()
        bbox = self.canvas.bbox("all")
        canvas_width = self.total_canvas_width
        canvas_height = max(bbox[3], bbox[1]) + InternalTestingMonitor.INITIAL_Y//2
        self.geometry(f"{canvas_width}x{canvas_height}")
        self.update()

    def get_and_confirm_password(self, callback, *args, **kwargs):

        if self.password is None:
            if password := askstring(
                "Enter Password",
                "Please enter the password to connect to the devices:",
                show="*",
                parent=self):
                if checked := askokcancel(
                    "Please confirm entered password:",
                    f"Confirm Entered Password:\n\n{password}\n\nWarning: If the password is incorrect the application will fail to run",
                    parent=self):
                    self.password = password
                    self.canvas.itemconfig(self.last_updated, text="Updating...")
                    self.after(
                        1, callback, *args, **kwargs
                    )
                    return

        return self.get_and_confirm_password(callback, *args, **kwargs)

    def update_gui_after_device_selection(self, device_square):

        self.selected_device = device_square  # Update selected_device

        device_id = self.selected_device.id
        device_ip = self.selected_device.ip
        warning_count = sum('Warning' in item[2] for item in self.selected_device.issues)
        error_count = sum('Error' in item[2] for item in self.selected_device.issues)
        acknowledged_count = len(self.selected_device.acknowledged_issues)

        self.click_a_device_label_var.set("")
        self.device_id_label_var.set(f"Device ID: {device_id}")
        self.device_ip_label_var.set(f"Device IP: {device_ip}")
        self.warning_label_var.set(f"Warnings: {warning_count}")
        self.error_label_var.set(f"Errors: {error_count}")
        self.acknowledged_label_var.set(f"Acknowledged: {acknowledged_count}")

        # Enable the button when selected_device is not None
        if self.selected_device is not None:
            self.details_window_button.config(state='normal')
        else:
            self.details_window_button.config(state='disabled')

    async def find_all_logs_with_issues(self):

        self.logs_with_issues = []
        
        valid_log_paths = list(
            iglob(
                f"{self.save_folder}/**/123*_{DEOBFUSCATE}_logstderr.log",
                recursive=True,
            )
        )

        for log_path in valid_log_paths:

            async with aiofiles.open(log_path) as log:

                log_lines = await log.readlines()

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

    async def rsync_devices(self):
        rsync_tasks = []

        for device_square in self.device_squares.values():
            rsync_task = device_square.device_rsync(self.password, self.save_folder)
            rsync_tasks.append(rsync_task)

        await asyncio.gather(*rsync_tasks)
        print("All devices have been rsynced")

    async def find_and_process_device_issues(self):

        self.acknowledged_issues = load_acknowledged_issues_from_file()

        await self.find_all_logs_with_issues()

        tasks = []
        for device_square in self.device_squares.values():
            task = device_square.device_find_and_process_issues(
                self.acknowledged_issues, self.normal_lines, self.warning_lines
            )
            tasks.append(task)

        await asyncio.gather(*tasks)
        print("All issues have been found")

    def update_device_issues(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        try:

            self.canvas.itemconfig(self.last_updated, text="Last updated: Updating...")

            if self.want_rsync:

                self.loop.run_until_complete(self.rsync_devices())
            
            self.loop.run_until_complete(self.find_and_process_device_issues())
    
        except Exception as e:
            logging.exception("An exception occurred: %s", str(e))  # Log the exception with traceback

        finally:
            self.loop.close()

        self.want_rsync = True

        self.updating = False
                    
        self.update_button.config(state='normal')

        self.canvas.itemconfig(self.last_updated, text=f"Last updated: {dt.now()}")

    def threaded_update_device_issues(self):
        thread = threading.Thread(target=self.update_device_issues)
        thread.start()

    def start_update_cycle(self):

        if self.updating == False:

            self.create_sidebar()
            
            self.threaded_update_device_issues()

            self.updating = True

    def wait_for_loop_before_closing(self):

        if not self.loop:

            self.destroy()
            self.quit()
            exit()

        elif self.loop.is_closed():
            self.destroy()

        else:
            messagebox = tk.Toplevel(self)
            messagebox.title("Waiting to close...")
            messagebox.transient(self)
            label = tk.Label(messagebox, text="Waiting to finish updating before closing...")
            label.pack(padx=20, pady=20)

            def check_loop_completion():
                if self.loop.is_running():
                    self.after(100, check_loop_completion)  # Check again after 100 milliseconds
                else:
                    messagebox.destroy()  # Close the waiting messagebox
                    self.destroy()
                    self.quit()
                    exit()

            check_loop_completion() 

if __name__ == "__main__":

    # Add warning strings to this list
    warnings = [
        "Corrupt JPEG data",
        "DeprecationWarning",
        "UserWarning",
        "Deprecated in NumPy 1.20",
        "Failed to load image Python extension",
        "Overload resolution failed:",
        "M is not a numpy array, neither a scalar",
        "Expected Ptr<cv::UMat> for argument",
        "Traceback",
        "warpAffine",
        "nimg = face_align.norm_crop(face_img_bgr, pts5)",
        "facen = model.get_input(face, facelmarks.astype(np.int).reshape(1,5,2), face=True)",
        "face = io.imread(os.path.join(path, fname))",
        "detFacesLog, bboxFaces, idxFaces = pipe_frames_data_to_faces",
        "test_vid_frames_batch_v7_2fps_frminp_newfv_rotate.py",
        "insightface/deploy/face_model.py",
        "insightface/utils/face_align.py",
    ]

    # Add normal strings to this list
    normals = [
        "Loading symbol saved by previous version",
        "Symbol successfully upgraded!",
        "Running performance tests",
        "Resource temporarily unavailable",
    ]

    app = InternalTestingMonitor(
        devices_and_ips=load_devices_and_ips_from_file(),
        normal_lines=normals,
        warning_lines=warnings,
        recent_timespan=(3 + 1),
        save_folder=f'{os.path.expanduser("~")}',
    )
    app.mainloop()

