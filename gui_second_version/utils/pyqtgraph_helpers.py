"""PyQtGraph helper classes and utilities."""

from __future__ import annotations

from datetime import datetime

import numpy as np
import pyqtgraph as pg


class TimeAxisItem(pg.AxisItem):
    """Axis item for local wall-clock timestamps."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.enableAutoSIPrefix(False)  # Disable SI prefix scaling

    def tickValues(self, minVal, maxVal, size):
        """Override to generate a reasonable number of ticks (max ~20)."""
        # Calculate range
        data_range = maxVal - minVal

        if data_range <= 0:
            return []

        # Determine appropriate tick spacing based on range
        # Aim for 10-20 ticks
        target_ticks = 15
        raw_spacing = data_range / target_ticks

        # Round to nice intervals (1s, 5s, 10s, 30s, 1min, 5min, 10min, 30min, 1hr, etc.)
        nice_intervals = [
            1,
            5,
            10,
            30,
            60,
            300,
            600,
            1800,
            3600,
            7200,
            10800,
            21600,
            43200,
            86400,
        ]

        # Find the closest nice interval
        spacing = min(nice_intervals, key=lambda x: abs(x - raw_spacing))

        # Generate major ticks
        major_ticks = []
        tick = np.ceil(minVal / spacing) * spacing
        while tick <= maxVal:
            major_ticks.append(tick)
            tick += spacing

        # Generate minor ticks (5x denser)
        minor_spacing = spacing / 5
        minor_ticks = []
        tick = np.ceil(minVal / minor_spacing) * minor_spacing
        while tick <= maxVal:
            if tick not in major_ticks:  # Don't duplicate major ticks
                minor_ticks.append(tick)
            tick += minor_spacing

        return [(spacing, major_ticks), (minor_spacing, minor_ticks)]

    def tickStrings(self, values, scale, spacing):
        """Format tick labels as local wall-clock time."""
        strings = []
        finite_values = [value for value in values if np.isfinite(value)]
        visible_span = (
            max(finite_values) - min(finite_values)
            if len(finite_values) >= 2
            else spacing
        )

        for value in values:
            if not np.isfinite(value):
                strings.append("")
                continue

            try:
                local_dt = datetime.fromtimestamp(float(value))
            except (OverflowError, OSError, ValueError):
                strings.append("")
                continue

            if visible_span < 3600:
                strings.append(local_dt.strftime("%H:%M:%S"))
            elif visible_span <= 86400:
                strings.append(local_dt.strftime("%H:%M"))
            else:
                strings.append(local_dt.strftime("%m/%d %H:%M"))

        return strings
