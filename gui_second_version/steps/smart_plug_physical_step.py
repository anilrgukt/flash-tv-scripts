"""Smart plug physical setup step implementation using new framework patterns."""

from __future__ import annotations

from PyQt6.QtWidgets import QWidget

from core import WizardStep
from core.exceptions import handle_step_error, FlashTVError, ErrorType
from models import StepStatus
from utils.ui_factory import ButtonStyle


class SmartPlugPhysicalStep(WizardStep):
    """Step 4: Smart Plug Physical Setup using new framework patterns."""

    def create_content_widget(self) -> QWidget:
        """Create the smart plug physical setup UI using UI factory."""
        content = QWidget()

        # Use UI factory for main layout
        main_layout = self.ui_factory.create_main_step_layout()
        content.setLayout(main_layout)

        # Create overview section
        overview_section = self._create_overview_section()
        main_layout.addWidget(overview_section)

        # Create setup steps in 2x2 grid
        steps_section = self._create_steps_section()
        main_layout.addLayout(steps_section, 1)

        # Create progress and continue section
        progress_section = self._create_progress_section()
        main_layout.addLayout(progress_section)

        return content

    def _create_overview_section(self) -> QWidget:
        """Create the instructions overview section using UI factory."""
        overview_group, overview_layout = self.ui_factory.create_group_box("Smart Plug Setup Overview")

        overview_text = self.ui_factory.create_label(
            "This step guides you through physically setting up the smart plug "
            "to monitor TV power usage. The smart plug will track when the TV "
            "is turned on or off. Follow each step carefully and check the box when completed."
        )
        overview_layout.addWidget(overview_text)

        return overview_group

    def _create_steps_section(self):
        """Create the setup steps in 2x2 grid layout (left-to-right, top-to-bottom) using UI factory."""
        # Create main vertical layout for rows
        steps_grid = self.ui_factory.create_vertical_layout(spacing=8)

        # Create top and bottom rows
        top_row = self._create_top_row()
        bottom_row = self._create_bottom_row()

        steps_grid.addLayout(top_row, 1)
        steps_grid.addLayout(bottom_row, 1)

        return steps_grid

    def _create_top_row(self):
        """Create the top row with steps 1 & 2."""
        top_row = self.ui_factory.create_horizontal_layout(spacing=12)

        # Step 1: Identify TV Power Cord
        step1_box, step1_layout = self.ui_factory.create_group_box("Step 1: Identify TV Power Cord")

        step1_text = self.ui_factory.create_label(
            "• Locate the TV power cord\n• Trace it from the TV to the wall outlet\n• Ensure you can safely access the outlet"
        )
        step1_layout.addWidget(step1_text)

        self.step1_check = self.ui_factory.create_checkbox("I have identified the TV power cord", callback=self._update_progress)
        step1_layout.addWidget(self.step1_check)
        step1_layout.addStretch()

        # Step 2: Unplug TV
        step2_box, step2_layout = self.ui_factory.create_group_box("Step 2: Unplug TV from Wall")

        step2_text = self.ui_factory.create_label("• Unplug the TV power cord from the wall outlet\n• Keep the cord accessible for next step")
        step2_layout.addWidget(step2_text)

        self.step2_check = self.ui_factory.create_checkbox("TV is unplugged from wall outlet", callback=self._update_progress)
        step2_layout.addWidget(self.step2_check)
        step2_layout.addStretch()

        top_row.addWidget(step1_box, 1)
        top_row.addWidget(step2_box, 1)

        return top_row

    def _create_bottom_row(self):
        """Create the bottom row with steps 3 & 4."""
        bottom_row = self.ui_factory.create_horizontal_layout(spacing=12)

        # Step 3: Connect TV to Smart Plug
        step3_box, step3_layout = self.ui_factory.create_group_box("Step 3: Connect TV to Smart Plug")

        step3_text = self.ui_factory.create_label(
            "• Take the TV power cord (unplugged from wall)\n"
            "• Plug the TV power cord into the smart plug\n"
            "• Ensure connection is secure\n"
            "• Keep this assembly ready for next step"
        )
        step3_layout.addWidget(step3_text)

        self.step3_check = self.ui_factory.create_checkbox("✓ TV is connected to smart plug", callback=self._update_progress)
        step3_layout.addWidget(self.step3_check)
        step3_layout.addStretch()

        # Step 4: Insert Smart Plug Assembly
        step4_box, step4_layout = self.ui_factory.create_group_box("Step 4: Insert Smart Plug Assembly")

        step4_text = self.ui_factory.create_label(
            "• Take the smart plug with TV cord attached\n"
            "• Plug it into the wall outlet where TV was connected\n"
            "• Ensure it's fully inserted and small red LED light is on\n"
            "• TV should power on automatically or turn on TV using remote/button to test"
        )
        step4_layout.addWidget(step4_text)

        self.step4_check = self.ui_factory.create_checkbox(
            "Smart plug is inserted, red LED is on, and TV works",
            callback=self._update_progress,
        )
        step4_layout.addWidget(self.step4_check)
        step4_layout.addStretch()

        bottom_row.addWidget(step3_box, 1)
        bottom_row.addWidget(step4_box, 1)

        return bottom_row

    def _create_progress_section(self):
        """Create the progress and continue button section using UI factory."""
        bottom_layout = self.ui_factory.create_horizontal_layout()

        # Progress status
        self.progress_label = self.ui_factory.create_status_label("Complete all steps to continue", status_type="info")
        bottom_layout.addWidget(self.progress_label)

        bottom_layout.addStretch()

        # Continue button using UI factory
        self.continue_button = self.ui_factory.create_action_button(
            "Physical Setup Complete - Continue",
            callback=self._on_continue_clicked,
            style=ButtonStyle.SUCCESS,
            height=30,
            enabled=False,
        )
        bottom_layout.addWidget(self.continue_button)

        return bottom_layout

    @handle_step_error
    def _update_progress(self, state: int = 0) -> None:
        """Update progress based on checkbox states with enhanced tracking."""
        try:
            checks = [
                self.step1_check.isChecked(),
                self.step2_check.isChecked(),
                self.step3_check.isChecked(),
                self.step4_check.isChecked(),
            ]

            completed = sum(checks)
            total = len(checks)

            # Log progress changes
            self.logger.debug(f"Smart plug setup progress: {completed}/{total} steps completed")

            if completed == total:
                self.progress_label.setText("✅ All steps completed! Ready to continue.")
                self.progress_label.setStyleSheet(f"color: {self.config.success_color}; font-weight: bold; padding: 10px;")
                self.continue_button.setEnabled(True)

                # Save progress to state
                self.state.set_user_input(
                    "smart_plug_physical_progress",
                    {
                        "step1": checks[0],
                        "step2": checks[1],
                        "step3": checks[2],
                        "step4": checks[3],
                    },
                )

                # Persist state
                if self.state_manager:
                    self.state_manager.save_state(self.state)

                self.update_status(StepStatus.COMPLETED)
                self.logger.info("Smart plug physical setup completed")
            else:
                self.progress_label.setText(f"Progress: {completed}/{total} steps completed")
                self.progress_label.setStyleSheet(f"color: {self.config.info_color}; font-weight: bold; padding: 10px;")
                self.continue_button.setEnabled(False)
                self.update_status(StepStatus.USER_ACTION_REQUIRED)

        except Exception as e:
            self.logger.error(f"Error updating smart plug setup progress: {e}")
            raise FlashTVError(
                f"Failed to update setup progress: {e}",
                ErrorType.UI_ERROR,
                recovery_action="Try checking/unchecking the boxes again",
            )

    @handle_step_error
    def _on_continue_clicked(self, checked: bool = False) -> None:
        """Handle continue button click with comprehensive validation."""
        try:
            all_steps_complete = all(
                [
                    self.step1_check.isChecked(),
                    self.step2_check.isChecked(),
                    self.step3_check.isChecked(),
                    self.step4_check.isChecked(),
                ]
            )

            if all_steps_complete:
                self.logger.info("Smart plug physical setup completed successfully")

                # Save completion status
                self.state.set_user_input("smart_plug_configured", True)
                self.state.set_user_input("smart_plug_physical_complete", True)

                # Final state persistence
                if self.state_manager:
                    self.state_manager.save_state(self.state)

                self.request_next_step.emit()
            else:
                self.logger.warning("Continue clicked but not all steps are completed")
                # This shouldn't happen since button is disabled, but handle gracefully
                self._update_progress()

        except Exception as e:
            self.logger.error(f"Error during continue action: {e}")
            raise FlashTVError(
                f"Failed to complete smart plug setup: {e}",
                ErrorType.PROCESS_ERROR,
                recovery_action="Ensure all steps are checked and try again",
            )

    @handle_step_error
    def activate_step(self) -> None:
        """Activate the smart plug physical setup step with state restoration."""
        super().activate_step()

        self.logger.info("Smart plug physical setup step activated")

        # Restore previous progress if available
        self._restore_previous_progress()

        # Update progress display
        self._update_progress()

    def _restore_previous_progress(self) -> None:
        """Restore previously saved checkbox states."""
        try:
            progress = self.state.get_user_input("smart_plug_physical_progress", {})

            if progress:
                self.step1_check.setChecked(progress.get("step1", False))
                self.step2_check.setChecked(progress.get("step2", False))
                self.step3_check.setChecked(progress.get("step3", False))
                self.step4_check.setChecked(progress.get("step4", False))

                self.logger.info("Restored previous smart plug setup progress")

        except Exception as e:
            self.logger.error(f"Error restoring progress: {e}")

    def _cleanup_step_resources(self) -> None:
        """Clean up step-specific resources."""
        try:
            # Final state save before cleanup
            if self.state_manager:
                current_progress = {
                    "step1": self.step1_check.isChecked(),
                    "step2": self.step2_check.isChecked(),
                    "step3": self.step3_check.isChecked(),
                    "step4": self.step4_check.isChecked(),
                }
                self.state.set_user_input("smart_plug_physical_progress", current_progress)
                self.state_manager.save_state(self.state)

            self.logger.info("Smart plug physical setup step cleanup completed")

        except Exception as e:
            self.logger.error(f"Error during step cleanup: {e}")
