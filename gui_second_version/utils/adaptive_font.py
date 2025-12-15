"""Adaptive font sizing for dynamic content scaling."""

from __future__ import annotations

from typing import TYPE_CHECKING

from config.ui_config import UI_CONFIG
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QFont, QFontMetrics
from PyQt6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QLabel,
    QPushButton,
    QTextEdit,
    QWidget,
)

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout


class AdaptiveFontScaler:
    """Handles adaptive font scaling for wizard steps."""

    def __init__(self):
        self.enabled = UI_CONFIG.ADAPTIVE_FONT_ENABLED

    def apply_adaptive_scaling(
        self,
        container: QWidget,
        delay_ms: int = 100,
    ) -> None:
        """Apply adaptive font scaling to a container after layout is complete.

        Args:
            container: The container widget to scale fonts within
            delay_ms: Delay before applying scaling to allow layout to settle
        """
        if not self.enabled:
            return

        # Use QTimer to defer scaling until after the layout is fully rendered
        QTimer.singleShot(delay_ms, lambda: self._scale_container_fonts(container))

    def _scale_container_fonts(self, container: QWidget) -> None:
        """Scale fonts within a container based on available space."""
        if not container.isVisible():
            return

        container_height = container.height()
        if container_height <= 0:
            return

        # Calculate current content height
        content_height = self._calculate_content_height(container)

        if content_height <= 0:
            return

        # Calculate current density
        current_density = content_height / container_height

        # If we have too much whitespace, try to increase font sizes
        if current_density < UI_CONFIG.TARGET_CONTENT_DENSITY:
            self._increase_fonts(container, current_density, container_height)

    def _calculate_content_height(self, widget: QWidget) -> int:
        """Recursively calculate the total content height of a widget."""
        total_height = 0

        # Check if widget has a layout
        layout = widget.layout()
        if layout:
            for i in range(layout.count()):
                item = layout.itemAt(i)
                if item.widget():
                    child_widget = item.widget()
                    # Get the size hint or actual height
                    height = child_widget.sizeHint().height()
                    if height <= 0:
                        height = child_widget.height()
                    total_height += height
                elif item.layout():
                    # Recursively handle nested layouts
                    nested_widget = QWidget()
                    nested_widget.setLayout(item.layout())
                    total_height += self._calculate_content_height(nested_widget)

            # Add spacing
            spacing = layout.spacing()
            if spacing > 0:
                total_height += spacing * (layout.count() - 1)

        return total_height

    def _increase_fonts(
        self,
        container: QWidget,
        current_density: float,
        container_height: int,
    ) -> None:
        """Incrementally increase font sizes until target density is reached."""
        # Collect all scalable widgets
        widgets = self._get_scalable_widgets(container)

        if not widgets:
            return

        # Try increasing font sizes incrementally
        for font_increase in range(
            UI_CONFIG.FONT_SCALE_STEP,
            UI_CONFIG.MAX_FONT_SIZE,
            UI_CONFIG.FONT_SCALE_STEP,
        ):
            # Apply font increase to all widgets
            for widget in widgets:
                current_font = widget.font()
                base_size = current_font.pointSize()

                # Don't exceed max font size
                new_size = min(base_size + font_increase, UI_CONFIG.MAX_FONT_SIZE)

                # Don't go below min font size
                if new_size < UI_CONFIG.MIN_FONT_SIZE:
                    continue

                new_font = QFont(current_font)
                new_font.setPointSize(new_size)
                widget.setFont(new_font)

            # Force layout update
            container.updateGeometry()
            container.update()

            # Recalculate content height with new fonts
            new_content_height = self._calculate_content_height(container)
            new_density = new_content_height / container_height

            # If we've exceeded target density, revert last change and stop
            if new_density > UI_CONFIG.TARGET_CONTENT_DENSITY:
                # Revert to previous font size
                prev_increase = font_increase - UI_CONFIG.FONT_SCALE_STEP
                for widget in widgets:
                    current_font = widget.font()
                    base_size = current_font.pointSize() - UI_CONFIG.FONT_SCALE_STEP
                    reverted_size = max(base_size, UI_CONFIG.MIN_FONT_SIZE)

                    new_font = QFont(current_font)
                    new_font.setPointSize(reverted_size)
                    widget.setFont(new_font)

                container.updateGeometry()
                container.update()
                break

            # If we've reached max font size, stop
            if new_size >= UI_CONFIG.MAX_FONT_SIZE:
                break

    def _get_scalable_widgets(self, container: QWidget) -> list[QWidget]:
        """Get all widgets that support font scaling."""
        scalable_types = (QLabel, QTextEdit, QGroupBox, QPushButton, QCheckBox)
        widgets = []

        def collect_widgets(widget: QWidget):
            if isinstance(widget, scalable_types):
                widgets.append(widget)

            # Recursively check children
            for child in widget.findChildren(QWidget):
                if isinstance(child, scalable_types) and child not in widgets:
                    widgets.append(child)

        collect_widgets(container)
        return widgets


# Global singleton instance
_adaptive_scaler = None


def get_adaptive_scaler() -> AdaptiveFontScaler:
    """Get the global adaptive font scaler instance."""
    global _adaptive_scaler
    if _adaptive_scaler is None:
        _adaptive_scaler = AdaptiveFontScaler()
    return _adaptive_scaler
