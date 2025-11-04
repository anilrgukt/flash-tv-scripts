"""Smart plug data verification step implementation using new framework patterns."""

from __future__ import annotations

import os
import time
import shutil
import subprocess
from glob import glob
from datetime import datetime

from PyQt6.QtWidgets import QWidget, QMessageBox, QLineEdit, QVBoxLayout
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QKeyEvent

import pyqtgraph as pg
import numpy as np

from core import WizardStep


class TimeAxisItem(pg.AxisItem):
    """Custom axis item that formats time values as MM:SS."""

    def tickStrings(self, values, scale, spacing):
        """Override to format tick labels as MM:SS or HH:MM:SS."""
        strings = []
        for value in values:
            total_seconds = int(value)
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60

            if hours > 0:
                # Show HH:MM:SS if duration is over 1 hour
                strings.append(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
            else:
                # Show MM:SS for durations under 1 hour
                strings.append(f"{minutes:02d}:{seconds:02d}")

        return strings
from core.exceptions import handle_step_error, FlashTVError, ErrorType
from models import StepStatus
from utils.ui_factory import ButtonStyle


class SmartPlugVerifyStep(WizardStep):
    """Step 5: Verify Smart Plug Data using new framework patterns."""

    def create_content_widget(self) -> QWidget:
        """Create the smart plug verification UI using UI factory."""
        content = QWidget()

        # Use UI factory for main layout
        main_layout = self.ui_factory.create_main_step_layout()
        content.setLayout(main_layout)

        # Create status section
        status_section = self._create_status_section()
        main_layout.addWidget(status_section)

        # Create interactive plot section
        plot_section = self._create_plot_section()
        main_layout.addWidget(plot_section, 1)

        # Create output section (verification log and CSV data)
        output_section = self._create_output_section()
        main_layout.addWidget(output_section, 1)

        # Create continue button
        continue_section = self._create_continue_section()
        main_layout.addLayout(continue_section)

        # Initialize state
        self.browser_launched = False
        self.last_checked = None
        self.last_connected = None

        # Setup timer for status updates
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._safe_update_status)

        return content

    def _create_top_section(self):
        """Create the top section with automation and status."""
        top_row = self.ui_factory.create_horizontal_layout(spacing=12)

        # Create automation and status sections
        automation_section = self._create_automation_section()
        status_section = self._create_status_section()

        top_row.addWidget(automation_section, 3)  # 60% width
        top_row.addWidget(status_section, 2)  # 40% width

        return top_row

    def _create_automation_section(self) -> QWidget:
        """Create the browser automation section using UI factory."""
        automation_box, automation_layout = self.ui_factory.create_group_box("Browser Automation Setup")

        automation_text = self.ui_factory.create_label(
            """This will open Firefox and automatically:\n
            • Navigate to Home Assistant\n
            • Go to History page\n
            • You will then manually select the power data from the dropdown if not already selected\n
            • You will then test by turning the TV on/off\n
            • You will then click the 'Capture Screenshot' button to capture a screenshot that best represents the on and off power states"""
        )
        automation_layout.addWidget(automation_text)
        automation_layout.addStretch()

        return automation_box

    def _create_status_section(self) -> QWidget:
        """Create the status indicators section using UI factory."""
        status_group, status_layout = self.ui_factory.create_group_box("Connection Status")

        self.ha_connection_status = self.ui_factory.create_status_label("🌐 Home Assistant connection: Checking...", status_type="info")

        status_layout.addWidget(self.ha_connection_status)
        status_layout.addStretch()

        return status_group

    def _create_middle_section(self):
        """Create the middle section with controls and instructions."""
        middle_row = self.ui_factory.create_horizontal_layout(spacing=12)

        # Create control and instruction sections
        control_section = self._create_control_section()
        instruction_section = self._create_instruction_section()

        middle_row.addWidget(control_section, 2)  # 40% width
        middle_row.addWidget(instruction_section, 3)  # 60% width

        return middle_row

    def _create_control_section(self) -> QWidget:
        """Create the verification controls section using UI factory."""
        control_group, control_layout = self.ui_factory.create_group_box("Verification Controls")

        # Room name input
        room_label = self.ui_factory.create_label("Room Name:")
        control_layout.addWidget(room_label)

        self.room_name_input = QLineEdit()
        self.room_name_input.setPlaceholderText("e.g., Living Room, Bedroom, etc.")
        control_layout.addWidget(self.room_name_input)

        control_layout.addSpacing(10)

        # Launch browser button
        self.launch_browser_button = self.ui_factory.create_action_button(
            "🚀 Launch Browser Automation",
            callback=self._launch_browser_automation,
            style=ButtonStyle.PRIMARY,
            height=40,
        )
        control_layout.addWidget(self.launch_browser_button)

        # Power cycle confirmation button
        self.power_cycle_button = self.ui_factory.create_action_button(
            "📸 Capture Screenshot",
            callback=self._capture_power_baseline,
            style=ButtonStyle.SECONDARY,
            height=40,
            enabled=False,
        )
        control_layout.addWidget(self.power_cycle_button)

        # Data verified button
        self.data_verified_button = self.ui_factory.create_action_button(
            "✓ Data Verified - Power Changes Detected",
            callback=self._data_verified,
            style=ButtonStyle.SUCCESS,
            height=40,
            enabled=False,
        )
        control_layout.addWidget(self.data_verified_button)

        control_layout.addStretch()

        return control_group

    def _create_instruction_section(self) -> QWidget:
        """Create the testing instructions section using UI factory."""
        instruction_group, instruction_layout = self.ui_factory.create_group_box("Testing Instructions")

        instruction_label = self.ui_factory.create_label(
            "After browser opens:\n\n"
            "1. Enter the room name in the textbox\n"
            "2. Turn TV OFF and wait a few minutes\n"
            "3. Turn TV ON and wait a few minutes\n"
            "4. Click 'Capture Screenshot' to capture screenshot\n"
            "5. Click 'Data Verified' if everything works correctly"
        )
        instruction_layout.addWidget(instruction_label)
        instruction_layout.addStretch()

        return instruction_group

    def _create_plot_section(self) -> QWidget:
        """Create the interactive power plot section using pyqtgraph."""
        plot_group, plot_layout = self.ui_factory.create_group_box("Interactive TV Power Plot - Click to Mark ON/OFF Periods")

        # Initialize marker state - store InfiniteLine objects, not positions
        self.marker_lines = []  # All marker line objects
        self.marker_pairs = {
            'on': {'onset': None, 'offset': None},    # InfiniteLine objects for ON period
            'off': {'onset': None, 'offset': None}    # InfiniteLine objects for OFF period
        }
        self.selected_marker_type = None  # Which marker pair is selected ('on' or 'off')
        self.current_marker_type = 'on'  # Toggle between 'on' and 'off' when placing
        self.region_items = []  # Store LinearRegionItem objects for shaded regions

        # Data boundaries for axis restrictions
        self.data_start_time = None
        self.data_end_time = None
        self.data_min_y = 0
        self.data_max_y = 100

        # Create pyqtgraph plot widget with custom time axis
        time_axis = TimeAxisItem(orientation='bottom')
        self.plot_widget = pg.PlotWidget(axisItems={'bottom': time_axis})
        self.plot_widget.setBackground('w')
        self.plot_widget.setLabel('left', 'Power (W)')
        self.plot_widget.setLabel('bottom', 'Time')
        self.plot_widget.setTitle('Click to place markers: Green=ON period, Red=OFF period | Press Delete to remove selected marker set')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setMinimumHeight(300)

        # Set to panning mode instead of rectangle selection
        self.plot_widget.plotItem.getViewBox().setMouseMode(pg.ViewBox.PanMode)

        # Enable keyboard events for Delete key
        self.plot_widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.plot_widget.keyPressEvent = self._on_key_press

        # Store plot data curve
        self.power_curve = None

        # Connect mouse click events for adding markers
        self.plot_widget.scene().sigMouseClicked.connect(self._on_plot_click)

        # Connect range change signal for axis restrictions
        self.vb = self.plot_widget.plotItem.getViewBox()
        self.vb.sigRangeChanged.connect(self._enforce_range_limits)

        # Add plot to layout
        plot_layout.addWidget(self.plot_widget)

        # Add marker type toggle button
        button_layout = self.ui_factory.create_horizontal_layout()
        self.marker_type_button = self.ui_factory.create_action_button(
            "Current: ON Period (Green) - Click to Toggle",
            callback=self._toggle_marker_type,
            style=ButtonStyle.SUCCESS,
            height=35,
        )
        button_layout.addWidget(self.marker_type_button)

        self.clear_markers_button = self.ui_factory.create_action_button(
            "Clear All Markers",
            callback=self._clear_all_markers,
            style=ButtonStyle.DANGER,
            height=35,
        )
        button_layout.addWidget(self.clear_markers_button)

        # Data verified button
        self.data_verified_button = self.ui_factory.create_action_button(
            "✓ Data Verified - Power Changes Detected",
            callback=self._data_verified,
            style=ButtonStyle.SUCCESS,
            height=40,
            enabled=False,
        )
        button_layout.addWidget(self.data_verified_button)

        plot_layout.addLayout(button_layout)

        return plot_group

    def _create_output_section(self) -> QWidget:
        """Create the CSV data output section using UI factory."""
        # CSV file content
        csv_group, csv_layout = self.ui_factory.create_group_box("TV Power Data (CSV)")
        self.csv_output = self.ui_factory.create_text_area(placeholder="Waiting for TV power data file...", read_only=True)
        csv_layout.addWidget(self.csv_output)

        return csv_group

    def _create_continue_section(self):
        """Create the continue button section using UI factory."""
        button_layout, self.continue_button = self.ui_factory.create_continue_button(
            callback=self._on_continue_clicked, text="Smart Plug Verified - Continue"
        )

        return button_layout

    def _on_key_press(self, event: QKeyEvent) -> None:
        """Handle keyboard events for deleting selected marker set."""
        if event.key() == Qt.Key.Key_Delete:
            if self.selected_marker_type:
                self._delete_marker_set(self.selected_marker_type)
                self.logger.info(f"Deleted {self.selected_marker_type.upper()} marker set")
            else:
                self.logger.info("No marker set selected - click a marker to select it first")
        else:
            # Call parent implementation for other keys
            pg.PlotWidget.keyPressEvent(self.plot_widget, event)

    def _toggle_marker_type(self, checked: bool = False) -> None:
        """Toggle between ON and OFF marker types."""
        self.current_marker_type = 'off' if self.current_marker_type == 'on' else 'on'
        if self.current_marker_type == 'on':
            self.marker_type_button.setText("Current: ON Period (Green) - Click to Toggle")
            self.marker_type_button.setStyleSheet("background-color: #4CAF50;")
        else:
            self.marker_type_button.setText("Current: OFF Period (Red) - Click to Toggle")
            self.marker_type_button.setStyleSheet("background-color: #f44336;")

    def _clear_all_markers(self, checked: bool = False) -> None:
        """Clear all markers from the plot."""
        # Remove all marker lines from plot
        for line in self.marker_lines:
            self.plot_widget.plotItem.removeItem(line)
        self.marker_lines.clear()

        # Clear marker pairs data
        self.marker_pairs = {
            'on': {'onset': None, 'offset': None},
            'off': {'onset': None, 'offset': None}
        }
        self.selected_marker_type = None

        self._redraw_plot()
        self.logger.info("Cleared all markers")

    def _delete_marker_set(self, marker_type: str) -> None:
        """Delete a specific marker set (ON or OFF)."""
        # Remove onset marker if it exists
        if self.marker_pairs[marker_type]['onset']:
            self.plot_widget.plotItem.removeItem(self.marker_pairs[marker_type]['onset'])
            self.marker_lines.remove(self.marker_pairs[marker_type]['onset'])
            self.marker_pairs[marker_type]['onset'] = None

        # Remove offset marker if it exists
        if self.marker_pairs[marker_type]['offset']:
            self.plot_widget.plotItem.removeItem(self.marker_pairs[marker_type]['offset'])
            self.marker_lines.remove(self.marker_pairs[marker_type]['offset'])
            self.marker_pairs[marker_type]['offset'] = None

        # Clear selection
        self.selected_marker_type = None

        # Redraw to update regions
        self._redraw_plot()

    def _on_plot_click(self, event):
        """Handle mouse click on plot to place markers."""
        if not hasattr(self, 'power_times') or len(self.power_times) == 0:
            return

        # Get click position in data coordinates
        mouse_point = self.plot_widget.plotItem.vb.mapSceneToView(event.scenePos())
        x_pos = mouse_point.x()

        # Snap to nearest data point
        x_pos = self._snap_to_nearest_data_point(x_pos)

        # Place marker of current type
        marker_type = self.current_marker_type
        pairs = self.marker_pairs[marker_type]

        # Determine which marker to place (onset or offset)
        if pairs['onset'] is None:
            # Place onset marker (first marker)
            pairs['onset'] = self._create_marker_line(x_pos, marker_type, 'onset', is_incomplete=True)
            self.logger.info(f"Placed {marker_type.upper()} onset marker (1/2)")
        elif pairs['offset'] is None:
            # Place offset marker (second marker)
            pairs['offset'] = self._create_marker_line(x_pos, marker_type, 'offset', is_incomplete=False)
            self.logger.info(f"Placed {marker_type.upper()} offset marker (2/2)")

            # Now we have a complete pair - update the onset marker color
            self._update_marker_completion_status()

            # Check if both marker sets are complete
            if self._are_all_markers_complete():
                self.data_verified_button.setEnabled(True)
                self.logger.info("✅ Both ON and OFF periods marked - ready to verify")
        else:
            self.logger.warning(f"{marker_type.upper()} period already has 2 markers. Toggle type or delete existing markers.")
            return

        # Redraw to update shaded regions
        self._redraw_plot()

    def _snap_to_nearest_data_point(self, x_pos: float) -> float:
        """Snap position to nearest data point based on time."""
        if not hasattr(self, 'power_times') or len(self.power_times) == 0:
            return x_pos

        # Find nearest timestamp
        distances = np.abs(self.power_times - x_pos)
        nearest_idx = np.argmin(distances)
        return float(self.power_times[nearest_idx])

    def _create_marker_line(self, x_pos: float, marker_type: str, marker_position: str, is_incomplete: bool) -> pg.InfiniteLine:
        """Create a draggable marker line with proper styling and behavior."""
        # Determine color based on marker type and completion status
        if is_incomplete:
            # Gray for incomplete marker
            color = (128, 128, 128)
        else:
            # Green for ON, Red for OFF
            color = (76, 175, 80) if marker_type == 'on' else (244, 67, 54)

        # Determine line width (thicker if selected)
        is_selected = (self.selected_marker_type == marker_type)
        line_width = 5 if is_selected else 3

        # Create the InfiniteLine with movable=True for dragging
        # Set bounds based on time range, not indices
        time_bounds = None
        if hasattr(self, 'power_times') and len(self.power_times) > 0:
            time_bounds = [self.power_times[0], self.power_times[-1]]

        line = pg.InfiniteLine(
            pos=x_pos,
            angle=90,  # Vertical line
            pen=pg.mkPen(color, width=line_width, style=Qt.PenStyle.DashLine),
            movable=True,
            bounds=time_bounds,
        )

        # Store metadata on the line object
        line.marker_type = marker_type
        line.marker_position = marker_position  # 'onset' or 'offset'

        # Connect signals for interaction
        line.sigPositionChangeFinished.connect(lambda: self._on_marker_drag_finished(line))
        line.sigPositionChanged.connect(lambda: self._on_marker_dragged(line))
        line.sigClicked.connect(lambda: self._on_marker_clicked(line))

        # Add to plot and tracking list
        self.plot_widget.plotItem.addItem(line)
        self.marker_lines.append(line)

        return line

    def _update_marker_completion_status(self):
        """Update marker colors when a pair becomes complete."""
        for marker_type in ['on', 'off']:
            pairs = self.marker_pairs[marker_type]
            if pairs['onset'] and pairs['offset']:
                # Both markers exist - update to full color
                color = (76, 175, 80) if marker_type == 'on' else (244, 67, 54)
                is_selected = (self.selected_marker_type == marker_type)
                line_width = 5 if is_selected else 3

                pairs['onset'].setPen(pg.mkPen(color, width=line_width, style=Qt.PenStyle.DashLine))
                pairs['offset'].setPen(pg.mkPen(color, width=line_width, style=Qt.PenStyle.DashLine))

    def _are_all_markers_complete(self) -> bool:
        """Check if all marker pairs are complete."""
        return (self.marker_pairs['on']['onset'] is not None and
                self.marker_pairs['on']['offset'] is not None and
                self.marker_pairs['off']['onset'] is not None and
                self.marker_pairs['off']['offset'] is not None)

    def _on_marker_clicked(self, line: pg.InfiniteLine) -> None:
        """Handle marker click to select the marker set."""
        self.selected_marker_type = line.marker_type
        self.logger.info(f"Selected {line.marker_type.upper()} marker set - Press Delete to remove")
        self._update_marker_selection_visual()

    def _on_marker_dragged(self, line: pg.InfiniteLine) -> None:
        """Handle marker drag in progress (real-time feedback)."""
        # Just redraw to update shaded regions
        self._redraw_plot()

    def _on_marker_drag_finished(self, line: pg.InfiniteLine) -> None:
        """Handle marker drag completion with snapping."""
        new_pos = line.value()  # Get current position
        snapped_pos = self._snap_to_nearest_data_point(new_pos)

        if abs(new_pos - snapped_pos) > 0.1:
            line.setValue(snapped_pos)

        self.logger.info(f"Moved {line.marker_type.upper()} {line.marker_position} marker to {snapped_pos:.2f} seconds")
        self._redraw_plot()

    def _update_marker_selection_visual(self):
        """Update visual appearance of markers based on selection."""
        for marker_type in ['on', 'off']:
            pairs = self.marker_pairs[marker_type]
            is_selected = (self.selected_marker_type == marker_type)
            is_complete = (pairs['onset'] is not None and pairs['offset'] is not None)

            # Determine color
            if not is_complete:
                color = (128, 128, 128)  # Gray for incomplete
            else:
                color = (76, 175, 80) if marker_type == 'on' else (244, 67, 54)

            # Determine line width
            line_width = 5 if is_selected else 3

            # Update onset marker
            if pairs['onset']:
                pairs['onset'].setPen(pg.mkPen(color, width=line_width, style=Qt.PenStyle.DashLine))

            # Update offset marker
            if pairs['offset']:
                pairs['offset'].setPen(pg.mkPen(color, width=line_width, style=Qt.PenStyle.DashLine))

    def _enforce_range_limits(self) -> None:
        """Enforce strict pan/zoom boundaries."""
        if self.data_start_time is None or self.data_end_time is None:
            return

        current_range = self.vb.viewRange()
        x_range = current_range[0]  # [xmin, xmax]
        y_range = current_range[1]  # [ymin, ymax]

        # X-axis boundaries
        max_start = self.data_start_time
        max_end = self.data_end_time

        # Correct out-of-bounds X ranges
        x_min = max(x_range[0], max_start)  # Can't pan before start
        x_max = min(x_range[1], max_end)  # Can't pan after end

        # Prevent zooming out beyond allowed range
        current_width = x_max - x_min
        max_width = max_end - max_start

        if current_width > max_width:
            # Force back to full allowed range
            x_min = max_start
            x_max = max_end
        elif current_width < 60:  # Minimum 1 minute visible (60 seconds)
            # Prevent over-zooming
            center = (x_range[0] + x_range[1]) / 2
            x_min = center - 30  # 30 seconds before center
            x_max = center + 30  # 30 seconds after center

            # Adjust if this pushes us out of bounds
            if x_min < max_start:
                x_min = max_start
                x_max = x_min + 60
            elif x_max > max_end:
                x_max = max_end
                x_min = x_max - 60

        # Force Y range to always be the full data range (no Y-axis zooming)
        y_min = self.data_min_y  # Always 0
        y_max = self.data_max_y  # Always 1.5x max value

        # Fix Y-axis range on the axis itself to prevent visual changes
        self.plot_widget.getAxis("left").setRange(y_min, y_max)

        # Apply corrected ranges if needed
        x_changed = abs(x_min - x_range[0]) > 0.1 or abs(x_max - x_range[1]) > 0.1
        y_changed = abs(y_min - y_range[0]) > 0.1 or abs(y_max - y_range[1]) > 0.1

        if x_changed or y_changed:
            self.vb.blockSignals(True)
            self.vb.setRange(xRange=[x_min, x_max], yRange=[y_min, y_max], padding=0)
            self.vb.blockSignals(False)

    def _redraw_plot(self):
        """Redraw the plot with current data and shaded regions."""
        if not hasattr(self, 'power_values') or not hasattr(self, 'power_times'):
            return

        # Clear previous region items only (not markers)
        for item in self.region_items:
            self.plot_widget.plotItem.removeItem(item)
        self.region_items = []

        # Always update or create the power data curve
        if self.power_curve is None:
            # Create new plot curve
            self.power_curve = self.plot_widget.plot(
                self.power_times,
                self.power_values,
                pen=pg.mkPen('b', width=2),
                name='TV Power'
            )
        else:
            # Update existing curve with new data
            self.power_curve.setData(self.power_times, self.power_values)

        # Configure tick spacing (TimeAxisItem handles formatting)
        axis = self.plot_widget.getAxis('bottom')
        axis.setTickSpacing(major=60, minor=10)  # Major ticks every minute, minor every 10 seconds

        # Draw shaded regions for completed marker pairs
        for marker_type in ['on', 'off']:
            pairs = self.marker_pairs[marker_type]

            # Only draw region if both markers exist
            if pairs['onset'] and pairs['offset']:
                onset_pos = pairs['onset'].value()
                offset_pos = pairs['offset'].value()

                # Sort positions
                start, end = sorted([onset_pos, offset_pos])

                # Determine color with transparency
                color = (76, 175, 80, 80) if marker_type == 'on' else (244, 67, 54, 80)  # RGBA

                # Create shaded region
                region = pg.LinearRegionItem(
                    values=[start, end],
                    brush=pg.mkBrush(color),
                    pen=pg.mkPen(None),  # No border
                    movable=False
                )
                self.plot_widget.plotItem.addItem(region)
                self.region_items.append(region)

                # Send region to back so markers are visible on top
                region.setZValue(-10)

    def _load_power_data(self):
        """Load power data from CSV and plot it."""
        try:
            participant_id = self.state.get_user_input("participant_id", "")
            device_id = self.state.get_user_input("device_id", "")
            username = self.state.get_user_input("username", "")

            if not all([participant_id, device_id, username]):
                return

            full_id = f"{participant_id}{device_id}"
            csv_file = f"/home/{username}/data/{full_id}_data/{full_id}_tv_power_5s.csv"

            if not os.path.exists(csv_file):
                return

            # Read CSV file and parse timestamps
            # Format: power_value;date;time (e.g., 45.2;01.15.2025;14.30.45)
            powers = []
            timestamps = []
            first_timestamp = None

            with open(csv_file, 'r') as f:
                for line in f:
                    parts = line.strip().split(';')
                    if len(parts) >= 3:
                        try:
                            power = float(parts[0])
                            date_str = parts[1]  # MM.DD.YYYY
                            time_str = parts[2]  # HH.MM.SS

                            # Parse timestamp
                            datetime_str = f"{date_str} {time_str}"
                            dt = datetime.strptime(datetime_str, "%m.%d.%Y %H.%M.%S")

                            if first_timestamp is None:
                                first_timestamp = dt

                            # Calculate seconds from first timestamp
                            elapsed_seconds = (dt - first_timestamp).total_seconds()

                            powers.append(power)
                            timestamps.append(elapsed_seconds)
                        except Exception as parse_error:
                            # Skip malformed lines
                            continue

            if powers and timestamps:
                # Store both timestamps and power values
                self.power_times = np.array(timestamps)
                self.power_values = np.array(powers)
                self.first_timestamp = first_timestamp

                # Set data boundaries for axis restrictions
                self.data_start_time = 0  # Start at 0 seconds
                self.data_end_time = self.power_times[-1]  # End at last timestamp
                self.data_min_y = 0  # Always start at 0
                self.data_max_y = max(powers) * 1.5 if powers else 100  # 1.5x max power

                # Always redraw plot with latest data
                self._redraw_plot()

                # Set initial view range (only on first load)
                if not hasattr(self, '_initial_view_set'):
                    self.vb.setRange(
                        xRange=[self.data_start_time, self.data_end_time],
                        yRange=[self.data_min_y, self.data_max_y],
                        padding=0
                    )
                    self._initial_view_set = True

                # Only log once
                if not hasattr(self, '_data_loaded_logged'):
                    self.logger.info(f"Loaded {len(powers)} power readings")
                    self._data_loaded_logged = True

                # Update bounds for markers if they exist
                if hasattr(self, 'marker_lines'):
                    for line in self.marker_lines:
                        if hasattr(line, 'setBounds'):
                            line.setBounds([self.data_start_time, self.data_end_time])

        except Exception as e:
            self.logger.error(f"Error loading power data: {e}")

    @handle_step_error
    def _launch_browser_automation(self, checked: bool = False) -> None:
        """Launch browser automation to monitor Home Assistant with comprehensive error handling."""
        try:
            self.logger.info("Starting browser automation for smart plug verification")

            # Use standard Home Assistant URL - it's always localhost:8123/history
            home_assistant_url = "http://localhost:8123/history"

            self.launch_browser_button.setEnabled(False)
            self.logger.info("Launching browser automation...")
            self.logger.info(f"Target URL: {home_assistant_url}")

            # Launch browser using process runner for better error handling
            result = self.process_runner.run_command(["xdg-open", home_assistant_url], timeout_ms=10000)

            if result and result.returncode == 0:
                self.logger.info("Browser launched successfully")
                self.logger.info("Browser launched - navigate to History page")
                self.logger.info("Look for your TV smart plug sensor")
                self.logger.info("Now test TV power on/off...")

                self.browser_launched = True
                self.power_cycle_button.setEnabled(True)

                self.logger.info("Browser automation completed - ready for user verification")
            else:
                error_msg = result.stderr if result else "Command failed"
                self.logger.error(f"Browser launch failed: {error_msg}")
                raise FlashTVError(
                    f"Browser launch failed: {error_msg}",
                    ErrorType.PROCESS_ERROR,
                    recovery_action="Try opening Home Assistant manually",
                )

        except Exception as e:
            self.logger.error(f"Error during browser automation launch: {e}")
            self._enable_manual_verification()
            raise
        finally:
            self.launch_browser_button.setEnabled(True)

    @handle_step_error
    def _capture_power_baseline(self, checked: bool = False) -> None:
        """Capture screenshot after power cycling and save to participant's data folder."""
        try:
            # Validate room name is entered
            room_name = self.room_name_input.text().strip()
            if not room_name:
                QMessageBox.warning(self, "Room Name Required", "Please enter the room name before capturing the screenshot.")
                return

            self.logger.info(f"Capturing power baseline screenshot for room: {room_name}")

            # Get participant info
            participant_id = self.state.get_user_input("participant_id", "")
            device_id = self.state.get_user_input("device_id", "")
            username = self.state.get_user_input("username", "")

            full_participant_id = f"{participant_id}{device_id}" if device_id else participant_id

            self.logger.info("Preparing to capture screenshot...")
            self.power_cycle_button.setEnabled(False)

            # Wait a moment for user to see the message
            QTimer.singleShot(2000, lambda: self._perform_screenshot_capture(full_participant_id, room_name, username))

        except Exception as e:
            self.logger.error(f"Error initiating screenshot capture: {e}")
            self.power_cycle_button.setEnabled(True)
            raise

    def _perform_screenshot_capture(self, participant_id: str, room_name: str, username: str) -> None:
        """Actually perform the screenshot capture and file operations."""
        try:
            self.logger.info(f"Starting screenshot capture for participant {participant_id}, room: {room_name}")

            # Refresh the Home Assistant page first
            self.logger.info("Refreshing Home Assistant page...")
            self.logger.debug("Refreshing Home Assistant history page")

            # Open/refresh the page
            home_assistant_url = "http://localhost:8123/history"
            subprocess.run(["xdg-open", home_assistant_url], capture_output=True)

            # Wait for page to load
            self.logger.debug("Waiting 3 seconds for page to load")
            time.sleep(3)

            # Take screenshot using gnome-screenshot or scrot
            self.logger.info("Capturing screenshot...")
            self.logger.info("Attempting to capture screenshot")

            # Try gnome-screenshot first
            screenshot_taken = False
            temp_screenshot = "/tmp/smart_plug_screenshot.png"

            # Try gnome-screenshot
            self.logger.debug("Trying gnome-screenshot command")
            result = subprocess.run(["gnome-screenshot", "-f", temp_screenshot], capture_output=True)

            if result.returncode == 0:
                screenshot_taken = True
                self.logger.info("Screenshot captured successfully with gnome-screenshot")
            else:
                self.logger.warning(f"gnome-screenshot failed: {result.stderr.decode() if result.stderr else 'Unknown error'}")
                # Try scrot as fallback
                self.logger.debug("Trying scrot command as fallback")
                result = subprocess.run(["scrot", temp_screenshot], capture_output=True)
                if result.returncode == 0:
                    screenshot_taken = True
                    self.logger.info("Screenshot captured successfully with scrot")
                else:
                    self.logger.warning(f"scrot also failed: {result.stderr.decode() if result.stderr else 'Unknown error'}")

            if not screenshot_taken:
                # Try to find any recent screenshot file
                self.logger.info("Screenshot commands failed, searching for recent screenshot files")

                # Common screenshot locations
                screenshot_dirs = [
                    f"/home/{username}/Pictures",
                    f"/home/{username}/Pictures/Screenshots",
                    f"/home/{username}/Downloads",
                    "/tmp",
                    f"/tmp/TemporaryItems",
                ]

                # Look for recent screenshot files
                found_screenshot = None
                for directory in screenshot_dirs:
                    if os.path.exists(directory):
                        pattern_list = [
                            os.path.join(directory, "*[Ss]creenshot*.png"),
                            os.path.join(directory, "*[Ss]creen*.png"),
                            os.path.join(directory, "*.png"),
                        ]

                        for pattern in pattern_list:
                            files = glob(pattern)
                            # Get files created in the last 30 seconds
                            recent_files = [f for f in files if os.path.exists(f) and (time.time() - os.path.getctime(f)) < 30]

                            if recent_files:
                                # Use the most recent file
                                found_screenshot = max(recent_files, key=os.path.getctime)
                                break

                        if found_screenshot:
                            break

                if found_screenshot:
                    temp_screenshot = found_screenshot
                    screenshot_taken = True
                    self.logger.info(f"Found screenshot at: {temp_screenshot}")
                else:
                    self.logger.error("No recent screenshot files found in any directory")

            if screenshot_taken and os.path.exists(temp_screenshot):
                # Create destination path
                data_path = f"/home/{username}/data/{participant_id}_data"
                self.logger.info(f"Creating data directory: {data_path}")
                os.makedirs(data_path, exist_ok=True)

                # Create filename with participant ID and room name
                screenshot_filename = f"{participant_id} {room_name} TV Power Baseline.png"
                destination_path = os.path.join(data_path, screenshot_filename)

                self.logger.info(f"Moving screenshot from {temp_screenshot} to {destination_path}")
                # Move and rename the screenshot
                shutil.move(temp_screenshot, destination_path)

                self.logger.info(f"Screenshot successfully saved to: {destination_path}")

                # Enable the data verified button
                self.data_verified_button.setEnabled(True)

                QMessageBox.information(
                    self,
                    "Screenshot Captured",
                    f"Power baseline screenshot captured successfully!\n\nSaved as: {screenshot_filename}\nLocation: {data_path}",
                )
            else:
                raise FlashTVError(
                    "Failed to capture screenshot",
                    ErrorType.PROCESS_ERROR,
                    recovery_action="Try taking a manual screenshot and save it to the data folder",
                )

        except Exception as e:
            self.logger.error(f"Error during screenshot capture: {e}")
            QMessageBox.warning(
                self, "Screenshot Failed", f"Failed to capture screenshot: {e}\n\nPlease take a manual screenshot and save it to the data folder."
            )
        finally:
            self.power_cycle_button.setEnabled(True)

    @handle_step_error
    def _enable_manual_verification(self) -> None:
        """Enable manual verification mode with logging."""
        try:
            self.logger.info("Enabling manual verification mode")
            self.logger.info("Manual verification mode enabled")
            self.logger.info("Please verify the smart plug is working by:")
            self.logger.info("1. Turning TV off and on")
            self.logger.info("2. Checking smart plug LED changes")
            self.logger.info("3. Confirming power monitoring works")

            self.data_verified_button.setEnabled(True)
            self.data_verified_button.setText("✓ Manually Verified - Smart Plug Working")

            self.logger.info("Manual verification mode enabled successfully")

        except Exception as e:
            self.logger.error(f"Error enabling manual verification: {e}")
            raise FlashTVError(
                f"Failed to enable manual verification: {e}",
                ErrorType.UI_ERROR,
                recovery_action="Try refreshing the page",
            )

    def _safe_update_status(self) -> None:
        """Safely update connection status with error handling."""
        try:
            self._update_status()
        except Exception as e:
            self.logger.error(f"Error updating status: {e}")

    def _update_status(self) -> None:
        """Update connection status periodically with enhanced tracking."""
        # Check if ha_connection_status widget exists
        if not hasattr(self, 'ha_connection_status'):
            return

        # Always check status, regardless of browser launch state
        if True:
            # Update last checked timestamp
            now = datetime.now()
            self.last_checked = now

            # Actually ping Home Assistant
            import urllib.request
            try:
                self.logger.debug("Pinging Home Assistant at localhost:8123")
                response = urllib.request.urlopen("http://localhost:8123", timeout=2)
                if response.getcode() == 200:
                    self.last_connected = now
                    self.logger.info("Home Assistant connection verified - server responding")

                    # Format timestamps for display
                    last_connected_str = self.last_connected.strftime("%H:%M:%S")
                    last_checked_str = self.last_checked.strftime("%H:%M:%S")

                    self.ha_connection_status.setText(
                        f"🌐 Home Assistant connection: Connected ✓\n"
                        f"Last connected: {last_connected_str} | Last checked: {last_checked_str}"
                    )
                else:
                    self.logger.warning(f"Home Assistant returned unexpected code: {response.getcode()}")
                    last_checked_str = self.last_checked.strftime("%H:%M:%S")
                    last_connected_str = self.last_connected.strftime("%H:%M:%S") if self.last_connected else "Never"

                    self.ha_connection_status.setText(
                        f"🌐 Home Assistant connection: Unexpected response\n"
                        f"Last connected: {last_connected_str} | Last checked: {last_checked_str}"
                    )
            except Exception as e:
                self.logger.error(f"Failed to ping Home Assistant: {e}")
                last_checked_str = self.last_checked.strftime("%H:%M:%S")
                last_connected_str = self.last_connected.strftime("%H:%M:%S") if self.last_connected else "Never"

                self.ha_connection_status.setText(
                    f"🌐 Home Assistant connection: Not reachable\n"
                    f"Last connected: {last_connected_str} | Last checked: {last_checked_str}"
                )

            # Check if CSV file exists and display its content
            participant_id = self.state.get_user_input("participant_id", "")
            device_id = self.state.get_user_input("device_id", "")
            username = self.state.get_user_input("username", "")

            if participant_id and device_id and username:
                full_id = f"{participant_id}{device_id}"
                csv_file = f"/home/{username}/data/{full_id}_data/{full_id}_tv_power_5s.csv"

                if os.path.exists(csv_file):
                    # Read and display CSV file content
                    self._display_csv_file(csv_file, full_id)

                    # Reload power data for the plot
                    self._load_power_data()

                    # Only log once when file is first detected
                    if not hasattr(self, '_csv_file_detected'):
                        self.logger.info(f"Smart plug CSV file found: {csv_file}")
                        self.logger.info(f"Smart plug data file detected: {full_id}_tv_power_5s.csv")
                        self.logger.info("CSV data is being displayed in the panel")
                        self.logger.info("Interactive plot is updating - click to mark ON/OFF periods")
                        self._csv_file_detected = True
                else:
                    self.logger.debug(f"Smart plug CSV file not found yet: {csv_file}")
                    self.csv_output.setPlainText(f"Waiting for file: {csv_file}\n\nThe file will be created once Home Assistant starts logging power data.")

    def _display_csv_file(self, csv_path: str, participant_id: str) -> None:
        """Display the last 100 lines of the CSV file content similar to stderr log display."""
        try:
            with open(csv_path, 'r', errors='ignore') as f:
                content = f.read()

            # Clear current content
            self.csv_output.clear()

            # Parse and format CSV data
            # Expected format from configuration.yaml line 46-47:
            # {{states('sensor.third_reality_inc_3rsp02028bz_power')}};{{now().strftime('%m.%d.%Y')}};{{now().strftime('%H.%M.%S')}}
            # Format: power_value;date;time

            all_lines = content.splitlines()

            # Get only the last 100 lines
            last_100_lines = all_lines[-100:] if len(all_lines) > 100 else all_lines

            for line in last_100_lines:
                line = line.strip()
                if not line:
                    self.csv_output.append(line)
                    continue

                # Parse CSV line
                parts = line.split(';')
                if len(parts) >= 3:
                    power = parts[0]
                    date = parts[1]
                    time = parts[2]

                    # Format the line nicely
                    formatted_line = f"{date} {time} | Power: {power}W"
                    self.csv_output.append(formatted_line)
                else:
                    # Malformed line, display as-is
                    self.csv_output.append(line)

            # Auto-scroll to bottom to show most recent data
            self.csv_output.verticalScrollBar().setValue(
                self.csv_output.verticalScrollBar().maximum()
            )

        except Exception as e:
            self.logger.error(f"Error displaying CSV file {csv_path}: {e}")
            self.csv_output.setPlainText(f"Error reading CSV file: {e}")

    @handle_step_error
    def _data_verified(self, checked: bool = False) -> None:
        """Handle data verification confirmation with comprehensive validation."""
        try:
            reply = QMessageBox.question(
                self,
                "Confirm Verification",
                "Did you successfully see the TV power changes in the monitoring system?\n\n"
                "• TV OFF showed low/zero power\n"
                "• TV ON showed increased power usage",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.logger.info("User confirmed smart plug data verification")
                self.logger.info("Smart plug data verification successful!")
                self.logger.info("Power monitoring is working correctly")

                # Save verification status
                self.state.set_user_input("smart_plug_verified", True)
                self.state.set_user_input(
                    "smart_plug_verification_method",
                    "interactive_plot",
                )

                # Save marked ON/OFF periods and generate report
                if self._are_all_markers_complete():
                    # Extract positions from InfiniteLine objects
                    on_onset = self.marker_pairs['on']['onset'].value()
                    on_offset = self.marker_pairs['on']['offset'].value()
                    off_onset = self.marker_pairs['off']['onset'].value()
                    off_offset = self.marker_pairs['off']['offset'].value()

                    self.state.set_user_input("tv_on_period_start", min(on_onset, on_offset))
                    self.state.set_user_input("tv_on_period_end", max(on_onset, on_offset))
                    self.state.set_user_input("tv_off_period_start", min(off_onset, off_offset))
                    self.state.set_user_input("tv_off_period_end", max(off_onset, off_offset))
                    self.logger.info(f"Saved ON period: {min(on_onset, on_offset):.2f} - {max(on_onset, on_offset):.2f}")
                    self.logger.info(f"Saved OFF period: {min(off_onset, off_offset):.2f} - {max(off_onset, off_offset):.2f}")

                    # Save plot image and marker info to data folder
                    self._save_plot_and_marker_info()

                # Persist state
                if self.state_manager:
                    self.state_manager.save_state(self.state)

                self.continue_button.setEnabled(True)
                self.update_status(StepStatus.COMPLETED)

                # Stop status timer
                if self.status_timer.isActive():
                    self.status_timer.stop()

                self.logger.info("Smart plug verification completed successfully")
            else:
                self.logger.warning("User did not confirm verification")
                self.logger.info("Verification not confirmed")
                self.logger.info("Please check connections and try again")

        except Exception as e:
            self.logger.error(f"Error during data verification: {e}")
            raise FlashTVError(
                f"Failed to complete verification: {e}",
                ErrorType.PROCESS_ERROR,
                recovery_action="Check smart plug connections and try again",
            )

    def _save_plot_and_marker_info(self) -> None:
        """Save plot image and marker information to the data folder."""
        try:
            # Get participant info
            participant_id = self.state.get_user_input("participant_id", "")
            device_id = self.state.get_user_input("device_id", "")
            username = self.state.get_user_input("username", "")

            if not all([participant_id, device_id, username]):
                self.logger.error("Missing participant info for saving plot")
                return

            full_id = f"{participant_id}{device_id}"
            data_path = f"/home/{username}/data/{full_id}_data"

            # Ensure data directory exists
            os.makedirs(data_path, exist_ok=True)

            # Save plot image using pyqtgraph exporter
            from pyqtgraph.exporters import ImageExporter

            plot_filename = f"{full_id}_tv_power_verification_plot.png"
            plot_path = os.path.join(data_path, plot_filename)

            exporter = ImageExporter(self.plot_widget.plotItem)
            exporter.parameters()['width'] = 1920  # High resolution
            exporter.export(plot_path)

            self.logger.info(f"Plot image saved to: {plot_path}")

            # Extract marker positions (in seconds)
            on_onset = self.marker_pairs['on']['onset'].value()
            on_offset = self.marker_pairs['on']['offset'].value()
            off_onset = self.marker_pairs['off']['onset'].value()
            off_offset = self.marker_pairs['off']['offset'].value()

            # Convert time positions to indices for data extraction
            on_start_time = min(on_onset, on_offset)
            on_end_time = max(on_onset, on_offset)
            off_start_time = min(off_onset, off_offset)
            off_end_time = max(off_onset, off_offset)

            # Find indices for ON period
            on_mask = (self.power_times >= on_start_time) & (self.power_times <= on_end_time)
            on_values = self.power_values[on_mask]
            on_start_idx = np.argmax(self.power_times >= on_start_time)
            on_end_idx = np.argmax(self.power_times > on_end_time) - 1
            if on_end_idx < on_start_idx:
                on_end_idx = len(self.power_times) - 1

            # Calculate ON period stats
            on_avg = np.mean(on_values)
            on_std = np.std(on_values)
            on_min = np.min(on_values)
            on_max = np.max(on_values)

            # Find indices for OFF period
            off_mask = (self.power_times >= off_start_time) & (self.power_times <= off_end_time)
            off_values = self.power_values[off_mask]
            off_start_idx = np.argmax(self.power_times >= off_start_time)
            off_end_idx = np.argmax(self.power_times > off_end_time) - 1
            if off_end_idx < off_start_idx:
                off_end_idx = len(self.power_times) - 1

            # Calculate OFF period stats
            off_avg = np.mean(off_values)
            off_std = np.std(off_values)
            off_min = np.min(off_values)
            off_max = np.max(off_values)

            # Create marker info text file
            info_filename = f"{full_id}_tv_power_verification_markers.txt"
            info_path = os.path.join(data_path, info_filename)

            with open(info_path, 'w') as f:
                f.write("TV POWER VERIFICATION - MARKER INFORMATION\n")
                f.write("=" * 60 + "\n\n")
                f.write(f"Participant ID: {full_id}\n")
                f.write(f"Verification Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"First Timestamp: {self.first_timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total Data Points: {len(self.power_values)}\n")
                f.write(f"Total Duration: {self.power_times[-1]:.2f} seconds ({self.power_times[-1]/60:.2f} minutes)\n\n")

                f.write("ON PERIOD MARKERS\n")
                f.write("-" * 60 + "\n")
                f.write(f"Start Time: {on_start_time:.2f} seconds ({on_start_time/60:.2f} minutes)\n")
                f.write(f"End Time: {on_end_time:.2f} seconds ({on_end_time/60:.2f} minutes)\n")
                f.write(f"Start Index: {on_start_idx}\n")
                f.write(f"End Index: {on_end_idx}\n")
                f.write(f"Duration: {on_end_time - on_start_time:.2f} seconds ({(on_end_time - on_start_time)/60:.2f} minutes)\n")
                f.write(f"Data Points: {len(on_values)}\n")
                f.write(f"Average Power: {on_avg:.2f} W\n")
                f.write(f"Std Deviation: {on_std:.2f} W\n")
                f.write(f"Min Power: {on_min:.2f} W\n")
                f.write(f"Max Power: {on_max:.2f} W\n\n")

                f.write("OFF PERIOD MARKERS\n")
                f.write("-" * 60 + "\n")
                f.write(f"Start Time: {off_start_time:.2f} seconds ({off_start_time/60:.2f} minutes)\n")
                f.write(f"End Time: {off_end_time:.2f} seconds ({off_end_time/60:.2f} minutes)\n")
                f.write(f"Start Index: {off_start_idx}\n")
                f.write(f"End Index: {off_end_idx}\n")
                f.write(f"Duration: {off_end_time - off_start_time:.2f} seconds ({(off_end_time - off_start_time)/60:.2f} minutes)\n")
                f.write(f"Data Points: {len(off_values)}\n")
                f.write(f"Average Power: {off_avg:.2f} W\n")
                f.write(f"Std Deviation: {off_std:.2f} W\n")
                f.write(f"Min Power: {off_min:.2f} W\n")
                f.write(f"Max Power: {off_max:.2f} W\n\n")

                f.write("POWER DIFFERENCE ANALYSIS\n")
                f.write("-" * 60 + "\n")
                f.write(f"Average Power Difference (ON - OFF): {on_avg - off_avg:.2f} W\n")
                f.write(f"Power Ratio (ON / OFF): {on_avg / off_avg if off_avg > 0 else float('inf'):.2f}x\n\n")

                f.write("RAW MARKER POSITIONS (Time in seconds)\n")
                f.write("-" * 60 + "\n")
                f.write(f"ON Onset: {on_onset:.2f} seconds\n")
                f.write(f"ON Offset: {on_offset:.2f} seconds\n")
                f.write(f"OFF Onset: {off_onset:.2f} seconds\n")
                f.write(f"OFF Offset: {off_offset:.2f} seconds\n")

            self.logger.info(f"Marker info saved to: {info_path}")

            QMessageBox.information(
                self,
                "Data Saved",
                f"Plot and marker information saved successfully!\n\n"
                f"Plot: {plot_filename}\n"
                f"Info: {info_filename}\n\n"
                f"Location: {data_path}"
            )

        except Exception as e:
            self.logger.error(f"Error saving plot and marker info: {e}")
            QMessageBox.warning(
                self,
                "Save Error",
                f"Failed to save plot and marker info: {e}"
            )

    @handle_step_error
    def _on_continue_clicked(self, checked: bool = False) -> None:
        """Handle continue button click with validation."""
        try:
            if self.is_completed() or self.continue_button.isEnabled():
                verification_method = self.state.get_user_input("smart_plug_verification_method", "unknown")
                self.logger.info(f"Smart plug verification completed via {verification_method} method")

                # Final state persistence
                if self.state_manager:
                    self.state_manager.save_state(self.state)

                self.request_next_step.emit()
            else:
                self.logger.warning("Continue clicked but verification not completed")

        except Exception as e:
            self.logger.error(f"Error during continue action: {e}")
            raise FlashTVError(
                f"Failed to complete verification step: {e}",
                ErrorType.PROCESS_ERROR,
                recovery_action="Complete the verification process first",
            )

    @handle_step_error
    def activate_step(self) -> None:
        """Activate the smart plug verification step with state restoration."""
        super().activate_step()

        self.logger.info("Smart plug verification step activated")

        # Start status monitoring immediately when step is activated
        self.logger.info("Starting status monitoring timer")
        self.status_timer.start(5000)  # Check every 5 seconds

        # Load power data for the plot
        self._load_power_data()

        # Check if already verified
        if self.state.get_user_input("smart_plug_verified", False):
            verification_method = self.state.get_user_input("smart_plug_verification_method", "previous")
            self.logger.info(f"Smart plug already verified (method: {verification_method})")
            self.continue_button.setEnabled(True)
            self.update_status(StepStatus.COMPLETED)
            self.logger.info("Smart plug verification already completed, skipping")
        else:
            # Not verified yet - show initial message
            self.logger.info("Monitoring Home Assistant connection and TV power data...")
            self.logger.info("Check the panel for live data updates")

    def cleanup(self) -> None:
        """Clean up resources when step is destroyed."""
        try:
            self.logger.info("Cleaning up smart plug verification step")

            # Stop status timer
            if hasattr(self, "status_timer") and self.status_timer.isActive():
                self.status_timer.stop()

            # Call parent cleanup
            super().cleanup()

        except Exception as e:
            self.logger.error(f"Error during verification step cleanup: {e}")

    def _cleanup_step_resources(self) -> None:
        """Clean up step-specific resources."""
        try:
            # Stop the status monitoring timer
            if hasattr(self, "status_timer") and self.status_timer.isActive():
                self.status_timer.stop()
                self.logger.info("Stopped status monitoring timer")

            # Final state save before cleanup
            if self.state_manager:
                self.state_manager.save_state(self.state)

            self.logger.info("Smart plug verification step cleanup completed")

        except Exception as e:
            self.logger.error(f"Error during step cleanup: {e}")
