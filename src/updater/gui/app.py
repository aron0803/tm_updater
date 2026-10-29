from __future__ import annotations

import argparse
import json
import sys
import threading
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import webview

from updater import get_version
from updater.config import UpdaterConfig
from packaging.version import Version

from updater.core import (
    STATUS_NOT_INSTALLED,
    STATUS_UP_TO_DATE,
    STATUS_UPDATE_AVAILABLE,
    UPDATABLE_STATUSES,
    PackageStatus,
    check_updates,
    clear_pip_cache,
    get_all_versions,
    get_installed_versions_batch,
    install_updates,
    scan_packages,
)
from updater.gui.dialog import DialogUnavailable, pick_folder
from updater.gui.state import (
    GuiState,
    fallback_state_dir,
    load_saved_state,
    save_state,
    state_path,
    usable,
)
from updater.launcher import LauncherError, launch_executable, should_launch
from updater.target import (
    ORIGIN_EXE,
    SourceResolution,
    TargetError,
    UpdateTarget,
    pick_source,
    resolve_target,
)


# Window geometry (gui_folder_dialog_spec.md section 3.1): the target bar shows
# three full paths on separate rows, so the default width has to fit them.
DEFAULT_WINDOW_WIDTH = 1200
MIN_WINDOW_SIZE = (900, 420)


def window_geometry(
    screens: list[webview.Screen] | None = None,
) -> tuple[int, webview.Screen | None]:
    """
    Window height and the screen to open on (spec section 3.1).

    ``screens`` is injectable so the rule is testable without a display; ``None``
    means "ask pywebview".  Height follows the display (70%, clamped) so the
    package list stays readable without swallowing the taskbar, and the returned
    ``Screen`` is handed to ``create_window(screen=...)`` — pywebview's own way to
    center the window on a scaled display.  ``(700, None)`` means "let the toolkit
    decide".
    """
    if screens is None:
        try:
            screens = webview.screens
        except Exception:
            return 700, None
    if not screens:
        return 700, None

    screen = screens[0]
    height = max(500, min(1000, int(screen.height * 0.7)))
    return height, screen


