"""Instruction modal dialog for displaying detailed step instructions."""

from __future__ import annotations

from config.ui_config import UI_CONFIG
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class InstructionModal(QDialog):
    """Modal dialog for displaying detailed instructions."""

    def __init__(
        self,
        title: str,
        instructions: str | list[str],
        parent=None,
        width: int = 700,
        height: int = 500,
    ):
        """Initialize the instruction modal.

        Args:
            title: Dialog title
            instructions: Either a single string or list of instruction steps
            parent: Parent widget
            width: Dialog width
            height: Dialog height
        """
        super().__init__(parent)

        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(width, height)

        self._setup_ui(instructions)

    def _setup_ui(self, instructions: str | list[str]) -> None:
        """Set up the modal UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Scroll area for instructions
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Content widget
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(12)

        # Format instructions
        if isinstance(instructions, list):
            # Numbered list of steps
            for i, instruction in enumerate(instructions, 1):
                step_label = QLabel(f"<b>{i}.</b> {instruction}")
                step_label.setWordWrap(True)
                step_label.setFont(QFont("Arial", 12))
                content_layout.addWidget(step_label)
        else:
            # Single text block
            instruction_label = QLabel(instructions)
            instruction_label.setWordWrap(True)
            instruction_label.setFont(QFont("Arial", 12))
            instruction_label.setTextFormat(Qt.TextFormat.RichText)
            content_layout.addWidget(instruction_label)

        content_layout.addStretch()
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area, 1)

        # Close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        close_button = QPushButton("Got It!")
        close_button.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        close_button.setFixedHeight(40)
        close_button.setFixedWidth(120)
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #1976d2;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #1565c0;
            }
            QPushButton:pressed {
                background-color: #0d47a1;
            }
        """)
        close_button.clicked.connect(self.accept)

        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)


def show_instruction_modal(
    title: str,
    instructions: str | list[str],
    parent=None,
) -> None:
    """Show an instruction modal dialog.

    Args:
        title: Dialog title
        instructions: Either a single string or list of instruction steps
        parent: Parent widget
    """
    modal = InstructionModal(title, instructions, parent)
    modal.exec()
