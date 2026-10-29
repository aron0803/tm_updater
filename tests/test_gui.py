from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from updater.config import GuiConfig, LauncherConfig, UpdaterConfig
from updater.core import UpdateResult
from updater.gui.app import Api
from updater.gui.state import GuiState, load_state
from updater.target import UpdateTarget


@pytest.fixture
def sample_config(tmp_path: Path) -> UpdaterConfig:
    """Create a sample config for testing."""
    return UpdaterConfig(
        packages=["test-pkg"],
        source=str(tmp_path),
        launcher=LauncherConfig(
            enabled=False,
            executable="",
            auto_launch=False,
            auto_update=False,
            auto_launch_enable=False,
            auto_update_enable=False,
            mode="on_success",
        ),
        gui=GuiConfig(theme="light"),
    )


@pytest.fixture
def api(sample_config: UpdaterConfig) -> Api:
    """Create an Api instance for testing."""
    return Api(sample_config, None)


@pytest.fixture
def api_with_python(sample_config: UpdaterConfig) -> Api:
    """Create an Api instance with a mock python_exe for testing."""
    return Api(sample_config, Path("python.exe"))


class TestGetVersions:
    def test_get_versions_returns_all_available_versions(
        self, api: Api, sample_config: UpdaterConfig, tmp_path: Path
    ) -> None:
        """Test that get_versions returns all versions sorted newest-first."""
        # Setup: Create multiple wheel files with different versions
        source_path = Path(sample_config.source)
        source_path.mkdir(exist_ok=True)

        # Create test wheel files
        (source_path / "test_pkg-3.0.0-py3-none-any.whl").write_bytes(b"fake")
        (source_path / "test_pkg-2.5.0-py3-none-any.whl").write_bytes(b"fake")

        # Call the API
        result = api.get_versions("test-pkg")

        # Assert
        assert result == ["3.0.0", "2.5.0"]  # newest first
        assert isinstance(result, list)


class TestInstallVersionedPackageSetsFlag:
    def test_install_versioned_package_sets_flag(
        self, api_with_python: Api, tmp_path: Path, sample_config: UpdaterConfig
    ) -> None:
        """Verify _auto_update_disabled is set to True after
        install_versioned_package.
        """
        # Create a fake wheel in the source directory so scan_packages finds it
        source_path = Path(sample_config.source)
        source_path.mkdir(exist_ok=True)
        (source_path / "test_pkg-2.5.0-py3-none-any.whl").write_bytes(b"fake")

        mock_result = UpdateResult(total=1, updated=1, failed=0, failures=[])

        # Patch _run_with_lock to run synchronously so flag is set before we assert
        api_with_python._run_with_lock = lambda fn: fn()  # type: ignore[assignment]

        with patch("updater.gui.app.install_updates", return_value=mock_result):
            with patch(
                "updater.gui.app.get_installed_versions_batch",
                return_value={"test-pkg": "1.0.0"},
            ):
                api_with_python.install_versioned_package("test-pkg", "2.5.0")

        assert api_with_python._auto_update_disabled is True


class TestCheckUpdatesRespectsAutoUpdateDisabled:
    def test_do_scan_returns_early_when_flag_set(self, api_with_python: Api) -> None:
        """_do_scan must return early without scanning when
        _auto_update_disabled is True.
        """
        api_with_python._auto_update_disabled = True

        mock_window = MagicMock()
        api_with_python._window = mock_window

        with patch("updater.gui.app.scan_packages") as mock_scan:
            with patch("updater.gui.app.check_updates") as mock_check:
                api_with_python._do_scan()

        # scan_packages and check_updates must NOT have been called
        mock_scan.assert_not_called()
        mock_check.assert_not_called()

        # onScanComplete must NOT have been called on the window
        for call in mock_window.evaluate_js.call_args_list:
            args = call[0]
            assert "onScanComplete" not in str(
                args
            ), "onScanComplete should not be called when auto-update is disabled"


