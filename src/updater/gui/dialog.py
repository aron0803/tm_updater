"""
Native folder picker for the GUI, isolated from pywebview's API surface.

Spec: docs/specs/gui_folder_dialog_spec.md (section 1: pywebview 6.2.x contract)

pywebview >= 5 removed the module level ``webview.create_file_dialog``; the dialog
must be created through the ``Window`` instance.  ``webview.FOLDER_DIALOG`` is also
deprecated in 6.2 in favour of ``webview.FileDialog.FOLDER``.  Everything that
touches those names lives here so the version drift stays in one place, and the
window is injected by the caller so the flow is unit-testable without a GUI.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from typing import Any

import webview


class DialogUnavailable(Exception):
    """The native folder dialog cannot be shown in this build/environment."""


def pywebview_version() -> str:
    try:
        return version("pywebview")
    except PackageNotFoundError:  # pragma: no cover - dev checkout without metadata
        return "unknown"


def folder_dialog_type() -> int:
    """
    The FOLDER dialog constant for the installed pywebview.

    6.2.x exposes ``webview.FileDialog.FOLDER``; older releases only had the
    (now deprecated) ``webview.FOLDER_DIALOG`` integer.
    """
    dialog_enum = getattr(webview, "FileDialog", None)
    if dialog_enum is not None:
        return int(dialog_enum.FOLDER)
    return int(webview.FOLDER_DIALOG)


def pick_folder(window: Any, start_dir: str) -> str | None:
    """
    Open the native folder dialog.

    Args:
        window: the live ``webview.Window`` (injected; None before the window exists).
        start_dir: initial folder, may be "" - pywebview falls back to the home dir.

    Returns:
        The chosen path, or None when the user cancelled.

    Raises:
        DialogUnavailable: the dialog could not be created at all.  Callers must
            surface this; pywebview's winforms backend also returns None when it
            has no browser instance, so a None return can only be treated as
            "cancelled" once the window is known to be alive.
    """
    if window is None:
        raise DialogUnavailable(f"主視窗尚未就緒（pywebview {pywebview_version()}）")
    if not hasattr(window, "create_file_dialog"):
        raise DialogUnavailable(
            f"pywebview {pywebview_version()} 的 Window 沒有 create_file_dialog"
        )

    try:
        result = window.create_file_dialog(folder_dialog_type(), directory=start_dir)
    except Exception as exc:  # noqa: BLE001 - any backend failure must be reportable
        raise DialogUnavailable(f"{type(exc).__name__}: {exc}") from exc

    return _first_path(result)


def _first_path(result: Any) -> str | None:
    """Normalise pywebview's return (tuple / list / str / None) to a single path."""
    if not result:
        return None
    if isinstance(result, (str, bytes)):
        return result.decode() if isinstance(result, bytes) else result
    if isinstance(result, (tuple, list)):
        first = result[0]
        return first.decode() if isinstance(first, bytes) else str(first)
    return str(result)
