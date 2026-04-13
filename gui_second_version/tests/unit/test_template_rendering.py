from __future__ import annotations

import contextlib
from collections.abc import Iterator
from dataclasses import dataclass
import importlib.util
from pathlib import Path
import sys
import types


@contextlib.contextmanager
def _temporary_module_entry(module_name: str) -> Iterator[None]:
    original = sys.modules.get(module_name)
    try:
        yield
    finally:
        if original is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = original


@contextlib.contextmanager
def _temporary_sys_path(path: Path) -> Iterator[None]:
    path_str = str(path)
    original = list(sys.path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)
    try:
        yield
    finally:
        sys.path[:] = original


def _load_config_support_modules(repo_root: Path) -> dict[str, object]:
    config_dir = repo_root / "config"
    config_package = types.ModuleType("config")
    config_package.__path__ = [str(config_dir)]

    loader_name = "config.install_defaults_loader"
    loader_spec = importlib.util.spec_from_file_location(
        loader_name,
        config_dir / "install_defaults_loader.py",
    )
    assert loader_spec is not None
    assert loader_spec.loader is not None
    loader_module = importlib.util.module_from_spec(loader_spec)
    sys.modules[loader_name] = loader_module
    try:
        loader_spec.loader.exec_module(loader_module)
    finally:
        sys.modules.pop(loader_name, None)

    return {
        "config": config_package,
        loader_name: loader_module,
    }


def _load_participant_manager_module():
    repo_root = Path(__file__).resolve().parents[3]
    module_path = repo_root / "python_scripts" / "participant_manager.py"
    spec = importlib.util.spec_from_file_location(
        "participant_manager_test_module", module_path
    )
    assert spec is not None
    assert spec.loader is not None
    support_modules = _load_config_support_modules(repo_root)
    with (
        _temporary_sys_path(repo_root),
        _temporary_module_entry(spec.name),
        _temporary_module_entry("participant_config"),
        _temporary_module_entry("config"),
        _temporary_module_entry("config.install_defaults_loader"),
        _temporary_module_entry("flash_tv_install_defaults"),
    ):
        sys.modules.update(support_modules)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
    return module


def _load_home_assistant_image() -> str:
    repo_root = Path(__file__).resolve().parents[3]
    support_modules = _load_config_support_modules(repo_root)
    with (
        _temporary_sys_path(repo_root),
        _temporary_module_entry("config"),
        _temporary_module_entry("config.install_defaults_loader"),
        _temporary_module_entry("flash_tv_install_defaults"),
    ):
        sys.modules.update(support_modules)
        loader_module = support_modules["config.install_defaults_loader"]
        install_defaults_module = loader_module.load_install_defaults_module()
        return str(install_defaults_module.HOME_ASSISTANT_IMAGE)


HOME_ASSISTANT_IMAGE = _load_home_assistant_image()


@dataclass(frozen=True)
class _TempParticipantConfig:
    participant_id: str
    device_id: str
    username: str
    root_dir: Path
    smart_plug_switch_entity_id: str = "switch.third_reality_inc_3rsp02028bz"
    smart_plug_power_sensor_entity_id: str = (
        "sensor.third_reality_inc_3rsp02028bz_power"
    )
    bluetooth_beacon_mac_address: str = "Not Needed for this Visit"

    @property
    def full_id(self) -> str:
        return f"{self.participant_id}{self.device_id}"

    @property
    def home_dir(self) -> Path:
        return self.root_dir

    @property
    def data_root(self) -> Path:
        return self.root_dir / "data"

    @property
    def data_dir(self) -> Path:
        return self.data_root / f"{self.full_id}_data"

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"

    @property
    def tv_power_csv_path(self) -> Path:
        return self.data_dir / f"{self.full_id}_tv_power_5s.csv"

    @property
    def homeassistant_root(self) -> Path:
        return self.root_dir / "homeassistant-compose"

    @property
    def homeassistant_config_dir(self) -> Path:
        return self.homeassistant_root / "config"

    @property
    def homeassistant_archive_dir(self) -> Path:
        return self.homeassistant_root / "archived_participants"

    @property
    def git_config_copy_path(self) -> Path:
        return self.data_dir / "git_config.txt"

    @property
    def backup_readiness_path(self) -> Path:
        return self.data_dir / "participant_change_backup_readiness.txt"

    def template_values(self) -> dict[str, str]:
        return {
            "PARTICIPANT_ID": self.participant_id,
            "DEVICE_ID": self.device_id,
            "USERNAME": self.username,
            "FULL_ID": self.full_id,
            "HOME_DIR": str(self.root_dir),
            "DATA_DIR": str(self.data_dir),
            "LOGS_DIR": str(self.logs_dir),
            "HOMEASSISTANT_DIR": str(self.homeassistant_root),
            "HOMEASSISTANT_CONFIG_DIR": str(self.homeassistant_config_dir),
            "HOME_ASSISTANT_IMAGE": HOME_ASSISTANT_IMAGE,
            "SMART_PLUG_SWITCH_ENTITY_ID": self.smart_plug_switch_entity_id,
            "SMART_PLUG_POWER_SENSOR_ENTITY_ID": self.smart_plug_power_sensor_entity_id,
            "TV_POWER_CSV_PATH": str(self.tv_power_csv_path),
            "TV_POWER_CSV_CONTAINER_PATH": f"/{self.full_id}_data/{self.full_id}_tv_power_5s.csv",
            "DATA_DIR_CONTAINER_PATH": f"/{self.full_id}_data",
            "BLUETOOTH_BEACON_MAC_ADDRESS": self.bluetooth_beacon_mac_address,
        }


