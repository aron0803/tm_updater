"""
Contract tests for the GUI runtime state file (updater_state.json).

Spec: docs/specs/gui_folder_dialog_spec.md section 3.3
"""

from __future__ import annotations

import json

import pytest

from updater.gui.state import (
    COMPANY_DIR,
    PRODUCT_DIR,
    STATE_FILENAME,
    GuiState,
    fallback_state_dir,
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

    def test_fallback_lives_under_localappdata(self, tmp_path, monkeypatch):
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        assert fallback_state_dir() == tmp_path / COMPANY_DIR / PRODUCT_DIR

    def test_candidates_prefer_the_exe_folder(self, tmp_path, monkeypatch):
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "appdata"))
        files = state_files(tmp_path / "exe")
        assert files[0] == tmp_path / "exe" / STATE_FILENAME
        assert files[1] == tmp_path / "appdata" / COMPANY_DIR / PRODUCT_DIR / STATE_FILENAME
        assert len(set(files)) == len(files)


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

    def test_payload_matches_the_spec_schema(self, tmp_path):
        path = tmp_path / STATE_FILENAME
        save_state(path, GuiState(project=r"C:\Proj", source=None))
        raw = json.loads(path.read_text(encoding="utf-8"))
        assert set(raw) == {"schema", "project", "source", "updated_at"}
        assert raw["schema"] == 1

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
        ["not json at all", '{"project": "C:\\\\Proj"}', "[1, 2, 3]"],
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
            json.dumps(
                {"schema": 1, "project": "   ", "source": 42, "updated_at": "x"}
            ),
            encoding="utf-8",
        )
        state, _ = load_state(path)
        assert state.is_empty()


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

        state, write_to, error = load_saved_state(tmp_path / "exe")
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
