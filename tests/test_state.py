"""
Contract tests for the GUI runtime state file (updater_state.toml).

Spec: docs/specs/gui_folder_dialog_spec.md section 3.3
"""

from __future__ import annotations

import tomllib

import pytest

from updater.gui.state import (
    COMPANY_DIR,
    LEGACY_STATE_FILENAME,
    PRODUCT_DIR,
    STATE_FILENAME,
    GuiState,
    dump_state,
    fallback_state_dir,
    legacy_state_files,
    load_saved_state,
    load_state,
    save_state,
    state_files,
    state_path,
    usable,
)


class TestPaths:
    def test_state_file_sits_next_to_the_exe(self, tmp_path):
        assert state_path(tmp_path) == tmp_path / STATE_FILENAME

    def test_the_state_file_is_toml(self) -> None:
        assert STATE_FILENAME == "updater_state.toml"
        assert LEGACY_STATE_FILENAME == "updater_state.json"

    def test_fallback_lives_under_localappdata(self, tmp_path, monkeypatch):
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        assert fallback_state_dir() == tmp_path / COMPANY_DIR / PRODUCT_DIR

    def test_candidates_prefer_the_exe_folder(self, tmp_path, monkeypatch):
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "appdata"))
        files = state_files(tmp_path / "exe")
        assert files[0] == tmp_path / "exe" / STATE_FILENAME
        assert files[1] == tmp_path / "appdata" / COMPANY_DIR / PRODUCT_DIR / STATE_FILENAME
        assert len(set(files)) == len(files)
        assert all(p.suffix == ".toml" for p in files)
        assert all(p.suffix == ".json" for p in legacy_state_files(tmp_path / "exe"))


class TestTomlFormat:
    def test_paths_stay_readable_in_toml(self) -> None:
        text = dump_state(
            GuiState(
                project=r"C:\Test_Matrix",
                source=r"\\pnt52\研發本部\packages",
                updated_at="2026-10-29T13:00:00",
            )
        )
        assert "project = 'C:\\Test_Matrix'" in text, "no doubled backslashes"
        assert r"source = '\\pnt52\研發本部\packages'" in text
        assert tomllib.loads(text)["project"] == r"C:\Test_Matrix"

    def test_only_the_chosen_keys_are_written(self) -> None:
        raw = tomllib.loads(dump_state(GuiState(source=r"D:\whl")))
        assert raw["schema"] == 1
        assert set(raw) == {"schema", "source", "updated_at"}

    def test_a_value_with_a_quote_falls_back_to_a_basic_string(self) -> None:
        path = r"D:\it's here\packages"
        raw = tomllib.loads(dump_state(GuiState(source=path)))
        assert raw["source"] == path

    def test_a_timestamp_is_always_stamped(self) -> None:
        raw = tomllib.loads(dump_state(GuiState(project=r"C:\Proj")))
        assert raw["updated_at"]