class TestInstallVersionedPackageCallsInstallUpdates:
    def test_install_versioned_package_calls_install_updates_with_correct_args(
        self, api_with_python: Api, sample_config: UpdaterConfig
    ) -> None:
        """install_versioned_package must call install_updates with matching
        package and target_version."""
        source_path = Path(sample_config.source)
        source_path.mkdir(exist_ok=True)
        (source_path / "test_pkg-2.5.0-py3-none-any.whl").write_bytes(b"fake")

        mock_result = UpdateResult(total=1, updated=1, failed=0, failures=[])

        # Run synchronously so we can inspect the captured call
        api_with_python._run_with_lock = lambda fn: fn()  # type: ignore[assignment]

        with patch(
            "updater.gui.app.install_updates", return_value=mock_result
        ) as mock_install:
            with patch(
                "updater.gui.app.get_installed_versions_batch",
                return_value={"test-pkg": "1.0.0"},
            ):
                api_with_python.install_versioned_package("test-pkg", "2.5.0")

        mock_install.assert_called_once()
        call_kwargs = mock_install.call_args

        # Verify target_version was passed as "2.5.0"
        assert call_kwargs.kwargs.get("target_version") == "2.5.0" or (
            len(call_kwargs.args) >= 4 and call_kwargs.args[3] == "2.5.0"
        ), f"Expected target_version='2.5.0' in call, got: {call_kwargs}"

        # Verify the statuses list contains the correct package name
        statuses_arg = (
            call_kwargs.args[0]
            if call_kwargs.args
            else call_kwargs.kwargs.get("statuses")
        )
        assert statuses_arg is not None
        assert any(s.name == "test-pkg" for s in statuses_arg)


class FakeDialogWindow:
    """Minimal stand-in for webview.Window (pywebview 6.2.1 API)."""

    def __init__(self, result=None, exc: Exception | None = None) -> None:
        self._result = result
        self._exc = exc
        self.calls: list[tuple[int, str]] = []

    def create_file_dialog(self, dialog_type: int, directory: str = "", **kwargs):
        self.calls.append((dialog_type, directory))
        if self._exc:
            raise self._exc
        return self._result

    def evaluate_js(self, script: str) -> None:  # _push_log target
        pass


class TestChooseTargetFolder:
    """Spec: docs/specs/gui_folder_dialog_spec.md section 2."""

    @staticmethod
    def _api(sample_config: UpdaterConfig, window: object) -> Api:
        api = Api(sample_config, None)
        api._set_window(window)  # type: ignore[arg-type]
        return api

    def test_selected_folder_switches_target(self, sample_config: UpdaterConfig) -> None:
        api = self._api(sample_config, FakeDialogWindow(result=(r"D:\Work\ProjB",)))

        with patch.object(
            Api, "set_target", return_value={"error": None, "target": {"project": "x"}}
        ) as mock_set:
            result = api.choose_target_folder()

        mock_set.assert_called_once_with(r"D:\Work\ProjB")
        assert result == {"error": None, "target": {"project": "x"}}

    def test_cancel_leaves_target_untouched(self, sample_config: UpdaterConfig) -> None:
        api = self._api(sample_config, FakeDialogWindow(result=None))

        with patch.object(Api, "set_target") as mock_set:
            result = api.choose_target_folder()

        mock_set.assert_not_called()
        assert result["cancelled"] is True
        assert result["reason"] is None
        assert set(result) == {"cancelled", "reason", "target"}

    def test_dialog_start_dir_is_current_project(self, sample_config: UpdaterConfig) -> None:
        target = UpdateTarget(
            project_root=Path(r"D:\Work\ProjA"),
            config=sample_config,
            python_exe=None,
            config_origin="project",
        )
        api = Api(sample_config, None, target)
        window = FakeDialogWindow(result=None)
        api._set_window(window)  # type: ignore[arg-type]

        api.choose_target_folder()

        assert window.calls == [(20, r"D:\Work\ProjA")]

    def test_unavailable_dialog_is_logged_at_error_level(
        self, sample_config: UpdaterConfig
    ) -> None:
        api = Api(sample_config, None)  # window never set -> dialog unavailable

        with patch.object(api, "_push_log") as push:
            result = api.choose_target_folder()

        assert result["cancelled"] is True
        assert result["reason"], "a failed dialog must carry a reason for the GUI"
        assert set(result) == {"cancelled", "reason", "target"}
        assert push.call_args.args[0] == "error"

    def test_backend_failure_is_reported_as_reason(self, sample_config: UpdaterConfig) -> None:
        api = self._api(
            sample_config,
            FakeDialogWindow(exc=AttributeError("no attribute 'create_file_dialog'")),
        )

        with patch.object(api, "_push_log"):
            result = api.choose_target_folder()

        assert result["cancelled"] is True
        assert "AttributeError" in result["reason"]