class TestParticipantTemplateRendering:
    def test_render_template_inserts_participant_values(self, tmp_path):
        module = _load_participant_manager_module()
        manager = module.ParticipantManager(
            config=module.build_participant_config(
                participant_id="P1-1234",
                device_id="007",
                username="flashsys007",
            ),
            repo_root=tmp_path,
        )
        template_dir = tmp_path / "config" / "templates"
        template_dir.mkdir(parents=True)
        (template_dir / "service.tmpl").write_text(
            "User={{USERNAME}}\nParticipant={{FULL_ID}}\nData={{DATA_DIR}}\n",
            encoding="utf-8",
        )

        target = tmp_path / "rendered" / "service.txt"
        manager._render_template(
            "service.tmpl", target, manager.config.template_values()
        )

        assert target.read_text(encoding="utf-8") == (
            "User=flashsys007\n"
            "Participant=P1-1234007\n"
            "Data=/home/flashsys007/data/P1-1234007_data\n"
        )

    def test_render_template_is_idempotent_for_same_context(self, tmp_path):
        module = _load_participant_manager_module()
        manager = module.ParticipantManager(
            config=module.build_participant_config(
                participant_id="ES-4321",
                device_id="123",
                username="flashsys123",
            ),
            repo_root=tmp_path,
        )
        template_dir = tmp_path / "config" / "templates"
        template_dir.mkdir(parents=True)
        (template_dir / "compose.tmpl").write_text(
            "name={{FULL_ID}}\nmount={{DATA_DIR}}\n",
            encoding="utf-8",
        )

        target = tmp_path / "rendered" / "compose.yaml"
        context = manager.config.template_values()
        manager._render_template("compose.tmpl", target, context)
        first_render = target.read_text(encoding="utf-8")

        manager._render_template("compose.tmpl", target, context)

        assert target.read_text(encoding="utf-8") == first_render

    def test_render_template_rejects_unresolved_placeholders(self, tmp_path):
        module = _load_participant_manager_module()
        manager = module.ParticipantManager(
            config=module.build_participant_config(
                participant_id="P1-1234",
                device_id="007",
                username="flashsys007",
            ),
            repo_root=tmp_path,
        )
        template_dir = tmp_path / "config" / "templates"
        template_dir.mkdir(parents=True)
        (template_dir / "broken.tmpl").write_text(
            "Participant={{FULL_ID}}\nUnknown={{NOT_IN_CONTEXT}}\n",
            encoding="utf-8",
        )

        target = tmp_path / "rendered" / "broken.txt"

        try:
            manager._render_template(
                "broken.tmpl", target, manager.config.template_values()
            )
        except module.ParticipantManagerError as exc:
            assert "Template placeholders are still unresolved" in str(exc)
        else:
            raise AssertionError("Expected unresolved placeholders to raise an error")

    def test_render_homeassistant_artifacts_match_real_csv_contract(self, tmp_path):
        module = _load_participant_manager_module()
        repo_root = Path(__file__).resolve().parents[3]
        config = _TempParticipantConfig(
            participant_id="P1-1234",
            device_id="007",
            username="flashsys007",
            root_dir=tmp_path / "participant-home",
        )
        manager = module.ParticipantManager(config=config, repo_root=repo_root)

        manager._ensure_data_directories()
        manager._render_homeassistant_artifacts()
        manager._validate_homeassistant_csv_writer_contract()

        compose_text = (config.homeassistant_root / "compose.yaml").read_text(
            encoding="utf-8"
        )
        configuration_text = (
            config.homeassistant_config_dir / "configuration.yaml"
        ).read_text(encoding="utf-8")
        automations_text = (
            config.homeassistant_config_dir / "automations.yaml"
        ).read_text(encoding="utf-8")

        assert f"- {config.data_dir}:/{config.full_id}_data" in compose_text
        assert f'    - "/{config.full_id}_data"' in configuration_text
        assert (
            f'    filename: "/{config.full_id}_data/{config.full_id}_tv_power_5s.csv"'
            in configuration_text
        )
        assert "- service: notify.file" in automations_text
        assert config.smart_plug_power_sensor_entity_id in automations_text

    def test_detect_previous_full_id_reads_current_compose_mount_format(self, tmp_path):
        module = _load_participant_manager_module()
        repo_root = Path(__file__).resolve().parents[3]
        config = _TempParticipantConfig(
            participant_id="P1-1234",
            device_id="007",
            username="flashsys007",
            root_dir=tmp_path / "participant-home",
        )
        manager = module.ParticipantManager(config=config, repo_root=repo_root)
        config.homeassistant_root.mkdir(parents=True, exist_ok=True)
        (config.homeassistant_root / "compose.yaml").write_text(
            (
                "services:\n"
                "  homeassistant:\n"
                "    volumes:\n"
                f"      - {config.data_dir}:/{config.full_id}_data\n"
            ),
            encoding="utf-8",
        )

        assert manager._detect_previous_full_id() == config.full_id

    def test_ensure_data_directories_creates_real_csv_file(self, tmp_path):
        module = _load_participant_manager_module()
        repo_root = Path(__file__).resolve().parents[3]
        config = _TempParticipantConfig(
            participant_id="ES-4321",
            device_id="123",
            username="flashsys123",
            root_dir=tmp_path / "participant-home",
        )
        manager = module.ParticipantManager(config=config, repo_root=repo_root)

        manager._ensure_data_directories()

        assert config.data_root.is_dir()
        assert config.data_dir.is_dir()
        assert config.logs_dir.is_dir()
        assert config.tv_power_csv_path.exists()
        assert config.tv_power_csv_path.is_file()
        assert config.tv_power_csv_path.name == "ES-4321123_tv_power_5s.csv"

    def test_assess_backup_readiness_reports_required_next_action(self, tmp_path):
        module = _load_participant_manager_module()
        repo_root = Path(__file__).resolve().parents[3]
        config = _TempParticipantConfig(
            participant_id="P1-1234",
            device_id="007",
            username="flashsys007",
            root_dir=tmp_path / "participant-home",
        )
        manager = module.ParticipantManager(config=config, repo_root=repo_root)

        manager._ensure_data_directories()

        status = manager._assess_backup_readiness()

        assert status.is_ready is False
        assert "USB backup is not ready for this device yet" in status.summary
        assert status.next_action is not None
        report_text = config.backup_readiness_path.read_text(encoding="utf-8")
        assert "backup_ready=no" in report_text
        assert "borg_repo_configured=no" in report_text
        assert "borg_passphrase_configured=no" in report_text
        assert "next_action=Required next action before leaving the home" in report_text

    def test_assess_backup_readiness_accepts_existing_borg_configuration(
        self, tmp_path
    ):
        module = _load_participant_manager_module()
        repo_root = Path(__file__).resolve().parents[3]
        config = _TempParticipantConfig(
            participant_id="ES-4321",
            device_id="123",
            username="flashsys123",
            root_dir=tmp_path / "participant-home",
        )
        manager = module.ParticipantManager(config=config, repo_root=repo_root)

        manager._ensure_data_directories()
        config.home_dir.mkdir(parents=True, exist_ok=True)
        (config.home_dir / ".flash_borg_env").write_text(
            (
                "export BORG_PASSPHRASE='encoded-secret'\n"
                "export BORG_REPO='/media/flashsys123/UUID/USB_Backup_Data_flashsys123'\n"
            ),
            encoding="utf-8",
        )
        manager._probe_borg_repository = lambda borg_repo, borg_passphrase: None

        status = manager._assess_backup_readiness()

        assert status.is_ready is True
        assert status.next_action is None
        report_text = config.backup_readiness_path.read_text(encoding="utf-8")
        assert "backup_ready=yes" in report_text
        assert "borg_repo_configured=yes" in report_text
        assert "borg_passphrase_configured=yes" in report_text
        assert "borg_repo_accessible=yes" in report_text