class TestLoadSave:
    def test_missing_file_is_not_an_error(self, tmp_path):
        state, error = load_state(tmp_path / STATE_FILENAME)
        assert state.is_empty()
        assert error == ""

    def test_save_then_load_round_trip(self, tmp_path):
        path = tmp_path / STATE_FILENAME
        assert save_state(path, GuiState(project=r"C:\Proj", source=r"C:\whl")) == ""
        state, error = load_state(path)
        assert error == ""
        assert state.project == r"C:\Proj"
        assert state.source == r"C:\whl"
        assert state.updated_at

    def test_write_leaves_no_temp_file_behind(self, tmp_path):
        path = tmp_path / STATE_FILENAME
        save_state(path, GuiState(project=r"C:\Proj"))
        assert list(tmp_path.glob(f"{STATE_FILENAME}.*tmp")) == []

    def test_creates_a_missing_parent_directory(self, tmp_path):
        path = tmp_path / "nested" / "deeper" / STATE_FILENAME
        assert save_state(path, GuiState(source=r"C:\whl")) == ""
        assert path.exists()

    def test_unwritable_folder_reports_error_instead_of_raising(self, tmp_path):
        blocker = tmp_path / "blocked"
        blocker.write_text("not a folder", encoding="utf-8")
        error = save_state(blocker / STATE_FILENAME, GuiState(project="x"))
        assert "無法儲存" in error

    @pytest.mark.parametrize(
        "content",
        ["not toml at all", "schema = 2\nproject = 'C:\\Proj'", "project = C:\\Proj"],
    )
    def test_corrupt_or_foreign_file_yields_empty_state_with_a_message(
        self, tmp_path, content
    ):
        path = tmp_path / STATE_FILENAME
        path.write_text(content, encoding="utf-8")
        state, error = load_state(path)
        assert state.is_empty()
        assert error

    def test_blank_and_non_string_values_are_dropped(self, tmp_path):
        path = tmp_path / STATE_FILENAME
        path.write_text(
            "schema = 1\nproject = '   '\nsource = 42\n", encoding="utf-8"
        )
        state, _ = load_state(path)
        assert state.is_empty()

    def test_a_bom_or_cp950_file_still_reads(self, tmp_path):
        # an operator editing the file by hand on a zh-TW machine
        path = tmp_path / STATE_FILENAME
        path.write_bytes("schema = 1\nsource = 'D:\\研發本部\\packages'\n".encode("cp950"))
        state, error = load_state(path)
        assert error == ""
        assert state.source == r"D:\研發本部\packages"


class TestLegacyJson:
    def test_an_older_json_state_is_still_read(self, tmp_path):
        path = tmp_path / LEGACY_STATE_FILENAME
        path.write_text(
            '{"schema": 1, "project": "C:\\\\Proj", "source": null}', encoding="utf-8"
        )
        state, error = load_state(path)
        assert error == ""
        assert state.project == r"C:\Proj"

    def test_the_json_state_is_migrated_to_toml_on_the_next_save(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "appdata"))
        exe_dir = tmp_path / "exe"
        exe_dir.mkdir()
        (exe_dir / LEGACY_STATE_FILENAME).write_text(
            '{"schema": 1, "project": null, "source": "D:\\\\whl"}', encoding="utf-8"
        )

        state, write_to, error = load_saved_state(exe_dir)

        assert state.source == r"D:\whl"
        assert write_to == exe_dir / STATE_FILENAME, "next save writes TOML"

        assert save_state(write_to, state) == ""
        assert (exe_dir / STATE_FILENAME).read_text(encoding="utf-8").startswith("#")
        assert load_state(exe_dir / STATE_FILENAME)[0].source == r"D:\whl"


class TestLoadSavedState:
    def test_no_file_yet_targets_the_exe_folder_for_the_first_write(self, tmp_path, monkeypatch):
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "appdata"))
        state, write_to, error = load_saved_state(tmp_path / "exe")
        assert state.is_empty()
        assert write_to == tmp_path / "exe" / STATE_FILENAME
        assert error == ""

    def test_reads_the_localappdata_copy_when_the_exe_folder_has_none(self, tmp_path, monkeypatch):
        appdata = tmp_path / "appdata"
        monkeypatch.setenv("LOCALAPPDATA", str(appdata))
        fallback = fallback_state_dir() / STATE_FILENAME
        save_state(fallback, GuiState(source=r"\\server\whl"))

        state, write_to, error = load_saved_state(tmp_path / "exe")
        assert state.source == r"\\server\whl"
        assert error == ""
        assert write_to == fallback  # keep writing where it was found

    def test_a_parse_failure_is_reported_but_not_fatal(self, tmp_path, monkeypatch):
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "appdata"))
        exe_dir = tmp_path / "exe"
        exe_dir.mkdir()
        path = state_path(exe_dir)
        path.write_text("{ broken", encoding="utf-8")

        state, write_to, error = load_saved_state(exe_dir)
        assert state.is_empty()
        assert "無法讀取" in error
        assert write_to == path


class TestUsable:
    def test_only_existing_folders_count(self, tmp_path):
        folder = tmp_path / "whl"
        folder.mkdir()
        assert usable(str(folder))
        assert not usable(str(tmp_path / "gone"))
        assert not usable("")
        assert not usable(None)
