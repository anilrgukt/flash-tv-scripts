"""UI component factory for consistent widget creation."""

from __future__ import annotations

from enum import StrEnum
from typing import Callable

from PyQt6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QListWidget,
    QProgressBar,
)
from PyQt6.QtGui import QFont

from core.config import get_config


class ButtonStyle(StrEnum):
    """Button style types."""

    PRIMARY = "primary"
    SECONDARY = "secondary"
    SUCCESS = "success"
    WARNING = "warning"
    DANGER = "danger"


class UIFactory:
    """Factory for creating standardized UI components."""

    def __init__(self):
        self.config = get_config()

    def create_group_box(
        self,
        title: str,
        spacing: int | None = None,
        margins: tuple[int, int, int, int] | None = None,
    ) -> tuple[QGroupBox, QVBoxLayout]:
        """Create a standardized group box with layout."""
        group_box = QGroupBox(title)

        # Set larger font for group box title
        font = QFont()
        font.setPointSize(24)
        font.setBold(True)
        group_box.setFont(font)

        layout = QVBoxLayout(group_box)

        # Apply consistent spacing and margins
        layout.setSpacing(spacing or self.config.content_spacing)

        if margins:
            layout.setContentsMargins(*margins)
        else:
            margin = self.config.default_padding
            layout.setContentsMargins(margin, margin, margin, margin)

        return group_box, layout

    def create_action_button(
        self,
        text: str,
        callback: Callable | None = None,
        style: ButtonStyle = ButtonStyle.PRIMARY,
        height: int | None = None,
        enabled: bool = True,
    ) -> QPushButton:
        """Create a standardized action button."""
        button = QPushButton(text)

        # Set larger font for button
        font = QFont()
        font.setPointSize(20)
        font.setBold(True)
        button.setFont(font)

        # Set height
        button_height = height or self.config.action_button_height
        button.setFixedHeight(button_height)

        # Apply style
        button.setStyleSheet(self._get_button_style(style))

        # Connect callback
        if callback:
            button.clicked.connect(callback)

        button.setEnabled(enabled)

        return button

    def create_standard_button(
        self, text: str, callback: Callable | None = None, enabled: bool = True
    ) -> QPushButton:
        """Create a standard-sized button."""
        button = QPushButton(text)

        # Set larger font for button
        font = QFont()
        font.setPointSize(20)
        font.setBold(True)
        button.setFont(font)

        button.setFixedHeight(self.config.standard_button_height)

        if callback:
            button.clicked.connect(callback)

        button.setEnabled(enabled)

        return button

    def create_continue_button(
        self, callback: Callable, text: str = "Continue to Next Step"
    ) -> tuple[QHBoxLayout, QPushButton]:
        """Create a standardized continue button with layout."""
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, self.config.section_spacing, 0, 0)

        continue_button = self.create_standard_button(text, callback, enabled=False)

        button_layout.addStretch()
        button_layout.addWidget(continue_button)

        return button_layout, continue_button

    def create_input_field(
        self,
        placeholder: str = "",
        height: int | None = None,
        validator: Callable[[str], tuple[bool, str]] | None = None,
    ) -> QLineEdit:
        """Create a standardized input field."""
        input_field = QLineEdit()
        input_field.setPlaceholderText(placeholder)

        # Set larger font for input field
        font = QFont()
        font.setPointSize(20)
        input_field.setFont(font)

        if height:
            input_field.setFixedHeight(height)
        else:
            input_field.setMinimumHeight(40)

        # Add validation if provided
        if validator:

            def on_text_changed():
                text = input_field.text()
                is_valid, message = validator(text)

                if is_valid:
                    input_field.setStyleSheet("")
                    input_field.setToolTip("")
                else:
                    input_field.setStyleSheet("border: 1px solid red;")
                    input_field.setToolTip(message)

            input_field.textChanged.connect(on_text_changed)

        return input_field

    def create_text_area(
        self,
        placeholder: str = "",
        max_height: int | None = None,
        min_height: int | None = None,
        read_only: bool = False,
    ) -> QTextEdit:
        """Create a standardized text area."""
        text_area = QTextEdit()
        text_area.setPlaceholderText(placeholder)
        text_area.setReadOnly(read_only)

        # Set larger font for text area
        font = QFont()
        font.setPointSize(18)
        text_area.setFont(font)

        if max_height:
            text_area.setMaximumHeight(max_height)
        if min_height:
            text_area.setMinimumHeight(min_height)

        return text_area

    def create_checkbox(
        self, text: str, callback: Callable | None = None, checked: bool = False
    ) -> QCheckBox:
        """Create a standardized checkbox."""
        checkbox = QCheckBox(text)
        checkbox.setChecked(checked)

        # Set larger font for checkbox
        font = QFont()
        font.setPointSize(20)
        checkbox.setFont(font)

        if callback:
            checkbox.stateChanged.connect(callback)

        return checkbox

    def create_label(
        self, text: str, word_wrap: bool = True, style: str | None = None
    ) -> QLabel:
        """Create a standardized label."""
        label = QLabel(text)
        label.setWordWrap(word_wrap)

        # Set larger font for label
        font = QFont()
        font.setPointSize(20)
        label.setFont(font)

        if style:
            label.setStyleSheet(style)

        return label

    def create_status_label(self, text: str, status_type: str = "info") -> QLabel:
        """Create a status label with appropriate styling."""
        label = QLabel(text)
        label.setWordWrap(True)

        # Set larger font for status label
        font = QFont()
        font.setPointSize(20)
        font.setBold(True)
        label.setFont(font)

        styles = {
            "info": "color: #1976d2; font-weight: bold; padding: 5px;",
            "success": "color: #2e7d32; font-weight: bold; padding: 5px;",
            "warning": "color: #f57c00; font-weight: bold; padding: 5px;",
            "error": "color: #c62828; font-weight: bold; padding: 5px;",
        }

        label.setStyleSheet(styles.get(status_type, styles["info"]))

        return label

    def create_list_widget(
        self, max_height: int | None = None, min_height: int | None = None
    ) -> QListWidget:
        """Create a standardized list widget."""
        list_widget = QListWidget()

        # Set larger font for list widget
        font = QFont()
        font.setPointSize(18)
        list_widget.setFont(font)

        if max_height:
            list_widget.setMaximumHeight(max_height)
        if min_height:
            list_widget.setMinimumHeight(min_height)

        return list_widget

    def create_progress_bar(
        self, minimum: int = 0, maximum: int = 100, value: int = 0
    ) -> QProgressBar:
        """Create a standardized progress bar."""
        progress_bar = QProgressBar()
        progress_bar.setMinimum(minimum)
        progress_bar.setMaximum(maximum)
        progress_bar.setValue(value)

        # Set larger font for progress bar
        font = QFont()
        font.setPointSize(18)
        progress_bar.setFont(font)

        return progress_bar

    def create_horizontal_layout(
        self,
        spacing: int | None = None,
        margins: tuple[int, int, int, int] | None = None,
    ) -> QHBoxLayout:
        """Create a standardized horizontal layout."""
        layout = QHBoxLayout()
        layout.setSpacing(spacing or self.config.content_spacing)

        if margins:
            layout.setContentsMargins(*margins)

        return layout

    def create_vertical_layout(
        self,
        spacing: int | None = None,
        margins: tuple[int, int, int, int] | None = None,
    ) -> QVBoxLayout:
        """Create a standardized vertical layout."""
        layout = QVBoxLayout()
        layout.setSpacing(spacing or self.config.content_spacing)

        if margins:
            layout.setContentsMargins(*margins)

        return layout

    def create_main_step_layout(self) -> QVBoxLayout:
        """Create the standard main layout for step content."""
        layout = QVBoxLayout()
        layout.setContentsMargins(
            self.config.default_margin,
            self.config.default_margin,
            self.config.default_margin,
            self.config.default_margin,
        )
        layout.setSpacing(self.config.section_spacing)

        return layout

    def create_horizontal_section(
        self,
        left_widget: QWidget,
        right_widget: QWidget,
        left_stretch: int = 1,
        right_stretch: int = 1,
        spacing: int | None = None,
    ) -> QHBoxLayout:
        """Create a horizontal section with two widgets."""
        layout = self.create_horizontal_layout(spacing=spacing or 12)

        layout.addWidget(left_widget, left_stretch)
        layout.addWidget(right_widget, right_stretch)

        return layout

    def _get_button_style(self, style: ButtonStyle) -> str:
        """Get CSS style for button type."""
        styles = {
            ButtonStyle.PRIMARY: """
                QPushButton {
                    background-color: #1976d2;
                    color: white;
                    border: none;
                    border-radius: 3px;
                    font-weight: bold;
                    font-size: 20pt;
                }
                QPushButton:hover {
                    background-color: #1565c0;
                }
                QPushButton:pressed {
                    background-color: #0d47a1;
                }
                QPushButton:disabled {
                    background-color: #ccc;
                    color: #666;
                }
            """,
            ButtonStyle.SECONDARY: """
                QPushButton {
                    background-color: #f5f5f5;
                    color: #333;
                    border: 1px solid #ddd;
                    border-radius: 3px;
                    font-size: 20pt;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;
                }
                QPushButton:pressed {
                    background-color: #d5d5d5;
                }
            """,
            ButtonStyle.SUCCESS: """
                QPushButton {
                    background-color: #2e7d32;
                    color: white;
                    border: none;
                    border-radius: 3px;
                    font-weight: bold;
                    font-size: 20pt;
                }
                QPushButton:hover {
                    background-color: #1b5e20;
                }
            """,
            ButtonStyle.WARNING: """
                QPushButton {
                    background-color: #f57c00;
                    color: white;
                    border: none;
                    border-radius: 3px;
                    font-weight: bold;
                    font-size: 20pt;
                }
                QPushButton:hover {
                    background-color: #ef6c00;
                }
            """,
            ButtonStyle.DANGER: """
                QPushButton {
                    background-color: #c62828;
                    color: white;
                    border: none;
                    border-radius: 3px;
                    font-weight: bold;
                    font-size: 20pt;
                }
                QPushButton:hover {
                    background-color: #b71c1c;
                }
            """,
        }

        return styles.get(style, styles[ButtonStyle.PRIMARY])


# Global factory instance
_ui_factory = None


def get_ui_factory() -> UIFactory:
    """Get the global UI factory instance."""
    global _ui_factory
    if _ui_factory is None:
        _ui_factory = UIFactory()
    return _ui_factory
