from __future__ import annotations

import contextlib
import importlib.util
from pathlib import Path
import sys
import types
from typing import Any, Iterator, cast

GUI_DIR = Path(__file__).resolve().parents[2]
UTILS_DIR = GUI_DIR / "utils"


@contextlib.contextmanager
def _temporary_modules(replacements: dict[str, types.ModuleType]) -> Iterator[None]:
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


def _load_utils_modules():
    package_name = "_isolated_test_utils"
    package = types.ModuleType(package_name)
    package.__path__ = [str(UTILS_DIR)]

    numpy_stub = cast(Any, types.ModuleType("numpy"))
    setattr(numpy_stub, "load", lambda *_args, **_kwargs: None)
    setattr(numpy_stub, "floating", float)

    replacements = {
        package_name: package,
        "numpy": numpy_stub,
    }

    loaded_modules = []
    with _temporary_modules(replacements):
        for module_name in ["log_tailer", "gaze_log_parser"]:
            qualified_name = f"{package_name}.{module_name}"
            spec = importlib.util.spec_from_file_location(
                qualified_name,
                UTILS_DIR / f"{module_name}.py",
            )
            assert spec is not None
            assert spec.loader is not None
            module = importlib.util.module_from_spec(spec)
            sys.modules[qualified_name] = module
            try:
                spec.loader.exec_module(module)
            finally:
                sys.modules.pop(qualified_name, None)
            loaded_modules.append(module)

    return loaded_modules[1].GazeLogParser, loaded_modules[0].StderrLogTailer


class TestKnownSafeErrorFiltering:
    def test_gaze_parser_recognizes_known_safe_messages_case_insensitively(self):
        GazeLogParser, _ = _load_utils_modules()
        parser = GazeLogParser(use_efficient_tailing=False)

        assert parser.is_known_minor_error("deprecationwarning: legacy path")
        assert parser.is_known_minor_error("LOADING SYMBOL SAVED BY PREVIOUS VERSION")

    def test_gaze_parser_leaves_real_errors_unfiltered(self):
        GazeLogParser, _ = _load_utils_modules()
        parser = GazeLogParser(use_efficient_tailing=False)

        assert not parser.is_known_minor_error("RuntimeError: camera pipeline failed")
        assert parser.is_known_minor_error("Traceback: unexpected exception")

    def test_stderr_tailer_filters_only_patterns_the_app_marks_safe(
        self, tmp_path: Path
    ):
        GazeLogParser, StderrLogTailer = _load_utils_modules()
        stderr_log = tmp_path / "stderr.log"
        stderr_log.write_text(
            "Loading symbol saved by previous version\n"
            "Traceback: unexpected exception\n"
            "RuntimeError: camera pipeline failed\n"
            "Critical failure in service startup\n",
            encoding="utf-8",
        )

        parser = GazeLogParser(use_efficient_tailing=False)
        tailer = StderrLogTailer(is_error_func=parser.is_known_minor_error)

        _, error_lines = tailer.get_new_content_with_errors(str(stderr_log))

        assert error_lines == [
            "RuntimeError: camera pipeline failed",
            "Critical failure in service startup",
        ]

    def test_stderr_tailer_only_returns_real_errors(self, tmp_path: Path):
        GazeLogParser, StderrLogTailer = _load_utils_modules()
        stderr_log = tmp_path / "stderr.log"
        stderr_log.write_text(
            "Loading symbol saved by previous version\n"
            "RuntimeError: camera pipeline failed\n"
            "DeprecationWarning: old API\n"
            "Critical failure in service startup\n",
            encoding="utf-8",
        )

        parser = GazeLogParser(use_efficient_tailing=False)
        tailer = StderrLogTailer(is_error_func=parser.is_known_minor_error)

        all_lines, error_lines = tailer.get_new_content_with_errors(str(stderr_log))

        assert len(all_lines) == 4
        assert error_lines == [
            "RuntimeError: camera pipeline failed",
            "Critical failure in service startup",
        ]

    def test_stderr_tailer_treats_normal_startup_messages_as_safe(self, tmp_path: Path):
        GazeLogParser, StderrLogTailer = _load_utils_modules()
        stderr_log = tmp_path / "stderr.log"
        stderr_log.write_text(
            "Loading symbol saved by previous version\n"
            "Symbol successfully upgraded!\n"
            "Resource temporarily unavailable\n",
            encoding="utf-8",
        )

        parser = GazeLogParser(use_efficient_tailing=False)
        tailer = StderrLogTailer(is_error_func=parser.is_known_minor_error)

        _, error_lines = tailer.get_new_content_with_errors(str(stderr_log))

        assert error_lines == []