class TestSetSource:
    """Spec: docs/specs/gui_folder_dialog_spec.md section 3.2."""

    @staticmethod
    def _api(sample_config: UpdaterConfig, tmp_path: Path) -> Api:
        target = UpdateTarget(
            project_root=tmp_path,
            config=sample_config,
            python_exe=None,
            config_origin="project",
        )
        return Api(sample_config, None, target, state_file=tmp_path / "updater_state.json")

    def test_switching_source_takes_effect(
        self, sample_config: UpdaterConfig, tmp_path: Path
    ) -> None:
        api = self._api(sample_config, tmp_path)
        wheels = tmp_path / "whl"
        (wheels / "a-1.0-py3-none-any.whl").parent.mkdir()
        (wheels / "a-1.0-py3-none-any.whl").write_bytes(b"")

        result = api.set_source(str(wheels))

        assert result["error"] is None
        assert api._source_path() == wheels
        assert result["target"]["source"] == str(wheels)
        assert result["target"]["source_origin"] == "gui"
        assert result["target"]["source_error"] == ""

    def test_missing_source_is_rejected_and_keeps_the_old_one(
        self, sample_config: UpdaterConfig, tmp_path: Path
    ) -> None:
        api = self._api(sample_config, tmp_path)
        before = api.get_target()["source"]

        result = api.set_source(str(tmp_path / "nope"))

        assert result["error"], "an unusable source must be reported, not swallowed"
        assert api._source_path() == Path(before)

    def test_empty_source_is_rejected(self, sample_config: UpdaterConfig, tmp_path: Path) -> None:
        api = self._api(sample_config, tmp_path)

        result = api.set_source("   ")

        assert "為空" in str(result["error"])

    def test_choose_source_folder_applies_the_choice(
        self, sample_config: UpdaterConfig, tmp_path: Path
    ) -> None:
        api = self._api(sample_config, tmp_path)
        wheels = tmp_path / "whl"
        wheels.mkdir()
        window = FakeDialogWindow(result=(str(wheels),))
        api._set_window(window)  # type: ignore[arg-type]

        result = api.choose_source_folder()

        assert result.get("cancelled") is None
        assert api._source_path() == wheels
        assert window.calls and window.calls[0][0] == 20

    def test_choose_source_folder_reports_unavailable_dialog(
        self, sample_config: UpdaterConfig, tmp_path: Path
    ) -> None:
        api = self._api(sample_config, tmp_path)  # no window

        with patch.object(api, "_push_log") as push:
            result = api.choose_source_folder()

        assert result["cancelled"] is True
        assert result["reason"]
        assert push.call_args.args[0] == "error"


