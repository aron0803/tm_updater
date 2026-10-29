"""
Contract tests for the pywebview folder-dialog compat layer.

Spec: docs/specs/gui_folder_dialog_spec.md (section 5)

These exist because 1.5.0 shipped a GUI where "瀏覽…" did nothing: app.py called
the module level webview.create_file_dialog, which pywebview >= 5 removed.
"""

from pathlib import Path
from typing import Any

import pytest

from updater.gui import app as app_module
from updater.gui import dialog
from updater.gui.dialog import DialogUnavailable, folder_dialog_type, pick_folder


class FakeWindow:
    """Stand-in for webview.Window - records the dialog request."""

    def __init__(self, result: Any = None, exc: Exception | None = None) -> None:
        self._result = result
        self._exc = exc
        self.calls: list[tuple[int, str]] = []

    def create_file_dialog(
        self, dialog_type: int, directory: str = "", **kwargs: Any
    ) -> Any:
        self.calls.append((dialog_type, directory))
        if self._exc:
            raise self._exc
        return self._result


class TestPywebviewContract:
    def test_pinned_major_is_installed(self) -> None:
        """The dependency is pinned to 6.2.1; the tests must run on that line."""
        major, minor, *_ = dialog.pywebview_version().split(".")
        assert int(major) == 6
        assert int(minor) >= 2

    def test_folder_dialog_constant(self) -> None:
        assert folder_dialog_type() == 20  # webview.FileDialog.FOLDER

    def test_app_layer_does_not_use_the_removed_module_level_api(self) -> None:
        """
        Regression guard: webview.create_file_dialog was removed in pywebview 5.

        Only dialog.py may name the legacy constants (as a fallback), and it must
        reach the dialog through the Window instance.
        """
        app_source = Path(app_module.__file__).read_text(encoding="utf-8")
        assert "webview.create_file_dialog" not in app_source
        assert "webview.FOLDER_DIALOG" not in app_source

        dialog_source = Path(dialog.__file__).read_text(encoding="utf-8")
        assert "window.create_file_dialog(" in dialog_source


class TestPickFolder:
    def test_returns_selected_folder(self) -> None:
        window = FakeWindow(result=("D:\\Work\\ProjB",))

        assert pick_folder(window, "C:\\Test_Matrix") == "D:\\Work\\ProjB"

    def test_requests_the_folder_dialog_with_the_start_dir(self) -> None:
        window = FakeWindow(result=("D:\\Work\\ProjB",))
        pick_folder(window, "C:\\Test_Matrix")

        assert window.calls == [(20, "C:\\Test_Matrix")]

    def test_accepts_plain_string_result(self) -> None:
        assert pick_folder(FakeWindow(result="D:\\Work\\ProjB"), "") == "D:\\Work\\ProjB"

    def test_cancel_returns_none(self) -> None:
        assert pick_folder(FakeWindow(result=None), "") is None
        assert pick_folder(FakeWindow(result=()), "") is None

    def test_missing_window_is_reported(self) -> None:
        with pytest.raises(DialogUnavailable, match="主視窗尚未就緒"):
            pick_folder(None, "")

    def test_window_without_dialog_support_is_reported(self) -> None:
        with pytest.raises(DialogUnavailable, match="沒有 create_file_dialog"):
            pick_folder(object(), "")

    def test_backend_exception_becomes_dialog_unavailable(self) -> None:
        window = FakeWindow(exc=AttributeError("no attribute 'create_file_dialog'"))

        with pytest.raises(DialogUnavailable) as excinfo:
            pick_folder(window, "C:\\Test_Matrix")

        assert "AttributeError" in str(excinfo.value)
        assert excinfo.value.__cause__ is not None
