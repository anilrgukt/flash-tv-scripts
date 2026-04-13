"""Gallery creation step implementation using new framework patterns."""

from __future__ import annotations

import os
from pathlib import Path
import shutil

from config.messages import MESSAGES
from config.participant_contract import build_participant_full_id, get_gallery_dir
from core import WizardStep
from core.exceptions import ErrorType, FlashTVError, handle_step_error
from models import ProcessStatus, StepStatus
from models.state_keys import UserInputKey
from PySide6.QtWidgets import QProgressBar, QWidget
from utils.ui_factory import ButtonStyle


class GalleryCreationStep(WizardStep):
    """Step 7: Face Gallery Creation using new framework patterns."""

    def create_content_widget(self) -> QWidget:
        """Create the gallery creation UI using UI factory."""
        content = QWidget()

        # Use UI factory for main layout
        main_layout = self.ui_factory.create_main_step_layout()
        content.setLayout(main_layout)

        # Create sections in a two-column layout
        content_row = self.ui_factory.create_horizontal_layout(spacing=12)

        # Left column: Setup and shortcuts
        left_column = self.ui_factory.create_vertical_layout(spacing=8)

        setup_section = self._create_setup_section()
        left_column.addWidget(setup_section)

        shortcuts_section = self._create_shortcuts_section()
        left_column.addWidget(shortcuts_section)

        left_column.addStretch()  # Push content up

        content_row.addLayout(left_column, 1)

        # Right column: Status
        right_column = self.ui_factory.create_vertical_layout(spacing=8)

        verification_section = self._create_verification_section()
        right_column.addWidget(verification_section)

        status_section = self._create_status_section()
        right_column.addWidget(status_section, 1)

        content_row.addLayout(right_column, 1)

        main_layout.addLayout(content_row, 1)

        # Continue button using UI factory
        continue_section = self._create_continue_section()
        main_layout.addLayout(continue_section)

        # Load existing gallery path if available
        self._load_existing_gallery_path()

        return content

    def _create_setup_section(self) -> QWidget:
        """Create the gallery setup section using UI factory."""
        setup_group, setup_layout = self.ui_factory.create_group_box(
            "Face Gallery Setup"
        )

        # Instructions
        instructions = self.ui_factory.create_label(
            "Manually create a face gallery with reference images for family members. "
            "The gallery location is determined from your participant ID and data path."
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

    def _create_verification_section(self) -> QWidget:
        verification_group, verification_layout = self.ui_factory.create_group_box(
            "Gallery Verification",
            spacing=4,
            margins=(10, 10, 10, 10),
        )
        verification_group.setMinimumHeight(250)

        verification_layout.addWidget(
            self.ui_factory.create_label(
                "Select the family roles captured today. Unchecked roles will be filled automatically.",
                style="color: #333;",
            )
        )

        self.tc_checkbox = self.ui_factory.create_checkbox(
            "Target child captured",
            callback=self._on_gallery_verification_changed,
            checked=False,
        )
        self.sib_checkbox = self.ui_factory.create_checkbox(
            "Sibling captured",
            callback=self._on_gallery_verification_changed,
            checked=False,
        )
        self.parent_checkbox = self.ui_factory.create_checkbox(
            "Parent captured",
            callback=self._on_gallery_verification_changed,
            checked=False,
        )

        verification_layout.addWidget(self.tc_checkbox)
        verification_layout.addWidget(self.sib_checkbox)
        verification_layout.addWidget(self.parent_checkbox)

        verification_layout.addWidget(
            self.ui_factory.create_label(
                "Consent confirmation",
                style="font-weight: bold; margin-top: 6px; padding-top: 6px; border-top: 1px solid #d9d9d9;",
            )
        )

        self.consent_checkbox = self.ui_factory.create_checkbox(
            "Family consent for selected face photos confirmed",
            callback=self._on_gallery_verification_changed,
            checked=False,
        )
        verification_layout.addWidget(self.consent_checkbox)

        self.gallery_readiness_label = self.ui_factory.create_label(
            "Confirm consent and select at least one role to enable Create Gallery.",
            style="color: #666; padding-top: 4px;",
        )
        verification_layout.addWidget(self.gallery_readiness_label)
        verification_layout.addStretch()

        return verification_group

    def _create_status_section(self) -> QWidget:
        """Create the combined status section for gallery creation and validation."""
        status_group, status_layout = self.ui_factory.create_group_box(
            "Create Gallery and Validation"
        )

        status_layout.setSpacing(6)

        # Create gallery button
        self.create_gallery_button = self.ui_factory.create_action_button(
            "🎥 Create Gallery from Camera Captures (Manual)",
            callback=self._create_gallery,
            style=ButtonStyle.PRIMARY,
            height=40,
            enabled=False,
        )
        status_layout.addWidget(self.create_gallery_button)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Initializing... %p%")
        status_layout.addWidget(self.progress_bar)

        # Combined status output
        self.gallery_output = self.ui_factory.create_text_area(
            placeholder="Click 'Create Gallery' to begin. Status will appear here...",
            max_height=150,
            min_height=120,
            read_only=True,
        )
        status_layout.addWidget(self.gallery_output, 1)

        self._update_gallery_readiness()

        return status_group

    def _on_gallery_verification_changed(self) -> None:
        self._persist_gallery_verification_state()
        self._update_gallery_readiness()

    def _persist_gallery_verification_state(self) -> None:
        self.state.set_user_input(
            UserInputKey.GALLERY_ROLE_TC_SELECTED, self.tc_checkbox.isChecked()
        )
        self.state.set_user_input(
            UserInputKey.GALLERY_ROLE_SIB_SELECTED, self.sib_checkbox.isChecked()
        )
        self.state.set_user_input(
            UserInputKey.GALLERY_ROLE_PARENT_SELECTED, self.parent_checkbox.isChecked()
        )
        self.state.set_user_input(
            UserInputKey.GALLERY_CONSENT_CONFIRMED, self.consent_checkbox.isChecked()
        )

        if self.state_manager:
            self.state_manager.save_state(self.state)

    def _has_gallery_consent(self) -> bool:
        return self.consent_checkbox.isChecked()

    def _get_selected_family_roles(self) -> list[str]:
        selected_roles: list[str] = []

        if self.tc_checkbox.isChecked():
            selected_roles.append("tc")
        if self.sib_checkbox.isChecked():
            selected_roles.append("sib")
        if self.parent_checkbox.isChecked():
            selected_roles.append("parent")

        return selected_roles

    def _is_gallery_ready_to_create(self) -> bool:
        return self._has_gallery_consent() and bool(self._get_selected_family_roles())

    def _update_gallery_readiness(self) -> None:
        selected_count = len(self._get_selected_family_roles())
        ready_to_create = self._is_gallery_ready_to_create()
        process_info = self.state.get_process("gallery_creation")
        process_running = bool(process_info and process_info.is_running())

        self.create_gallery_button.setEnabled(ready_to_create and not process_running)

        if ready_to_create:
            self.gallery_readiness_label.setText(
                "Ready to create the gallery with the selected family roles."
            )
            self.gallery_readiness_label.setStyleSheet(
                "color: #2e7d32; font-weight: bold; padding-top: 4px;"
            )
        elif not self._has_gallery_consent() and selected_count == 0:
            self.gallery_readiness_label.setText(
                "To enable Create Gallery, confirm consent and check at least one family role."
            )
            self.gallery_readiness_label.setStyleSheet("color: #666; padding-top: 4px;")
        elif not self._has_gallery_consent():
            self.gallery_readiness_label.setText(
                "Consent still needs to be confirmed before gallery creation can start."
            )
            self.gallery_readiness_label.setStyleSheet(
                "color: #f57c00; font-weight: bold; padding-top: 4px;"
            )
        else:
            self.gallery_readiness_label.setText(
                "Check at least one family role before creating the gallery."
            )
            self.gallery_readiness_label.setStyleSheet(
                "color: #f57c00; font-weight: bold; padding-top: 4px;"
            )

    def _restore_gallery_verification_state(self) -> None:
        self.tc_checkbox.setChecked(
            self.state.get_user_input(UserInputKey.GALLERY_ROLE_TC_SELECTED, False)
        )
        self.sib_checkbox.setChecked(
            self.state.get_user_input(UserInputKey.GALLERY_ROLE_SIB_SELECTED, False)
        )
        self.parent_checkbox.setChecked(
            self.state.get_user_input(UserInputKey.GALLERY_ROLE_PARENT_SELECTED, False)
        )
        self.consent_checkbox.setChecked(
            self.state.get_user_input(UserInputKey.GALLERY_CONSENT_CONFIRMED, False)
        )
        self._update_gallery_readiness()

    def _create_shortcuts_section(self) -> QWidget:
        """Create the keyboard shortcuts reference section."""
        shortcuts_group, shortcuts_layout = self.ui_factory.create_group_box(
            "⌨️ Keyboard Shortcuts"
        )

        shortcuts_text = self.ui_factory.create_label(
            "<table cellspacing='8'>"
            "<tr><td>• <b>T</b> = Target child</td><td>• <b>1-5</b> = Capture face</td></tr>"
            "<tr><td>• <b>S</b> = Sibling</td><td>• <b>R</b> = Refresh</td></tr>"
            "<tr><td>• <b>P</b> = Parent</td><td>• <b>Q</b> = Quit</td></tr>"
            "<tr><td>• <b>E</b> = Extra person</td><td></td></tr>"
            "<tr><td>• <b>U</b> = Unselect</td><td></td></tr>"
            "</table>"
        )
        shortcuts_layout.addWidget(shortcuts_text)

        return shortcuts_group

    def _create_continue_section(self):
        """Create the continue button section using UI factory."""
        button_layout, self.continue_button = self.ui_factory.create_continue_button(
            callback=self._on_continue_clicked, text=MESSAGES.UI.CONTINUE
        )

        return button_layout

    @handle_step_error
    def _load_existing_gallery_path(self) -> None:
        """Auto-generate and load gallery path from participant info with logging."""
        try:
            participant_id = self.state.get_user_input(UserInputKey.PARTICIPANT_ID, "")
            device_id = self.state.get_user_input(UserInputKey.DEVICE_ID, "")
            data_path = self.state.get_user_input(UserInputKey.DATA_PATH, "")
            username = self.state.get_user_input(UserInputKey.USERNAME, "")

            if participant_id and data_path and username:
                gallery_path = str(get_gallery_dir(username, participant_id, device_id))
                self.gallery_path_input.setText(gallery_path)
                self.state.set_user_input(UserInputKey.GALLERY_PATH, gallery_path)
                self.logger.info(f"Auto-generated gallery path: {gallery_path}")
            else:
                self.gallery_path_input.setText(
                    "Participant info needed for auto-generation"
                )
                self.logger.debug(
                    "Participant info not available for gallery path generation"
                )

        except Exception as e:
            self.logger.error(f"Error auto-generating gallery path: {e}")
            raise FlashTVError(
                f"Failed to generate gallery path: {e}",
                ErrorType.VALIDATION_ERROR,
                recovery_action="Check participant setup completion",
            )

    @handle_step_error
    def _create_gallery(self, checked: bool = False) -> None:
        """Create a new face gallery using the gallery creation script."""
        try:
            participant_id = self.state.get_user_input(UserInputKey.PARTICIPANT_ID, "")
            device_id = self.state.get_user_input(UserInputKey.DEVICE_ID, "")
            data_path = self.state.get_user_input(UserInputKey.DATA_PATH, "")
            username = self.state.get_user_input(UserInputKey.USERNAME, "")

            if not all([participant_id, data_path, username]):
                self.logger.error("Missing required information for gallery creation")
                self.gallery_output.append(MESSAGES.Errors.ERROR_MISSING_GALLERY_INFO)
                self.gallery_output.append(
                    "📌 What to try next: go back to Participant Setup and confirm the participant ID and device account details."
                )
                self.gallery_output.append(
                    "📌 When to ask for help: if those details look correct but this step still cannot start, ask technical support."
                )
                raise FlashTVError(
                    "Missing participant ID, data path, or username",
                    ErrorType.VALIDATION_ERROR,
                    recovery_action="Go back to Participant Setup and confirm the participant ID and device account details. If that still does not fix it, ask technical support for help.",
                )

            self.logger.info(
                f"Starting gallery creation for participant: {participant_id}"
            )
            self.update_status(StepStatus.AUTOMATION_RUNNING)
            self.create_gallery_button.setEnabled(False)
            self.continue_button.setEnabled(False)
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(10)
            self.progress_bar.setFormat("Starting gallery creation... %p%")

            # Construct gallery path
            full_participant_id = build_participant_full_id(participant_id, device_id)
            gallery_path = str(get_gallery_dir(username, participant_id, device_id))
            self.gallery_path_input.setText(gallery_path)
            self.state.set_user_input(UserInputKey.GALLERY_PATH, gallery_path)
            self.state.set_user_input(UserInputKey.GALLERY_VALIDATED, False)
            self.state.set_user_input(UserInputKey.GALLERY_TOTAL_IMAGES, 0)

            # Persist state
            if self.state_manager:
                self.state_manager.save_state(self.state)

            self.gallery_output.clear()
            self.gallery_output.append("📋 Starting gallery creation...")
            self.gallery_output.append(f"👤 Participant: {full_participant_id}")
            self.gallery_output.append(f"📁 Gallery location: {gallery_path}")
            self.gallery_output.append(f"💾 Data path: {data_path}")

            # Run gallery creation script
            script_path = (
                f"/home/{username}/flash-tv-scripts/runtime_scripts/build_gallery.sh"
            )

            self.gallery_output.append("\n🚀 Launching gallery creation window...")

            command = ["bash", script_path, full_participant_id, username, data_path]

            process_info = self.process_runner.run_script(
                command=command,
                description=f"Creating face gallery for {full_participant_id}",
                working_dir=os.path.expanduser("~/flash-tv-scripts/runtime_scripts"),
                process_name="gallery_creation",
            )

            if process_info:
                self.progress_bar.setValue(30)
                self.progress_bar.setFormat("Loading face detection models... %p%")
                self.gallery_output.append(
                    "✅ Gallery creation script launched successfully"
                )
                self.gallery_output.append(
                    "\n⏳ Loading face detection models (this may take 30-60 seconds)..."
                )
                self.gallery_output.append(
                    "📊 See keyboard shortcuts in the right panel →"
                )
                self.logger.info("Gallery creation script started successfully")
                # Monitor process completion in update_ui
            else:
                self.logger.error("Failed to start gallery creation script")
                self.gallery_output.append(
                    "❌ The gallery window could not be started."
                )
                self.gallery_output.append(
                    "📌 What to try next: click 'Create Gallery' again once."
                )
                self.gallery_output.append(
                    "📌 When to ask for help: if the gallery window still does not open, ask technical support."
                )
                self.update_status(StepStatus.FAILED)
                self._reset_gallery_creation_ui()
                raise FlashTVError(
                    "Failed to start gallery creation script",
                    ErrorType.PROCESS_ERROR,
                    recovery_action="Try starting gallery creation again once. If the window still does not open, ask technical support for help.",
                )

        except Exception as e:
            self.logger.error(f"Error during gallery creation: {e}")
            self.update_status(StepStatus.FAILED)
            self._reset_gallery_creation_ui()
            raise

    @handle_step_error
    def _fill_missing_extra_faces(self) -> None:
        """Check if extra faces are missing and fill with poster faces if needed."""
        try:
            participant_id = self.state.get_user_input(UserInputKey.PARTICIPANT_ID, "")
            device_id = self.state.get_user_input(UserInputKey.DEVICE_ID, "")
            data_path = self.state.get_user_input(UserInputKey.DATA_PATH, "")
            username = self.state.get_user_input(UserInputKey.USERNAME, "")

            if not all([participant_id, device_id, data_path, username]):
                self.logger.warning(
                    "Missing required information for poster face filling"
                )
                return

            # Get the faces folder path
            combined_id = f"{participant_id}{device_id}"
            faces_folder = os.path.join(data_path, f"{combined_id}_faces")

            if not os.path.exists(faces_folder):
                self.logger.warning(f"Faces folder does not exist: {faces_folder}")
                return

            # Count existing extra faces
            import glob

            extra_pattern = os.path.join(faces_folder, f"{combined_id}_extra*.png")
            extra_faces = glob.glob(extra_pattern)
            extra_count = len(extra_faces)

            self.logger.info(f"Found {extra_count} extra faces in gallery")

            # If we have fewer than 5 extra faces, copy poster faces
            min_faces = 5
            if extra_count < min_faces:
                self.gallery_output.append(
                    f"\n📋 Found only {extra_count} extra faces (need {min_faces})"
                )
                self.gallery_output.append(
                    "🖼️  Filling missing extra faces with poster images..."
                )

                # Poster faces location
                poster_faces_dir = f"/home/{username}/flash-tv-scripts/poster_faces"

                if not os.path.exists(poster_faces_dir):
                    self.logger.warning(
                        f"Poster faces directory not found: {poster_faces_dir}"
                    )
                    self.gallery_output.append("⚠️  Poster faces directory not found")
                    return

                # Get poster face files
                poster_files = sorted(
                    glob.glob(os.path.join(poster_faces_dir, "*.png"))
                )

                if not poster_files:
                    self.logger.warning("No poster face images found")
                    self.gallery_output.append("⚠️  No poster face images found")
                    return

                # Copy poster faces to fill the gaps
                import shutil

                faces_copied = 0
                for i in range(extra_count + 1, min_faces + 1):
                    # Use modulo to cycle through poster faces
                    poster_idx = (i - 1) % len(poster_files)
                    source_file = poster_files[poster_idx]
                    dest_file = os.path.join(
                        faces_folder, f"{combined_id}_extra{i}.png"
                    )

                    shutil.copy2(source_file, dest_file)
                    faces_copied += 1
                    self.logger.info(f"Copied poster face {i}")

                self.gallery_output.append(
                    f"✅ Copied {faces_copied} poster faces to complete the gallery"
                )
            else:
                self.logger.info("Extra faces complete - no poster faces needed")

        except Exception as e:
            self.logger.error(f"Error filling missing extra faces: {e}")
            self.gallery_output.append(
                f"⚠️  Warning: Could not fill missing extra faces: {e}"
            )

    @handle_step_error
    def _fill_unchecked_family_roles(self) -> None:
        participant_id = self.state.get_user_input(UserInputKey.PARTICIPANT_ID, "")
        device_id = self.state.get_user_input(UserInputKey.DEVICE_ID, "")
        data_path = self.state.get_user_input(UserInputKey.DATA_PATH, "")
        username = self.state.get_user_input(UserInputKey.USERNAME, "")

        if not all([participant_id, data_path, username]):
            self.logger.warning("Missing required information for family role fillers")
            self.gallery_output.append(
                "⚠️ Could not fill missing family roles because participant setup information is incomplete."
            )
            self.gallery_output.append(
                "📌 Go back to Participant Setup, confirm the participant details, and then rerun gallery creation if needed."
            )
            return

        combined_id = f"{participant_id}{device_id}" if device_id else participant_id
        faces_folder = Path(data_path) / f"{combined_id}_faces"

        if not faces_folder.exists():
            self.logger.warning(f"Faces folder does not exist: {faces_folder}")
            self.gallery_output.append(
                "⚠️ The gallery folder was not found, so missing family roles were not filled."
            )
            self.gallery_output.append(
                "📌 Create the gallery again. If the folder still is not created, ask technical support for help."
            )
            return

        filler_root = Path(f"/home/{username}/flash-tv-scripts/filler_faces")
        role_fillers = {
            "tc": {
                "checked": self.tc_checkbox.isChecked(),
                "source_dir": filler_root / "face1",
                "label": "target child",
            },
            "sib": {
                "checked": self.sib_checkbox.isChecked(),
                "source_dir": filler_root / "face2",
                "label": "sibling",
            },
            "parent": {
                "checked": self.parent_checkbox.isChecked(),
                "source_dir": filler_root / "face3",
                "label": "parent",
            },
        }

        for role_name, role_info in role_fillers.items():
            if role_info["checked"]:
                continue

            source_dir = role_info["source_dir"]
            label = role_info["label"]

            if not source_dir.exists():
                self.logger.warning(
                    f"Filler directory not found for {label}: {source_dir}"
                )
                self.gallery_output.append(
                    f"⚠️  Missing filler folder for {label}; continuing without automatic fill."
                )
                continue

            source_files = sorted(source_dir.glob("*.png"))
            if not source_files:
                self.logger.warning(
                    f"No filler face images found for {label}: {source_dir}"
                )
                self.gallery_output.append(
                    f"⚠️  No filler images were found for {label}; continuing without automatic fill."
                )
                continue

            if len(source_files) < 5:
                self.logger.warning(
                    f"Incomplete filler set for {label}: found {len(source_files)} image(s)"
                )
                self.gallery_output.append(
                    f"⚠️  Only found {len(source_files)} filler image(s) for {label}. Copying what is available."
                )

            copied_count = 0
            for index, source_file in enumerate(source_files[:5], start=1):
                destination_file = (
                    faces_folder / f"{combined_id}_{role_name}{index}.png"
                )
                shutil.copy2(source_file, destination_file)
                copied_count += 1

            self.logger.info(
                f"Filled {copied_count} deterministic face(s) for unchecked role: {label}"
            )
            self.gallery_output.append(
                f"🧩 Added {copied_count} filler face(s) for {label}."
            )

    def _validate_gallery(self, checked: bool = False) -> None:
        """Validate the gallery structure and contents automatically."""
        try:
            gallery_path = self.state.get_user_input(UserInputKey.GALLERY_PATH, "")
            if not gallery_path:
                self.logger.warning("No gallery path available for validation")
                return

            self.logger.info(f"Validating gallery at path: {gallery_path}")
            self.gallery_output.append("\n🔍 Validating gallery structure...")

            gallery_dir = Path(gallery_path)

            if not gallery_dir.exists():
                self.logger.error(f"Gallery directory does not exist: {gallery_path}")
                self.gallery_output.append("❌ Gallery directory does not exist")
                self.gallery_output.append(
                    "📌 What to try next: create the gallery again before continuing."
                )
                self.gallery_output.append(
                    "📌 When to ask for help: if the gallery folder still is not created, ask technical support."
                )
                raise FlashTVError(
                    f"Gallery directory does not exist: {gallery_path}",
                    ErrorType.SYSTEM_ERROR,
                    recovery_action="Create the gallery again before continuing. If the gallery folder still is not created, ask technical support for help.",
                )

            # Check for required face categories
            participant_id = self.state.get_user_input(UserInputKey.PARTICIPANT_ID, "")
            device_id = self.state.get_user_input(UserInputKey.DEVICE_ID, "")
            full_participant_id = (
                f"{participant_id}{device_id}" if device_id else participant_id
            )
            required_faces = MESSAGES.Gallery.ROLES

            validation_passed = True
            total_images = 0

            for face_type in required_faces:
                face_files = list(
                    gallery_dir.glob(f"{full_participant_id}_{face_type}*.png")
                )

                if face_files:
                    count = len(face_files)
                    total_images += count
                    self.gallery_output.append(
                        f"✅ Found {count} images for {face_type}"
                    )
                    self.logger.debug(f"Found {count} images for {face_type}")
                else:
                    self.gallery_output.append(f"❌ Missing images for {face_type}")
                    self.logger.warning(f"Missing images for face type: {face_type}")
                    validation_passed = False

            if validation_passed:
                self.logger.info(
                    f"Gallery validation successful - {total_images} total images"
                )
                self.gallery_output.append("\n🎉 Gallery validation successful!")
                self.gallery_output.append(f"📊 Total images found: {total_images}")
                self.gallery_output.append("✨ Your face gallery is ready for use!")

                # Save validation status
                self.state.set_user_input(UserInputKey.GALLERY_VALIDATED, True)
                self.state.set_user_input(
                    UserInputKey.GALLERY_TOTAL_IMAGES, total_images
                )

                # Persist state
                if self.state_manager:
                    self.state_manager.save_state(self.state)

                self.update_status(StepStatus.COMPLETED)
                self.continue_button.setEnabled(True)
            else:
                self.logger.warning(
                    "Gallery validation failed - missing required images"
                )
                self.gallery_output.append("\n❌ Gallery validation failed")
                self.gallery_output.append(
                    "📌 What to try next: reopen the gallery window and capture the missing face groups, then validate again."
                )
                self.gallery_output.append(
                    "📌 When to ask for help: if the gallery will not save the missing images after another try, ask technical support."
                )
                self.update_status(StepStatus.USER_ACTION_REQUIRED)

        except Exception as e:
            self.logger.error(f"Error during gallery validation: {e}")
            self.update_status(StepStatus.FAILED)
            raise

    @handle_step_error
    def _on_continue_clicked(self, checked: bool = False) -> None:
        """Handle continue button click with validation."""
        try:
            if self.is_completed() and self.continue_button.isEnabled():
                gallery_path = self.state.get_user_input(UserInputKey.GALLERY_PATH, "")
                total_images = self.state.get_user_input(
                    UserInputKey.GALLERY_TOTAL_IMAGES, 0
                )

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
        """Reset the gallery creation UI after process completion."""
        try:
            self.progress_bar.setVisible(False)
            self.progress_bar.setValue(0)
            self._update_gallery_readiness()
            self.logger.debug("Reset gallery creation UI")

        except Exception as e:
            self.logger.error(f"Error resetting gallery UI: {e}")

    @handle_step_error
    def activate_step(self) -> None:
        """Activate the gallery creation step with state restoration."""
        super().activate_step()

        self.logger.info("Gallery creation step activated")

        # Clear previous output to avoid duplicates when re-activating step
        self.gallery_output.clear()

        self._restore_gallery_verification_state()

        # Auto-generate gallery path from participant info
        self._load_existing_gallery_path()

        # Check if already validated
        if self.state.get_user_input(UserInputKey.GALLERY_VALIDATED, False):
            gallery_path = self.state.get_user_input(UserInputKey.GALLERY_PATH, "")
            total_images = self.state.get_user_input(
                UserInputKey.GALLERY_TOTAL_IMAGES, 0
            )
            if gallery_path:
                self.gallery_output.append(
                    f"✅ Gallery already validated: {total_images} images"
                )
                self.continue_button.setEnabled(True)
                self.update_status(StepStatus.COMPLETED)
                self.logger.info("Gallery already validated, skipping")
                return

        # Check if gallery path is already set and validate it
        gallery_path = self.state.get_user_input(UserInputKey.GALLERY_PATH, "")
        if gallery_path and Path(gallery_path).exists():
            self.gallery_output.append("📁 Found existing gallery")
            self._validate_gallery()
        else:
            self.gallery_output.append("📋 Ready to create face gallery")
            self.gallery_output.append(
                "👆 Complete the verification section above to enable Create Gallery"
            )

    def update_ui(self) -> None:
        """Update UI elements periodically with framework integration."""
        super().update_ui()

        # Check gallery creation process status
        process_info = self.state.get_process("gallery_creation")
        if process_info:
            # Update progress bar based on stderr output (model loading)
            stdout_lines, stderr_lines = process_info.get_output()

            # Track model loading progress
            if stderr_lines:
                model_load_keywords = [
                    "Loading weights",
                    "conv",
                    "detection",
                    "src/nnvm",
                    "MXNET_CUDNN",
                    "Initializing",
                    "cudnn",
                ]
                model_lines = [
                    line
                    for line in stderr_lines
                    if any(keyword in line for keyword in model_load_keywords)
                ]

                if model_lines:
                    # Estimate progress based on model loading stages
                    # Check in reverse order (most recent progress)
                    if any("cudnn" in line.lower() for line in model_lines[-20:]):
                        self.progress_bar.setValue(100)
                        self.progress_bar.setFormat("Models loaded - Window ready! %p%")
                    elif any("MXNET_CUDNN" in line for line in model_lines[-20:]):
                        self.progress_bar.setValue(90)
                        self.progress_bar.setFormat(
                            "Optimizing model performance... %p%"
                        )
                    elif any("src/nnvm" in line for line in model_lines[-20:]):
                        self.progress_bar.setValue(70)
                        self.progress_bar.setFormat(
                            "Loading face verification model... %p%"
                        )
                    elif any("Loading weights" in line for line in model_lines):
                        self.progress_bar.setValue(50)
                        self.progress_bar.setFormat(
                            "Loading face detection weights... %p%"
                        )
                    elif any("Initializing" in line for line in model_lines):
                        self.progress_bar.setValue(30)
                        self.progress_bar.setFormat("Initializing models... %p%")

            if not process_info.is_running():
                status = process_info.get_status()
                if status == ProcessStatus.COMPLETED:
                    self.logger.info("Gallery creation script completed")
                    self.progress_bar.setValue(100)
                    self.progress_bar.setFormat("Gallery creation completed! %p%")
                    self.gallery_output.append("\n✅ Gallery creation window closed")

                    self._fill_unchecked_family_roles()

                    # Check and fill missing extra faces with poster faces
                    self._fill_missing_extra_faces()

                    self.gallery_output.append("\n🔍 Starting automatic validation...")

                    # Automatically validate the gallery
                    self._validate_gallery()
                elif status == ProcessStatus.FAILED:
                    self.logger.error("Gallery creation failed")
                    self.progress_bar.setFormat("Gallery creation failed")
                    self.gallery_output.append("\n❌ Gallery creation failed")
                    self.gallery_output.append(
                        "📌 What to try next: restart gallery creation once and watch for any problem in the capture window."
                    )
                    self.gallery_output.append(
                        "📌 When to ask for help: if it fails again, ask technical support and share the details below if requested."
                    )

                    # Get and show error output
                    stdout_lines, stderr_lines = process_info.get_output()
                    if stderr_lines:
                        self.gallery_output.append("\nSupport details:")
                        for line in stderr_lines[-10:]:
                            self.gallery_output.append(f"  {line}")
                    self.update_status(StepStatus.FAILED)
                elif status == ProcessStatus.TERMINATED:
                    self.logger.warning("Gallery creation was terminated")
                    self.progress_bar.setFormat("Gallery creation terminated")
                    self.gallery_output.append("\n⚠️ Gallery creation was closed before it finished.")
                    self.gallery_output.append(
                        "📌 What to try next: start gallery creation again and finish the capture steps."
                    )
                    self.gallery_output.append(
                        "📌 When to ask for help: if the gallery window keeps closing early, ask technical support."
                    )
                    self.update_status(StepStatus.FAILED)
                else:
                    self.logger.error(
                        "Gallery creation finished with unexpected status"
                    )
                    self.gallery_output.append(
                        "\n⚠️ Gallery creation finished in an unexpected way."
                    )
                    self.gallery_output.append(
                        "📌 What to try next: restart gallery creation once."
                    )
                    self.gallery_output.append(
                        "📌 When to ask for help: if this happens again, ask technical support."
                    )
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