class Api:
    def __init__(
        self,
        config: UpdaterConfig,
        python_exe: Path | None,
        target: UpdateTarget | None = None,
        state: GuiState | None = None,
        state_file: Path | None = None,
        state_notes: list[str] | None = None,
    ) -> None:
        self._config = config
        self._python_exe = python_exe
        self._target = target
        self._window: webview.Window | None = None
        self._update_lock = threading.Lock()
        self._auto_update_disabled = False
        self._config_error_logged = False
        state = state or GuiState()
        # GUI-chosen whl folder; wins over every toml (target_resolution_spec §6.1)
        # and stays valid until changed, also across project switches.  Restored
        # from updater_state.json when the folder still exists (spec section 3.3).
        self._source_override: str | None = state.source if usable(state.source) else None
        self._project_override: str | None = state.project if usable(state.project) else None
        self._state_file = state_file or state_path(self._exe_dir())
        # what main() concluded while loading the state file; shown in the GUI log
        # on the first scan, because _push_log needs a window (same trick as the
        # config parse error)
        self._state_notes = list(state_notes or [])

    def _set_window(self, window: webview.Window) -> None:
        self._window = window

    # --- target (folder to update) -------------------------------------

    def _exe_dir(self) -> Path:
        return Path(sys.argv[0]).resolve().parent

    def _source_resolution(self, probe: bool = False) -> SourceResolution:
        """
        Resolve the whl source.  ``probe`` additionally checks reachability -
        worth an explicit call only where the result is reported, because an
        offline UNC share costs a few seconds in ``Path.exists()``.
        """
        return pick_source(
            self._config,
            exe_dir=self._exe_dir(),
            override_source=self._source_override,
            config_origin=(
                self._target.config_origin if self._target is not None else ORIGIN_EXE
            ),
            cwd=Path.cwd(),
            probe=probe,
        )

    def _source_path(self) -> Path:
        return self._source_resolution().path

    def _apply_target(self, target: UpdateTarget) -> None:
        """Hot-swap the folder being updated and drop stale pip data."""
        self._target = target
        self._config = target.config
        self._python_exe = target.python_exe
        clear_pip_cache()
        self._auto_update_disabled = False
        self._config_error_logged = False

    def _persist_state(self) -> None:
        """
        Remember the folders the user chose (spec section 3.3).

        Only explicit choices reach this path, so untouched deployments keep the
        automatic resolution chain.  A read-only exe folder falls back to
        %LOCALAPPDATA% instead of failing the update.
        """
        # only explicit choices are stored (spec 3.3.4): an automatically resolved
        # project_root must not be frozen into the state file
        state = GuiState(project=self._project_override, source=self._source_override)
        error = save_state(self._state_file, state)
        if error:
            fallback = fallback_state_dir() / self._state_file.name
            error = save_state(fallback, state)
            if error:
                self._push_log("warning", f"狀態未保存: {error}")
            else:
                self._state_file = fallback
                self._push_log("warning", f"exe 資料夾不可寫，狀態改存到 {fallback}")

    def clear_source(self) -> dict[str, object]:
        """Forget the chosen packages folder; automatic resolution takes over."""
        self._source_override = None
        clear_pip_cache()
        self._persist_state()
        self._push_log(
            "info", "packages 來源已還原為自動（toml → updater 上一層 → 內建預設）"
        )
        return {"error": None, "target": self.get_target()}

    def clear_target(self) -> dict[str, object]:
        """Forget the chosen project folder; automatic resolution takes over."""
        # a chosen packages source survives: only the project selection is cleared
        self._project_override = None
        exe_dir = self._exe_dir()
        try:
            target = resolve_target(None, exe_dir, Path.cwd())
        except TargetError as exc:
            return {"error": str(exc), "target": self.get_target()}
        self._apply_target(target)
        self._persist_state()
        self._push_log("info", f"目標已還原為自動解析: {target.describe()}")
        return {"error": None, "target": self.get_target()}

    def get_target(self) -> dict[str, object]:
        """Current update target, for the GUI header."""
        source = self._source_resolution(probe=True)
        base = {
            "project": "",
            "venv": "",
            "source": str(source.path),
            "source_origin": source.origin,
            "source_error": source.error,
            "config": str(self._config.config_dir),
            "config_origin": "",
            "config_error": self._config.parse_error,
            "encoding": self._config.encoding,
            # lets the GUI show/clear the saved choices (spec 3.3.5): True means the
            # value came from an explicit pick, so 「還原自動」 is meaningful
            "project_saved": self._project_override is not None,
            "source_saved": self._source_override is not None,
        }
        if self._target is None:
            base["error"] = "未解析到目標資料夾"
            return base
        venv = self._target.python_exe
        base.update(
            {
                "project": str(self._target.project_root),
                "venv": str(venv.parent.parent) if venv else "",
                "config_origin": self._target.config_origin,
                "error": "" if venv else "找不到 venv，請指定正確的專案資料夾",
            }
        )
        return base

    def set_target(self, project_path: str) -> dict[str, object]:
        """
        Point the updater at another project folder (typed in the GUI).

        Returns the new target payload, or {"error": "..."} when the path is
        unusable - the previous target stays active in that case.
        """
        exe_dir = Path(sys.argv[0]).resolve().parent
        try:
            target = resolve_target(project_path, exe_dir, Path.cwd())
        except TargetError as exc:
            self._push_log("error", f"目標設定失敗: {exc}")
            return {"error": str(exc), "target": self.get_target()}

        self._apply_target(target)
        self._project_override = str(target.project_root)
        self._push_log("success", f"目標資料夾: {target.describe()}")
        self._persist_state()
        return {"error": None, "target": self.get_target()}

    def choose_target_folder(self) -> dict[str, object]:
        """
        Open a native folder dialog and switch the target to the choice.

        Contract (docs/specs/gui_folder_dialog_spec.md section 2): always returns
        {"cancelled", "reason", "error", "target"}.  A dialog that cannot be shown
        is reported with a reason at error level - never silently swallowed - so the
        GUI can fall back to typing a path.
        """
        start_dir = ""
        if self._target is not None:
            start_dir = str(self._target.project_root)

        try:
            chosen = pick_folder(self._window, start_dir)
        except DialogUnavailable as exc:
            reason = str(exc)
            self._push_log("error", f"無法開啟資料夾對話框: {reason}")
            return {"cancelled": True, "reason": reason, "target": self.get_target()}

        if chosen is None:
            return {"cancelled": True, "reason": None, "target": self.get_target()}
        return self.set_target(chosen)

    # --- source (whl / packages folder) --------------------------------

    def set_source(self, source_path: str) -> dict[str, object]:
        """
        Point the updater at another whl folder for the rest of this run.

        Contract (docs/specs/gui_folder_dialog_spec.md section 3.2):
        {"error", "target"}; the previous source stays active on failure.
        """
        raw = (source_path or "").strip().strip('"')
        if not raw:
            return {"error": "packages 來源路徑為空", "target": self.get_target()}

        resolution = pick_source(
            self._config,
            exe_dir=self._exe_dir(),
            override_source=raw,
            config_origin=(
                self._target.config_origin if self._target is not None else ORIGIN_EXE
            ),
            cwd=Path.cwd(),
            probe=True,
        )
        if resolution.error:
            self._push_log("error", f"packages 來源設定失敗: {resolution.error}")
            return {"error": resolution.error, "target": self.get_target()}

        # store the resolved path: a relative entry ("..") would be meaningless
        # after a restart, and pick_source keeps UNC values untouched
        self._source_override = str(resolution.path)
        clear_pip_cache()
        self._push_log(
            "success", f"packages 來源: {resolution.path} ({resolution.origin})"
        )
        self._persist_state()
        return {"error": None, "target": self.get_target()}

    def choose_source_folder(self) -> dict[str, object]:
        """Native folder dialog for the whl source; contract = section 2 + 3.2."""
        start_dir = str(self._source_path())
        try:
            chosen = pick_folder(self._window, start_dir)
        except DialogUnavailable as exc:
            reason = str(exc)
            self._push_log("error", f"無法開啟資料夾對話框: {reason}")
            return {"cancelled": True, "reason": reason, "target": self.get_target()}

        if chosen is None:
            return {"cancelled": True, "reason": None, "target": self.get_target()}
        return self.set_source(chosen)

    def _run_with_lock(self, target_func: Callable[[], None]) -> None:
        """Spawn a daemon thread that runs target_func with lock management."""

        def safe_wrapper() -> None:
            # Wait for previous operations (like scanning) to release the lock
            self._update_lock.acquire(blocking=True)
            try:
                target_func()
            finally:
                self._update_lock.release()

        threading.Thread(target=safe_wrapper, daemon=True).start()

    def _should_auto_launch(self, do_launch: bool) -> bool:
        """Check if automatic launch should occur after update."""
        has_auto_launch = (
            self._config.launcher.auto_launch
            or self._config.launcher.auto_launch_enable
        )
        is_enabled = (
            self._config.launcher.enabled or self._config.launcher.auto_launch_enable
        )
        has_executable = bool(self._config.launcher.executable)
        return has_auto_launch and is_enabled and has_executable and do_launch


    def _serialize_packages(self, statuses: list[PackageStatus]) -> None:
        """Convert package statuses to JSON-friendly format and push to frontend."""
        pkg_data = [
            {
                "name": s.name,
                "installed": s.installed,
                "available": s.available,
                "status": s.status,
            }
            for s in statuses
        ]
        self._push_packages(pkg_data)

    def _push_log(self, level: str, message: str) -> None:
        if self._window is None:
            return
        ts = datetime.now().strftime("%H:%M:%S")
        payload = json.dumps({"level": level, "message": message, "timestamp": ts})
        self._window.evaluate_js(f"window.addLogLine({payload})")

    def _push_packages(self, packages: list[dict[str, str | None]]) -> None:
        if self._window is None:
            return
        payload = json.dumps(packages)
        self._window.evaluate_js(f"window.updatePackages({payload})")

    def get_config(self) -> dict[str, object]:
        return {
            "launcher_enabled": self._config.launcher.enabled,
            "launcher_executable": self._config.launcher.executable,
            "auto_launch": self._config.launcher.auto_launch,
            "auto_update": self._config.launcher.auto_update,
            "auto_launch_enable": self._config.launcher.auto_launch_enable,
            "auto_update_enable": self._config.launcher.auto_update_enable,
            "theme": self._config.gui.theme,
        }

    def get_packages(self) -> list[dict[str, str | None]]:
        if self._python_exe is None:
            return []
        installed = get_installed_versions_batch(
            self._python_exe, self._config.packages
        )
        return [
            {
                "name": pkg,
                "installed": ver,
                "available": None,
                "status": STATUS_UP_TO_DATE if ver else STATUS_NOT_INSTALLED,
            }
            for pkg, ver in installed.items()
        ]

    def get_versions(self, package_name: str) -> list[str]:
        """
        Get all available versions for a package from the source directory.

        Args:
            package_name: Package name (e.g., "test-matrix")

        Returns:
            List of version strings sorted newest-first
        """
        versions = get_all_versions(package_name, self._source_path())
        return versions

    def check_for_updates(self) -> None:
        self._run_with_lock(self._do_scan)

    def _drain_state_notes(self) -> None:
        """Report, once, what the state file contributed to this session."""
        for note in self._state_notes:
            self._push_log("info", note)
        self._state_notes = []

    def _do_scan(self) -> None:
        self._drain_state_notes()
        if self._config.parse_error and not self._config_error_logged:
            self._config_error_logged = True
            self._push_log("error", self._config.parse_error)
        if self._python_exe is None:
            self._push_log(
                "error",
                "找不到 venv：請在上方「目標資料夾」指定專案，或用 "
                "updater_gui.exe --project <專案資料夾> 啟動",
            )
            return

        if self._auto_update_disabled:
            self._push_log(
                "info",
                "Auto-update disabled for this session (older version installed) — scan continues",
            )

        self._push_log("info", f"Test Matrix Updater GUI (v{get_version()})")
        source = self._source_resolution(probe=True)
        self._push_log("info", f"packages 來源: {source.path} ({source.origin})")
        if source.error:
            # scan_packages() returns {} for an unreadable source, which would
            # otherwise look like "nothing to update" (offline UNC share).
            self._push_log(
                "error",
                f"{source.error} — 讀不到任何 .whl，請變更上方 packages 來源",
            )
        print(f"[DEBUG] Starting scan. Source: {source.path} ({source.origin})")
        available = scan_packages(source.path)
        print(f"[DEBUG] Available packages in source: {list(available.keys())}")

        installed_versions = get_installed_versions_batch(
            self._python_exe, self._config.packages
        )
        statuses = check_updates(self._config.packages, installed_versions, available)

        self._serialize_packages(statuses)

        updatable = [s.name for s in statuses if s.status in UPDATABLE_STATUSES]
        print(f"[DEBUG] Updatable packages found: {updatable}")

        has_updates = len(updatable) > 0
        if self._window:
            print(
                f"[DEBUG] Calling window.onScanComplete({has_updates}, "
                f"autoUpdateDisabled={self._auto_update_disabled})"
            )
            self._window.evaluate_js(
                f"window.onScanComplete("
                f"{json.dumps(has_updates)}, "
                f"{json.dumps(self._auto_update_disabled)})"
            )

    def run_update(self) -> None:
        self._run_with_lock(self._do_update)

    def _do_update(self) -> None:
        if self._python_exe is None:
            self._push_log("error", "No venv Python found")
            return

        print("[DEBUG] Starting update process (_do_update)...")
        self._push_log("info", f"Scanning source: {self._config.source}")
        available = scan_packages(self._source_path())

        if not available:
            print("[DEBUG] Update failed: No whl files found")
            self._push_log("error", "No .whl files found in source path")
            if self._window:
                summary = json.dumps(
                    {"total": 0, "updated": 0, "failed": 0, "should_launch": False}
                )
                self._window.evaluate_js(f"window.onUpdateComplete({summary})")
            return

        self._push_log("info", f"Found {len(available)} package(s) in source")

        installed_versions = get_installed_versions_batch(
            self._python_exe, self._config.packages
        )
        statuses = check_updates(self._config.packages, installed_versions, available)

        self._serialize_packages(statuses)

        to_update = [s for s in statuses if s.status in UPDATABLE_STATUSES]
        self._push_log("info", f"{len(to_update)} package(s) to update")

        result = install_updates(statuses, self._python_exe, on_progress=self._push_log)

        # Refresh package statuses to reflect updates in GUI
        available_now = scan_packages(self._source_path())
        installed_now = get_installed_versions_batch(
            self._python_exe, self._config.packages
        )
        statuses_now = check_updates(
            self._config.packages, installed_now, available_now
        )
        self._serialize_packages(statuses_now)

        # Regular update always installs the latest — re-enable auto-update.
        self._auto_update_disabled = False
        print("[DEBUG] _do_update complete — auto_update_disabled reset to False")

        do_launch = should_launch(self._config.launcher.mode, result)
        should_launch_final = (
            do_launch
            and (
                self._config.launcher.enabled
                or self._config.launcher.auto_launch_enable
            )
            and bool(self._config.launcher.executable)
        )
        summary = json.dumps(
            {
                "total": result.total,
                "updated": result.updated,
                "failed": result.failed,
                "should_launch": should_launch_final,
            }
        )
        if self._window:
            self._window.evaluate_js(f"window.onUpdateComplete({summary})")

        if self._should_auto_launch(do_launch):
            self._push_log("info", "Auto-launching application...")
            self._do_launch()

    def install_versioned_package(
        self, package_name: str, version: str
    ) -> dict[str, object]:
        """
        Install a specific version of a package, disabling auto-update for the session.

        Sets _auto_update_disabled to True so subsequent scan cycles do not overwrite
        the pinned version.  The actual installation runs on a background thread via
        _run_with_lock (mirrors the run_update pattern).

        Args:
            package_name: The package to install (e.g., "test-matrix").
            version: The exact version string to install (e.g., "1.4.2").

        Returns:
            {"success": True, "error": None} when the background job starts, or
            {"success": False, "error": "<reason>"} for immediate validation failures.
        """
        if self._python_exe is None:
            return {"success": False, "error": "No venv Python found"}

        # Only suppress auto-update when installing an older (non-latest) version.
        all_versions = get_all_versions(package_name, self._source_path())
        is_downgrade = bool(all_versions) and Version(version) < Version(all_versions[0])
        print(
            f"[DEBUG] install_versioned_package: version={version}, "
            f"latest={all_versions[0] if all_versions else 'n/a'}, "
            f"is_downgrade={is_downgrade}"
        )
        if is_downgrade:
            self._auto_update_disabled = True
            self._push_log(
                "info",
                f"Auto-update disabled for this session (downgrade to {version})",
            )
        else:
            self._auto_update_disabled = False
            self._push_log("info", f"Installing {package_name}=={version} (latest)")

        def _do_install() -> None:
            if self._python_exe is None:
                self._push_log("error", "No venv Python found")
                return

            self._push_log("info", f"Installing {package_name}=={version}...")

            # Build a PackageStatus for the target package so install_updates
            # knows what to operate on.  We scan for the current installed version
            # to populate the status faithfully.
            available = scan_packages(self._source_path())
            installed_versions = get_installed_versions_batch(
                self._python_exe, self._config.packages
            )
            statuses = check_updates(
                self._config.packages, installed_versions, available
            )

            # Find the matching status; fall back to a synthetic entry if the
            # package is somehow not listed in config packages.
            target_statuses = [s for s in statuses if s.name == package_name]
            if not target_statuses:
                self._push_log(
                    "debug",
                    f"{package_name}: not found in config packages, using synthetic status",
                )
                target_statuses = [
                    PackageStatus(
                        name=package_name,
                        installed=installed_versions.get(package_name),
                        available=version,
                        status=STATUS_UPDATE_AVAILABLE,
                    )
                ]

            for s in target_statuses:
                self._push_log(
                    "debug",
                    f"{s.name}: current status={s.status}, installed={s.installed}, target={version}",
                )

            result = install_updates(
                target_statuses,
                self._python_exe,
                on_progress=self._push_log,
                target_version=version,
                source_path=self._source_path(),
            )

            # Refresh package status in the GUI after installation
            available_now = scan_packages(self._source_path())
            installed_now = get_installed_versions_batch(
                self._python_exe, self._config.packages
            )
            statuses_now = check_updates(
                self._config.packages, installed_now, available_now
            )
            self._serialize_packages(statuses_now)

            summary = {
                "total": result.total,
                "updated": result.updated,
                "failed": result.failed,
                "success": result.all_success,
            }
            if self._window:
                self._window.evaluate_js(
                    f"window.onVersionedInstallComplete({json.dumps(summary)})"
                )

        self._run_with_lock(_do_install)
        return {"success": True, "error": None}

    def launch_app(self) -> dict[str, object]:
        return self._do_launch()

    def _do_launch(self) -> dict[str, object]:
        if not self._python_exe:
            return {"success": False, "error": "No venv Python found", "pid": None}
        try:
            proc = launch_executable(self._config, self._python_exe)
            self._push_log("success", f"Launched (PID: {proc.pid})")
            return {"success": True, "error": None, "pid": proc.pid}
        except LauncherError as exc:
            self._push_log("error", f"Launch failed: {exc}")
            return {"success": False, "error": str(exc), "pid": None}


