"""Gallery creation step implementation using new framework patterns."""

from __future__ import annotations

import os
from pathlib import Path

from PyQt6.QtWidgets import QWidget, QProgressBar, QFileDialog

from core import WizardStep
from core.exceptions import handle_step_error, FlashTVError, ErrorType
from models import StepStatus, ProcessStatus
from constants import UI, Messages, Gallery
from utils.ui_factory import ButtonStyle


class GalleryCreationStep(WizardStep):
    """Step 4: Face Gallery Creation using new framework patterns."""

    def create_content_widget(self) -> QWidget:
        """Create the gallery creation UI using UI factory."""
        content = QWidget()

        # Use UI factory for main layout
        main_layout = self.ui_factory.create_main_step_layout()
        content.setLayout(main_layout)

        # Create sections using UI factory
        setup_section = self._create_setup_section()
        creation_section = self._create_creation_section()
        validation_section = self._create_validation_section()

        main_layout.addWidget(setup_section)
        main_layout.addWidget(creation_section)
        main_layout.addWidget(validation_section)

        # Continue button using UI factory
        continue_section = self._create_continue_section()
        main_layout.addLayout(continue_section)

        # Load existing gallery path if available
        self._load_existing_gallery_path()

        return content

    def _create_setup_section(self) -> QWidget:
        """Create the gallery setup section using UI factory."""
        setup_group, setup_layout = self.ui_factory.create_group_box(
            UI.FACE_GALLERY_SETUP
        )

        # Instructions
        instructions = self.ui_factory.create_label(
            "The face gallery will be automatically created with reference images for family members. "
            "The gallery location will be determined from your participant ID and data path."
        )
        setup_layout.addWidget(instructions)

        # Gallery path display (read-only)
        path_layout = self.ui_factory.create_horizontal_layout()

        path_label = self.ui_factory.create_label("Gallery Location:")
        path_label.setMinimumWidth(120)
        path_layout.addWidget(path_label)

        self.gallery_path_input = self.ui_factory.create_label(
            "Will be auto-generated from participant info"
        )
        self.gallery_path_input.setStyleSheet(
            "border: 1px solid #ccc; padding: 5px; background: #f5f5f5; color: #666;"
        )
        path_layout.addWidget(self.gallery_path_input, 1)

        setup_layout.addLayout(path_layout)

        return setup_group

    def _create_creation_section(self) -> QWidget:
        """Create the gallery creation section using UI factory."""
        creation_group, creation_layout = self.ui_factory.create_group_box(
            UI.CREATE_NEW_GALLERY
        )

        # Create gallery button
        self.create_gallery_button = self.ui_factory.create_action_button(
            "🎥 Create Gallery from Camera Captures (Manual)",
            callback=self._create_gallery,
            style=ButtonStyle.PRIMARY,
            height=35,
        )
        creation_layout.addWidget(self.create_gallery_button)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFormat("Gallery creation in progress... %p%")
        creation_layout.addWidget(self.progress_bar)

        # Gallery creation output
        creation_progress_label = self.ui_factory.create_label(
            "📋 Gallery Creation Instructions:"
        )
        creation_layout.addWidget(creation_progress_label)

        self.gallery_output = self.ui_factory.create_text_area(
            placeholder="📝 Automated gallery creation progress will appear here...",
            max_height=200,
            read_only=True,
        )
        creation_layout.addWidget(self.gallery_output)

        return creation_group

    def _create_validation_section(self) -> QWidget:
        """Create the validation section using UI factory."""
        validation_group, validation_layout = self.ui_factory.create_group_box(
            UI.GALLERY_VALIDATION
        )

        self.validate_button = self.ui_factory.create_action_button(
            "🔍 Validate Gallery Structure",
            callback=self._validate_gallery,
            style=ButtonStyle.SUCCESS,
            height=35,
            enabled=False,
        )
        validation_layout.addWidget(self.validate_button)

        validation_results_label = self.ui_factory.create_label(
            "📊 Gallery Validation Results:"
        )
        validation_layout.addWidget(validation_results_label)

        self.validation_output = self.ui_factory.create_text_area(
            placeholder="✅ Gallery validation results will appear here...",
            max_height=150,
            read_only=True,
        )
        validation_layout.addWidget(self.validation_output)

        return validation_group

    def _create_continue_section(self):
        """Create the continue button section using UI factory."""
        button_layout, self.continue_button = self.ui_factory.create_continue_button(
            callback=self._on_continue_clicked, text=UI.CONTINUE_TO_NEXT_STEP
        )

        return button_layout

    @handle_step_error
    def _load_existing_gallery_path(self) -> None:
        """Auto-generate and load gallery path from participant info with logging."""
        try:
            participant_id = self.state.get_user_input("participant_id", "")
            device_id = self.state.get_user_input("device_id", "")
            data_path = self.state.get_user_input("data_path", "")
            
            if participant_id and data_path:
                # Include device_id in gallery path to match data path format
                if device_id:
                    gallery_path = str(Path(data_path) / f"{participant_id}{device_id}_faces")
                else:
                    gallery_path = str(Path(data_path) / f"{participant_id}_faces")
                self.gallery_path_input.setText(gallery_path)
                self.state.set_user_input("gallery_path", gallery_path)
                self.logger.info(f"Auto-generated gallery path: {gallery_path}")
                
                # Check if gallery already exists and is validated
                if Path(gallery_path).exists():
                    self.validate_button.setEnabled(True)
            else:
                self.gallery_path_input.setText("Participant info needed for auto-generation")
                self.logger.debug("Participant info not available for gallery path generation")

        except Exception as e:
            self.logger.error(f"Error auto-generating gallery path: {e}")
            raise FlashTVError(
                f"Failed to generate gallery path: {e}",
                ErrorType.VALIDATION_ERROR,
                recovery_action="Check participant setup completion",
            )


    @handle_step_error
    def _create_gallery(self, checked: bool = False) -> None:
        """Create a new face gallery using the gallery creation script with comprehensive error handling."""
        try:
            participant_id = self.state.get_user_input("participant_id", "")
            device_id = self.state.get_user_input("device_id", "")
            data_path = self.state.get_user_input("data_path", "")
            username = self.state.get_user_input("username", "")

            if not all([participant_id, data_path, username]):
                self.logger.error("Missing required information for gallery creation")
                self.gallery_output.append(Messages.ERROR_MISSING_GALLERY_INFO)
                raise FlashTVError(
                    "Missing participant ID, data path, or username",
                    ErrorType.VALIDATION_ERROR,
                    recovery_action="Complete participant setup first",
                )

            self.logger.info(
                f"Starting gallery creation for participant: {participant_id}"
            )
            self.update_status(StepStatus.AUTOMATION_RUNNING)
            self.create_gallery_button.setEnabled(False)
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # Indeterminate progress

            # Construct gallery path with device_id
            if device_id:
                gallery_path = str(Path(data_path) / f"{participant_id}{device_id}_faces")
            else:
                gallery_path = str(Path(data_path) / f"{participant_id}_faces")
            self.gallery_path_input.setText(gallery_path)
            self.state.set_user_input("gallery_path", gallery_path)

            # Persist state
            if self.state_manager:
                self.state_manager.save_state(self.state)

            self.gallery_output.clear()
            self.gallery_output.append(
                Messages.CREATING_GALLERY_FOR_PARTICIPANT.format(
                    participant_id=participant_id
                )
            )
            self.gallery_output.append(
                Messages.GALLERY_LOCATION.format(path=gallery_path)
            )

            # Run gallery creation script with command-line arguments
            script_path = os.path.expanduser("~/flash-tv-scripts/runtime_scripts/build_gallery.sh")
            
            self.gallery_output.append(f"📋 Starting gallery creation...")
            self.gallery_output.append(f"👤 Participant: {participant_id}")
            self.gallery_output.append(f"💾 Data path: {data_path}")
            
            # Pass arguments directly to the script
            command = [
                "bash", 
                script_path,
                participant_id,
                username,
                data_path
            ]
            
            process_info = self.process_runner.run_script(
                command=command,
                description=f"Creating face gallery for {participant_id}",
                working_dir=os.path.expanduser("~/flash-tv-scripts/runtime_scripts"),
                process_name="gallery_creation",
            )

            if process_info:
                self.gallery_output.append("🚀 Gallery creation script launched!")
                self.gallery_output.append("✋ Please follow the manual steps in the terminal window")
                self.gallery_output.append("📸 You will be guided to capture face images for each family member")
                self.gallery_output.append("👥 Capture 5 images each for: parent1, parent2, sib1, sib2, tc1")
                self.gallery_output.append("ℹ️ The script will open camera windows for you to capture images")
                self.logger.info("Gallery creation script started successfully")
                # Monitor process completion in update_ui
            else:
                self.logger.error("Failed to start gallery creation script")
                self.gallery_output.append("❌ Failed to start gallery creation process")
                self.gallery_output.append("💡 Please check script permissions and try again")
                self.update_status(StepStatus.FAILED)
                self._reset_gallery_creation_ui()
                raise FlashTVError(
                    "Failed to start gallery creation script",
                    ErrorType.PROCESS_ERROR,
                    recovery_action="Check script permissions and try again",
                )

        except Exception as e:
            self.logger.error(f"Error during gallery creation: {e}")
            self.update_status(StepStatus.FAILED)
            self._reset_gallery_creation_ui()
            raise

    @handle_step_error
    def _validate_gallery(self, checked: bool = False) -> None:
        """Validate the gallery structure and contents with comprehensive error handling."""
        try:
            gallery_path = self.state.get_user_input("gallery_path", "")
            if not gallery_path:
                self.logger.warning("No gallery path available for validation")
                return

            self.logger.info(f"Validating gallery at path: {gallery_path}")
            self.validate_button.setEnabled(False)
            self.validation_output.clear()
            self.validation_output.append(
                f"🔍 Validating gallery structure at: {gallery_path}"
            )

            gallery_dir = Path(gallery_path)

            if not gallery_dir.exists():
                self.logger.error(f"Gallery directory does not exist: {gallery_path}")
                self.validation_output.append("❌ Gallery directory does not exist")
                self.validation_output.append("💡 Please create the gallery first using the button above")
                self.validate_button.setEnabled(True)
                raise FlashTVError(
                    f"Gallery directory does not exist: {gallery_path}",
                    ErrorType.SYSTEM_ERROR,
                    recovery_action="Create the gallery first",
                )

            # Check for required face categories
            participant_id = self.state.get_user_input("participant_id", "")
            required_faces = Gallery.ROLES

            validation_passed = True
            total_images = 0

            for face_type in required_faces:
                # Look for files matching pattern: {participant_id}_{face_type}*.png
                face_files = list(
                    gallery_dir.glob(f"{participant_id}_{face_type}*.png")
                )

                if face_files:
                    count = len(face_files)
                    total_images += count
                    self.validation_output.append(
                        f"✅ Found {count} images for {face_type}"
                    )
                    self.logger.debug(f"Found {count} images for {face_type}")
                else:
                    self.validation_output.append(
                        f"❌ Missing images for {face_type}"
                    )
                    self.logger.warning(f"Missing images for face type: {face_type}")
                    validation_passed = False

            if validation_passed:
                self.logger.info(
                    f"Gallery validation successful - {total_images} total images"
                )
                self.validation_output.append(f"\n🎉 Gallery validation successful!")
                self.validation_output.append(f"📊 Total images found: {total_images}")
                self.validation_output.append("✨ Your face gallery is ready for use!")

                # Save validation status
                self.state.set_user_input("gallery_validated", True)
                self.state.set_user_input("gallery_total_images", total_images)

                # Persist state
                if self.state_manager:
                    self.state_manager.save_state(self.state)

                self.update_status(StepStatus.COMPLETED)
                self.continue_button.setEnabled(True)
            else:
                self.logger.warning(
                    "Gallery validation failed - missing required images"
                )
                self.validation_output.append(f"\n❌ Gallery validation failed - missing required face images")
                self.validation_output.append("💡 Please create the gallery or add missing images")
                self.update_status(StepStatus.USER_ACTION_REQUIRED)

        except Exception as e:
            self.logger.error(f"Error during gallery validation: {e}")
            self.update_status(StepStatus.FAILED)
            raise
        finally:
            self.validate_button.setEnabled(True)

    @handle_step_error
    def _on_continue_clicked(self, checked: bool = False) -> None:
        """Handle continue button click with validation."""
        try:
            if self.is_completed() and self.continue_button.isEnabled():
                gallery_path = self.state.get_user_input("gallery_path", "")
                total_images = self.state.get_user_input("gallery_total_images", 0)

                self.logger.info(
                    f"Gallery creation completed with {total_images} images at: {gallery_path}"
                )

                # Final state persistence
                if self.state_manager:
                    self.state_manager.save_state(self.state)

                self.request_next_step.emit()
            else:
                self.logger.warning("Continue clicked but gallery not validated")

        except Exception as e:
            self.logger.error(f"Error during continue action: {e}")
            raise FlashTVError(
                f"Failed to complete gallery step: {e}",
                ErrorType.PROCESS_ERROR,
                recovery_action="Validate the gallery first",
            )

    def _reset_gallery_creation_ui(self) -> None:
        """Reset the gallery creation UI after process completion with logging."""
        try:
            self.create_gallery_button.setEnabled(True)
            self.progress_bar.setVisible(False)
            self.validate_button.setEnabled(True)
            self.logger.debug("Reset gallery creation UI")

        except Exception as e:
            self.logger.error(f"Error resetting gallery UI: {e}")

    @handle_step_error
    def activate_step(self) -> None:
        """Activate the gallery creation step with state restoration."""
        super().activate_step()

        self.logger.info("Gallery creation step activated")
        
        # Auto-generate gallery path from participant info
        self._load_existing_gallery_path()

        # Check if already validated
        if self.state.get_user_input("gallery_validated", False):
            gallery_path = self.state.get_user_input("gallery_path", "")
            total_images = self.state.get_user_input("gallery_total_images", 0)
            if gallery_path:
                self.validation_output.append(
                    f"✅ Gallery already validated: {total_images} images at {gallery_path}"
                )
                self.continue_button.setEnabled(True)
                self.update_status(StepStatus.COMPLETED)
                self.logger.info("Gallery already validated, skipping")
                return

        # Check if gallery path is already set and validate it
        gallery_path = self.state.get_user_input("gallery_path", "")
        if gallery_path and Path(gallery_path).exists():
            self.gallery_output.append(f"📁 Found existing gallery at: {gallery_path}")
            self.gallery_output.append("🔍 Validating existing gallery...")
            self._validate_gallery()
        else:
            self.gallery_output.append("📋 Ready to create new face gallery")
            self.gallery_output.append("👆 Click 'Create Gallery from Camera Captures' to begin automated setup")

    def update_ui(self) -> None:
        """Update UI elements periodically with framework integration."""
        super().update_ui()

        # Check gallery creation process status
        process_info = self.state.get_process("gallery_creation")
        if process_info:
            if not process_info.is_running():
                status = process_info.get_status()
                if status == ProcessStatus.COMPLETED:
                    self.logger.info("Gallery creation script completed")
                    self.gallery_output.append("\n✅ Gallery creation completed successfully!")
                    self.gallery_output.append("🔍 Starting automatic validation...")
                    self.update_status(StepStatus.USER_ACTION_REQUIRED)
                    self._validate_gallery()  # Auto-validate after creation
                elif status == ProcessStatus.FAILED:
                    self.logger.error(f"Gallery creation failed")
                    self.gallery_output.append(f"\n❌ Gallery creation failed")
                    
                    # Get and show error output
                    stdout_lines, stderr_lines = process_info.get_output()
                    if stderr_lines:
                        self.gallery_output.append("\nError output:")
                        for line in stderr_lines[-10:]:  # Show last 10 lines
                            self.gallery_output.append(f"  {line}")
                            self.logger.error(f"Gallery stderr: {line}")
                    
                    if stdout_lines:
                        self.gallery_output.append("\nLast output:")
                        for line in stdout_lines[-5:]:  # Show last 5 lines
                            self.gallery_output.append(f"  {line}")
                    
                    self.gallery_output.append("💡 Please check the error messages above and try again")
                    self.update_status(StepStatus.FAILED)
                elif status == ProcessStatus.TERMINATED:
                    self.logger.warning("Gallery creation was terminated")
                    self.gallery_output.append("\n⚠️ Gallery creation was terminated")
                    
                    # Get and show any output before termination
                    stdout_lines, stderr_lines = process_info.get_output()
                    if stderr_lines:
                        self.gallery_output.append("\nError output before termination:")
                        for line in stderr_lines[-5:]:  
                            self.gallery_output.append(f"  {line}")
                    
                    self.gallery_output.append("💡 You can restart the process if needed")
                    self.update_status(StepStatus.FAILED)
                else:
                    self.logger.error(f"Gallery creation finished with unexpected status")
                    self.gallery_output.append(f"\n⚠️ Gallery creation finished with unexpected status")
                    self.update_status(StepStatus.FAILED)

                self._reset_gallery_creation_ui()
                # Remove completed process
                self.state.remove_process("gallery_creation")

    def _cleanup_step_resources(self) -> None:
        """Clean up step-specific resources."""
        try:
            # Final state save before cleanup
            if self.state_manager:
                self.state_manager.save_state(self.state)

            self.logger.info("Gallery creation step cleanup completed")

        except Exception as e:
            self.logger.error(f"Error during step cleanup: {e}")
