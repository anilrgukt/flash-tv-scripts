from __future__ import annotations

import contextlib
import importlib.util
from datetime import datetime
import math
from pathlib import Path
import sys
import types
from typing import Any, Iterator, cast


GUI_DIR = Path(__file__).resolve().parents[2]
HELPER_FILE = GUI_DIR / "utils" / "pyqtgraph_helpers.py"


def _load_time_axis_item():
    module_name = "_isolated_pyqtgraph_helpers"

    numpy_module = cast(Any, types.ModuleType("numpy"))
    setattr(
        numpy_module,
        "isfinite",
        lambda value: value == value and value not in (float("inf"), float("-inf")),
    )
    setattr(numpy_module, "ceil", lambda value: math.ceil(value))
    pyqtgraph_module = cast(Any, types.ModuleType("pyqtgraph"))

    class AxisItem:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs
            self.auto_si_prefix = None

        def enableAutoSIPrefix(self, value):
            self.auto_si_prefix = value

    setattr(pyqtgraph_module, "AxisItem", AxisItem)

    replacements = {
        "numpy": numpy_module,
        "pyqtgraph": pyqtgraph_module,
    }

    @contextlib.contextmanager
    def temporary_modules() -> Iterator[None]:
        original = {name: sys.modules.get(name) for name in replacements}
        try:
            sys.modules.update(replacements)
            yield
        finally:
            for name, module in original.items():
                if module is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = module

    with temporary_modules():
        spec = importlib.util.spec_from_file_location(module_name, HELPER_FILE)
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
        finally:
            sys.modules.pop(module_name, None)
    return module.TimeAxisItem


def _ts(year: int, month: int, day: int, hour: int, minute: int, second: int) -> float:
    return datetime(year, month, day, hour, minute, second).timestamp()


class TestTimeAxisFormatting:
    def test_formats_short_spans_with_seconds(self):
        TimeAxisItem = _load_time_axis_item()
        axis = TimeAxisItem(orientation="bottom")
        values = [_ts(2025, 1, 1, 12, 0, 0), _ts(2025, 1, 1, 12, 0, 30)]

        labels = axis.tickStrings(values, scale=1.0, spacing=5.0)

        assert labels == ["12:00:00", "12:00:30"]

    def test_formats_medium_spans_with_hours_and_minutes(self):
        TimeAxisItem = _load_time_axis_item()
        axis = TimeAxisItem(orientation="bottom")
        values = [_ts(2025, 1, 1, 12, 0, 0), _ts(2025, 1, 1, 14, 30, 0)]

        labels = axis.tickStrings(values, scale=1.0, spacing=300.0)

        assert labels == ["12:00", "14:30"]

    def test_formats_multi_day_spans_with_date_and_time(self):
        TimeAxisItem = _load_time_axis_item()
        axis = TimeAxisItem(orientation="bottom")
        values = [_ts(2025, 1, 1, 8, 15, 0), _ts(2025, 1, 3, 9, 45, 0)]

        labels = axis.tickStrings(values, scale=1.0, spacing=3600.0)

        assert labels == ["01/01 08:15", "01/03 09:45"]

    def test_formats_rollover_across_midnight_without_losing_seconds(self):
        TimeAxisItem = _load_time_axis_item()
        axis = TimeAxisItem(orientation="bottom")
        values = [_ts(2025, 1, 1, 23, 59, 50), _ts(2025, 1, 2, 0, 0, 10)]

        labels = axis.tickStrings(values, scale=1.0, spacing=5.0)

        assert labels == ["23:59:50", "00:00:10"]
