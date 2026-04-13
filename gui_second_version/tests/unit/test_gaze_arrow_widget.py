"""Unit tests for GazeArrowWidget."""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from widgets import GazeArrowWidget


class TestGazeArrowWidgetInitialization:
    """Tests for GazeArrowWidget initialization."""

    def test_default_initialization(self, qtbot):
        """Test widget initializes with default values."""
        widget = GazeArrowWidget()
        qtbot.addWidget(widget)

        assert widget.pitch_deg == 0.0
        assert widget.yaw_deg == 0.0
        assert widget.watching_tv is False
        assert widget.has_data is False
        assert widget.timestamp == ""
        assert widget.status_text == ""

    def test_widget_size_constraints(self, qtbot):
        """Test widget has proper size constraints."""
        widget = GazeArrowWidget()
        qtbot.addWidget(widget)

        min_size = widget.minimumSize()
        max_size = widget.maximumSize()

        assert min_size.width() == 150
        assert min_size.height() == 200
        assert max_size.width() == 220
        assert max_size.height() == 280

    def test_initialization_with_parent(self, qtbot):
        """Test widget initializes with parent."""
        parent = QWidget()
        qtbot.addWidget(parent)

        widget = GazeArrowWidget(parent)
        assert widget.parent() == parent


class TestSetGaze:
    """Tests for set_gaze method."""

    def test_set_gaze_updates_values(self, qtbot):
        """Test set_gaze updates all values."""
        widget = GazeArrowWidget()
        qtbot.addWidget(widget)

        widget.set_gaze(
            pitch_deg=10.0,
            yaw_deg=-5.0,
            watching_tv=True,
            timestamp="12:00:00.000",
            status="WATCHING TV",
        )

        assert widget.pitch_deg == 10.0
        assert widget.yaw_deg == -5.0
        assert widget.watching_tv is True
        assert widget.has_data is True
        assert widget.timestamp == "12:00:00.000"
        assert widget.status_text == "WATCHING TV"

    def test_set_gaze_with_minimal_args(self, qtbot):
        """Test set_gaze with only required arguments."""
        widget = GazeArrowWidget()
        qtbot.addWidget(widget)

        widget.set_gaze(pitch_deg=5.0, yaw_deg=5.0, watching_tv=False)

        assert widget.pitch_deg == 5.0
        assert widget.yaw_deg == 5.0
        assert widget.watching_tv is False
        assert widget.has_data is True

    def test_set_gaze_triggers_update(self, qtbot):
        """Test set_gaze triggers repaint."""
        widget = GazeArrowWidget()
        qtbot.addWidget(widget)
        widget.show()

        # This should not raise
        widget.set_gaze(10.0, 10.0, True)
        qtbot.wait(10)  # Allow repaint to occur

    def test_set_gaze_negative_angles(self, qtbot):
        """Test set_gaze with negative angles."""
        widget = GazeArrowWidget()
        qtbot.addWidget(widget)

        widget.set_gaze(-15.0, -20.0, False)

        assert widget.pitch_deg == -15.0
        assert widget.yaw_deg == -20.0

    def test_set_gaze_large_angles(self, qtbot):
        """Test set_gaze with large angles."""
        widget = GazeArrowWidget()
        qtbot.addWidget(widget)

        widget.set_gaze(90.0, 90.0, False)

        assert widget.pitch_deg == 90.0
        assert widget.yaw_deg == 90.0


class TestClearGaze:
    """Tests for clear_gaze method."""

    def test_clear_gaze_resets_has_data(self, qtbot):
        """Test clear_gaze resets has_data flag."""
        widget = GazeArrowWidget()
        qtbot.addWidget(widget)

        widget.set_gaze(10.0, 10.0, True)
        assert widget.has_data is True

        widget.clear_gaze()
        assert widget.has_data is False

    def test_clear_gaze_clears_text(self, qtbot):
        """Test clear_gaze clears timestamp and status."""
        widget = GazeArrowWidget()
        qtbot.addWidget(widget)

        widget.set_gaze(10.0, 10.0, True, "12:00:00", "WATCHING")
        widget.clear_gaze()

        assert widget.timestamp == ""
        assert widget.status_text == ""

    def test_clear_gaze_triggers_update(self, qtbot):
        """Test clear_gaze triggers repaint."""
        widget = GazeArrowWidget()
        qtbot.addWidget(widget)
        widget.show()

        widget.set_gaze(10.0, 10.0, True)
        widget.clear_gaze()
        qtbot.wait(10)  # Allow repaint


