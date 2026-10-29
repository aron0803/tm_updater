"""
Persisted GUI runtime state (last chosen project / packages folder).

Spec: docs/specs/gui_folder_dialog_spec.md section 3.3

Why a second file next to updater.toml: updater.toml is the deployment config an
administrator owns, while "which folder was last opened here" is operator state.
Keeping them apart means the GUI can remember a choice without overwriting the
shipped toml - and users who never touch the source control keep the automatic
chain (toml -> wheels folder above the exe -> built-in default).

Why TOML: the project already reads TOML (`tomllib`), it is the format the
operator edits by hand, and Windows paths stay readable -
``source = '..\\packages'`` as a literal string instead of JSON's doubled
backslashes.  Only a reader is in the standard library, so the writer here is a
fixed-schema emitter (three keys), not a general TOML serializer.
"""

from __future__ import annotations

import json
import os
import tempfile
import tomllib
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path

from updater.config import read_toml_text

STATE_FILENAME = "updater_state.toml"
LEGACY_STATE_FILENAME = "updater_state.json"  # 1.5.1 wrote JSON; read, then migrate
STATE_SCHEMA = 1
COMPANY_DIR = "Test Matrix"
PRODUCT_DIR = "Updater"
_STATE_HEADER = (
    "# Test Matrix Updater 執行期狀態（GUI 自動維護，可手動修改）\n"
    "# 沒有某個欄位 = 那一項改回自動解析（toml / updater 上一層 / 內建）\n"
)


@dataclass
class GuiState:
    """Last folders chosen in the GUI; None means "use automatic resolution"."""

    project: str | None = None
    source: str | None = None
    updated_at: str = ""

    def is_empty(self) -> bool:
        return not self.project and not self.source


def state_path(exe_dir: Path) -> Path:
    """Primary location: next to the exe, so a portable deployment keeps its state."""
    return exe_dir / STATE_FILENAME


def fallback_state_dir() -> Path:
    """Used when the exe folder is read-only (e.g. the updater runs off a share)."""
    base = Path(os.environ.get("LOCALAPPDATA", str(Path.home())))
    return base / COMPANY_DIR / PRODUCT_DIR


def state_files(exe_dir: Path) -> list[Path]:
    """Candidate state files, best first: exe folder, then %LOCALAPPDATA%."""
    primary = state_path(exe_dir)
    fallback = fallback_state_dir() / STATE_FILENAME
    return [primary] if fallback == primary else [primary, fallback]


def legacy_state_files(exe_dir: Path) -> list[Path]:
    """Older updater_state.json files, same order as state_files()."""
    primary = exe_dir / LEGACY_STATE_FILENAME
    fallback = fallback_state_dir() / LEGACY_STATE_FILENAME
    return [primary] if fallback == primary else [primary, fallback]


def load_saved_state(exe_dir: Path) -> tuple[GuiState, Path, str]:
    """
    Load whichever state file this deployment uses.

    Returns ``(state, write_target, error)``.  With no file yet, the write target
    is the exe folder, so the first explicit choice is stored next to the exe -
    and a deployment that never chooses one stays stateless (spec section 3.3.4).
    A legacy JSON file is read but written back as TOML on the next save.
    """
    files = state_files(exe_dir)
    for path in files:
        if path.exists():
            state, error = load_state(path)
            return state, path, error

    for path in legacy_state_files(exe_dir):
        if path.exists():
            state, error = load_state(path)
            return state, files[0], error
    return GuiState(), files[0], ""


def load_state(path: Path) -> tuple[GuiState, str]:
    """
    Read one state file (TOML, or the legacy JSON one by extension).

    Returns (state, error).  A missing file is not an error - it yields an empty
    state.  A corrupt file also yields an empty state but reports the problem so
    the GUI can say why nothing was restored.
    """
    if not path.exists():
        return GuiState(), ""

    if path.suffix.lower() == ".json":
        raw, error = _read_json(path)
    else:
        raw, error = _read_toml(path)
    if error:
        return GuiState(), error

    if not isinstance(raw, dict) or raw.get("schema") != STATE_SCHEMA:
        return GuiState(), f"{path.name} 格式不支援（schema 不符），已忽略"

    return (
        GuiState(
            project=_clean(raw.get("project")),
            source=_clean(raw.get("source")),
            updated_at=str(raw.get("updated_at", "")),
        ),
        "",
    )


def dump_state(state: GuiState) -> str:
    """Serialize to TOML text - pure, so the format itself is unit-testable."""
    payload = replace(state, updated_at=state.updated_at or _now())
    lines = [_STATE_HEADER, f"schema = {STATE_SCHEMA}"]
    for key in ("project", "source", "updated_at"):
        value = getattr(payload, key)
        if value:
            lines.append(f"{key} = {_toml_string(str(value))}")
    return "\n".join(lines) + "\n"


def save_state(path: Path, state: GuiState) -> str:
    """
    Write the state atomically (tmp file + ``os.replace``).

    Returns "" on success or a human readable error - the GUI logs it but keeps
    running, because losing the memory of a folder is not a reason to fail an update.
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            prefix=f"{path.name}.", suffix=".tmp", dir=str(path.parent)
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(dump_state(state))
            os.replace(tmp_name, path)
        except OSError:
            Path(tmp_name).unlink(missing_ok=True)
            raise
    except OSError as exc:
        return f"無法儲存 {path}: {type(exc).__name__}: {exc}"
    return ""


def usable(value: str | None) -> bool:
    """True when a remembered path still points at a real folder."""
    if not value:
        return False
    return Path(value).is_dir()


def _read_toml(path: Path) -> tuple[object, str]:
    try:
        # Same decoding tolerance as updater.toml (BOM / UTF-16 / cp950 editors).
        text, _encoding = read_toml_text(path)
        return tomllib.loads(text), ""
    except (OSError, ValueError, tomllib.TOMLDecodeError) as exc:
        return None, f"無法讀取 {path.name}: {type(exc).__name__}: {exc}"


def _read_json(path: Path) -> tuple[object, str]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), ""
    except (OSError, ValueError) as exc:
        return None, f"無法讀取 {path.name}: {type(exc).__name__}: {exc}"


def _toml_string(value: str) -> str:
    """
    Quote a path.

    TOML literal strings (single quotes) need no escaping, which is what keeps
    Windows and UNC paths readable; they cannot contain a single quote, so those
    rare values fall back to a basic string (and JSON's escaping matches TOML's).
    """
    if "'" not in value:
        return f"'{value}'"
    return json.dumps(value, ensure_ascii=False)


def _clean(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")