def main() -> None:
    # Enable DPI awareness (Level 2: Per Monitor DPI Aware)
    if sys.platform == "win32":
        import ctypes

        try:
            # Try SetProcessDpiAwareness (Level 2)
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

    parser = argparse.ArgumentParser(description="Test Matrix Updater GUI")
    parser.add_argument("--dev", action="store_true", help="Load from Vite dev server")
    parser.add_argument(
        "--project",
        default=None,
        help="Folder to update (its venv and updater.toml).  The exe itself "
        "may live anywhere; the GUI can also switch folders at runtime.",
    )
    args = parser.parse_args()

    # sys.argv[0] is the exe (frozen) or this script (dev); its parent is the
    # directory the legacy find_config()/find_venv_python() anchored on.
    exe_dir = Path(sys.argv[0]).resolve().parent

    # Last folders chosen in the GUI (updater_state.json).  Read-only unless the
    # user picks again; `--project` still wins over the saved value (spec 3.3.3).
    state, state_file, state_error = load_saved_state(exe_dir)
    state_notes: list[str] = []
    if state_error:
        state_notes.append(f"狀態檔問題: {state_error}")
    project_arg = args.project
    if project_arg is None and usable(state.project):
        project_arg = state.project
        state_notes.append(f"沿用上次選擇的專案資料夾: {project_arg}")
    elif state.project and not usable(state.project):
        state_notes.append(f"上次選擇的專案不存在，改用自動解析: {state.project}")
    if state.source and not usable(state.source):
        state_notes.append(f"上次選擇的 packages 不存在，改用自動解析: {state.source}")

    try:
        target = resolve_target(project_arg, exe_dir, Path.cwd())
    except TargetError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(2)

    print(f"[DEBUG] {target.describe()}")
    api = Api(
        target.config,
        target.python_exe,
        target,
        state=state,
        state_file=state_file,
        state_notes=state_notes,
    )

    if args.dev:
        url = "http://localhost:15173"
    else:
        frontend_dist = Path(__file__).parent / "frontend" / "dist" / "index.html"
        if not frontend_dist.exists():
            print(
                "[ERROR] Frontend not built. Run: "
                f"cd {frontend_dist.parent.parent} && npm run build"
            )
            sys.exit(1)
        url = str(frontend_dist)

    height, screen = window_geometry()
    if screen:
        print(
            f"[DEBUG] Screen: {screen.width}x{screen.height} (scale {screen.scale}), "
            f"window {DEFAULT_WINDOW_WIDTH}x{height}, placement: centered on screen"
        )
    else:
        print(f"[DEBUG] Calculated window height: {height}")

    # No x/y on purpose: passing `screen` lets pywebview place the window itself
    # (winforms.py centers it in logical pixels, then scales by DPI).  Handing it
    # our own x/y would be applied on top of that and lands off-center on scaled
    # displays; without either it falls back to WinForms CenterScreen.
    window = webview.create_window(
        "Test Matrix Updater",
        url=url,
        js_api=api,
        width=DEFAULT_WINDOW_WIDTH,
        height=height,
        screen=screen,
        min_size=MIN_WINDOW_SIZE,
    )
    assert window is not None, "webview.create_window returned None"
    api._set_window(window)

    webview.start()


if __name__ == "__main__":
    main()