class TestPaintEvent:
    """Tests for paint event handling."""

    def test_paint_without_data(self, qtbot):
        """Test painting when no data is set."""
        widget = GazeArrowWidget()
        qtbot.addWidget(widget)
        widget.show()

        # Should paint "No Data" without errors
        widget.repaint()
        qtbot.wait(10)

    def test_paint_with_watching_tv(self, qtbot):
        """Test painting when watching TV (green arrow)."""
        widget = GazeArrowWidget()
        qtbot.addWidget(widget)
        widget.show()

        widget.set_gaze(5.0, 5.0, True, "12:00:00", "WATCHING TV")
        widget.repaint()
        qtbot.wait(10)

    def test_paint_with_looking_away(self, qtbot):
        """Test painting when looking away (blue arrow)."""
        widget = GazeArrowWidget()
        qtbot.addWidget(widget)
        widget.show()

        widget.set_gaze(30.0, 30.0, False, "12:00:00", "LOOKING AWAY")
        widget.repaint()
        qtbot.wait(10)

    def test_paint_with_zero_angles(self, qtbot):
        """Test painting with zero angles (center arrow)."""
        widget = GazeArrowWidget()
        qtbot.addWidget(widget)
        widget.show()

        widget.set_gaze(0.0, 0.0, True)
        widget.repaint()
        qtbot.wait(10)

    def test_paint_at_different_sizes(self, qtbot):
        """Test painting at various widget sizes."""
        widget = GazeArrowWidget()
        qtbot.addWidget(widget)
        widget.show()

        widget.set_gaze(10.0, -10.0, True)

        # Test minimum size
        widget.resize(200, 280)
        widget.repaint()
        qtbot.wait(10)

        # Test maximum size
        widget.resize(250, 320)
        widget.repaint()
        qtbot.wait(10)


class TestStatusTextColors:
    """Tests for status text color coding."""

    def test_watching_tv_status(self, qtbot):
        """Test status containing WATCHING TV."""
        widget = GazeArrowWidget()
        qtbot.addWidget(widget)
        widget.show()

        widget.set_gaze(5.0, 5.0, True, status="WATCHING TV")
        widget.repaint()
        qtbot.wait(10)
        # Visual inspection would show green text

    def test_looking_away_status(self, qtbot):
        """Test status containing LOOKING AWAY."""
        widget = GazeArrowWidget()
        qtbot.addWidget(widget)
        widget.show()

        widget.set_gaze(30.0, 30.0, False, status="LOOKING AWAY")
        widget.repaint()
        qtbot.wait(10)
        # Visual inspection would show blue text


class TestArrowCalculation:
    """Tests for arrow direction calculation."""

    def test_arrow_direction_changes_with_angles(self, qtbot):
        """Test arrow direction responds to angle changes."""
        widget = GazeArrowWidget()
        qtbot.addWidget(widget)
        widget.show()

        # Various angle combinations
        test_cases = [
            (0.0, 0.0),  # Center
            (45.0, 0.0),  # Right
            (-45.0, 0.0),  # Left
            (0.0, 45.0),  # Up
            (0.0, -45.0),  # Down
            (30.0, 30.0),  # Upper right
            (-30.0, -30.0),  # Lower left
        ]

        for pitch, yaw in test_cases:
            widget.set_gaze(pitch, yaw, True)
            widget.repaint()
            qtbot.wait(5)


class TestWidgetVisibility:
    """Tests for widget visibility states."""

    def test_hidden_widget(self, qtbot):
        """Test widget behavior when hidden."""
        widget = GazeArrowWidget()
        qtbot.addWidget(widget)

        widget.set_gaze(10.0, 10.0, True)
        # Should not raise when hidden

    def test_show_hide_cycle(self, qtbot):
        """Test widget through show/hide cycle."""
        widget = GazeArrowWidget()
        qtbot.addWidget(widget)

        widget.show()
        widget.set_gaze(10.0, 10.0, True)
        qtbot.wait(10)

        widget.hide()
        widget.set_gaze(20.0, 20.0, False)

        widget.show()
        qtbot.wait(10)


class TestMultipleWidgets:
    """Tests for multiple widget instances."""

    def test_independent_instances(self, qtbot):
        """Test multiple widgets are independent."""
        widget1 = GazeArrowWidget()
        widget2 = GazeArrowWidget()
        qtbot.addWidget(widget1)
        qtbot.addWidget(widget2)

        widget1.set_gaze(10.0, 10.0, True)
        widget2.set_gaze(-10.0, -10.0, False)

        assert widget1.pitch_deg == 10.0
        assert widget2.pitch_deg == -10.0
        assert widget1.watching_tv is True
        assert widget2.watching_tv is False

    def test_clear_one_widget(self, qtbot):
        """Test clearing one widget doesn't affect others."""
        widget1 = GazeArrowWidget()
        widget2 = GazeArrowWidget()
        qtbot.addWidget(widget1)
        qtbot.addWidget(widget2)

        widget1.set_gaze(10.0, 10.0, True)
        widget2.set_gaze(20.0, 20.0, True)

        widget1.clear_gaze()

        assert widget1.has_data is False
        assert widget2.has_data is True


class TestEdgeCases:
    """Tests for edge cases."""

    def test_very_large_angles(self, qtbot):
        """Test with very large angle values."""
        widget = GazeArrowWidget()
        qtbot.addWidget(widget)
        widget.show()

        widget.set_gaze(180.0, 180.0, False)
        widget.repaint()
        qtbot.wait(10)

    def test_special_characters_in_status(self, qtbot):
        """Test status text with special characters."""
        widget = GazeArrowWidget()
        qtbot.addWidget(widget)
        widget.show()

        widget.set_gaze(10.0, 10.0, True, status="Status with emoji 👀 and symbols <>&")
        widget.repaint()
        qtbot.wait(10)

    def test_rapid_updates(self, qtbot):
        """Test rapid gaze updates."""
        widget = GazeArrowWidget()
        qtbot.addWidget(widget)
        widget.show()

        for i in range(100):
            widget.set_gaze(float(i), float(i), i % 2 == 0)

        qtbot.wait(10)
        assert widget.pitch_deg == 99.0