class TestStatePersistence:
    """Spec: docs/specs/gui_folder_dialog_spec.md section 3.3."""

    @staticmethod
    def _api(
        sample_config: UpdaterConfig,
        state_file: Path,
        project_root: Path | None = None,
        state: GuiState | None = None,
        state_notes: list[str] | None = None,
    ) -> Api:
        root = project_root or Path.cwd()
        target = UpdateTarget(
            project_root=root,
            config=sample_config,
            python_exe=None,
            config_origin="project",
        )
        return Api(
            sample_config,
            None,
            target,
            state=state,
            state_file=state_file,
            state_notes=state_notes,
        )

    @staticmethod
    def _wheels(tmp_path: Path) -> Path:
        wheels = tmp_path / "whl"
        wheels.mkdir()
        (wheels / "a-1.0-py3-none-any.whl").write_bytes(b"")
        return wheels

    def test_nothing_is_written_until_the_user_chooses(
        self, sample_config: UpdaterConfig, tmp_path: Path
    ) -> None:
        state_file = tmp_path / "updater_state.json"
        api = self._api(sample_config, state_file)

        api.get_target()

        assert not state_file.exists(), (
            "automatic resolution must not be frozen into the state file, or the "
            "packages auto-discovery chain stops working for untouched deployments"
        )

    def test_a_chosen_source_survives_the_restart(
        self, sample_config: UpdaterConfig, tmp_path: Path
    ) -> None:
        state_file = tmp_path / "updater_state.json"
        api = self._api(sample_config, state_file)
        wheels = self._wheels(tmp_path)

        assert api.set_source(str(wheels))["error"] is None
        saved, error = load_state(state_file)
        assert error == "" and saved.source == str(wheels)

        # a new process: same state file, target resolved from scratch
        restarted = self._api(sample_config, state_file, state=saved)
        assert restarted._source_path() == wheels
        assert restarted.get_target()["source_origin"] == "gui"
        assert restarted.get_target()["source_saved"] is True

    def test_clear_target_forgets_the_project_but_keeps_the_source(
        self, sample_config: UpdaterConfig, tmp_path: Path
    ) -> None:
        state_file = tmp_path / "updater_state.json"
        api = self._api(sample_config, state_file)
        wheels = self._wheels(tmp_path)
        project = tmp_path / "proj"
        project.mkdir()

        api.set_source(str(wheels))
        assert api.set_target(str(project))["error"] is None
        assert load_state(state_file)[0].project == str(project)

        result = api.clear_target()

        assert result["error"] is None
        saved, _ = load_state(state_file)
        assert saved.project is None, "the auto-resolved project must not be re-saved"
        assert saved.source == str(wheels), "clearing the project keeps the source"
        assert api.get_target()["source"] == str(wheels)
        assert api.get_target()["project_saved"] is False

    def test_clear_source_releases_the_automatic_chain(
        self, sample_config: UpdaterConfig, tmp_path: Path
    ) -> None:
        state_file = tmp_path / "updater_state.json"
        api = self._api(sample_config, state_file)
        wheels = self._wheels(tmp_path)
        api.set_source(str(wheels))

        result = api.clear_source()

        assert result["error"] is None
        assert load_state(state_file)[0].source is None
        # back to the automatic chain: the fixture config carries no toml, so the
        # next level below a gui override is the config/builtin fallback
        assert api.get_target()["source_origin"] == "builtin"
        assert api.get_target()["source"] == str(tmp_path)
        assert api.get_target()["source_saved"] is False

    def test_a_stale_choice_is_ignored_not_fatal(
        self, sample_config: UpdaterConfig, tmp_path: Path
    ) -> None:
        state_file = tmp_path / "updater_state.json"
        stale = GuiState(project=str(tmp_path / "gone"), source=str(tmp_path / "gone-whl"))

        api = self._api(sample_config, state_file, state=stale)

        assert api._source_override is None
        assert api._project_override is None
        assert api.get_target()["source_saved"] is False
        assert api._source_path() == Path(sample_config.source)

    def test_read_only_exe_folder_falls_back_to_localappdata(
        self,
        sample_config: UpdaterConfig,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        blocked = tmp_path / "blocked"
        blocked.write_text("not a folder", encoding="utf-8")
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "appdata"))
        api = self._api(sample_config, blocked / "updater_state.json")
        wheels = self._wheels(tmp_path)

        with patch.object(api, "_push_log") as push:
            assert api.set_source(str(wheels))["error"] is None

        fallback = tmp_path / "appdata" / "Test Matrix" / "Updater" / "updater_state.json"
        assert fallback.exists()
        assert load_state(fallback)[0].source == str(wheels)
        assert push.call_args.args[0] == "warning"

    def test_state_notes_are_pushed_once(
        self, sample_config: UpdaterConfig, tmp_path: Path
    ) -> None:
        api = self._api(
            sample_config,
            tmp_path / "updater_state.json",
            state_notes=["沿用上次選擇的專案資料夾: C:\\Proj"],
        )

        with patch.object(api, "_push_log") as push:
            api._drain_state_notes()
            api._drain_state_notes()

        assert push.call_count == 1
        assert "沿用上次選擇的專案" in push.call_args.args[1]
