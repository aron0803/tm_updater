# Spec: Version Downgrade & Specification UI Interaction

## 1. Background & Problem Statement
Currently, when package wheel files in the `source` directory are older than the installed versions in `.venv` (e.g. `test-matrix` installed: `2.4.9`, source available: `2.4.4`), the frontend displays the status as `⬇ Version specified` in purple.
However:
1. `store.selectedVersions` is pre-populated at startup with `versions[0]` (`2.4.4`). Because the value is already selected in the HTML `<select>`, user clicking on `2.4.4` does NOT emit a DOM `@change` event.
2. The right ActionPanel only calculates `update_available` and `not_installed`. Because installed >= available, `updateCount` is 0. The primary button remains on `↻ Check for Updates`, and no "Install" button appears anywhere.
3. As a result, the user cannot trigger the versioned install or downgrade.

## 2. Specification & Contract

### 2.1 PackageTable UI (`PackageTable.vue`)
- **Row Status**: When `store.selectedVersions[pkg.name]` is present and `store.selectedVersions[pkg.name] !== pkg.installed`, the row is in `version_specified` state.
- **Explicit Action Button**:
  - In `col-status` (or alongside the version selector), when in `version_specified` state, render a distinct action button:
    `<button class="btn-install-mini" :disabled="store.isUpdating" @click.stop="triggerVersionInstall(pkg)">Install</button>`
  - Clicking this button immediately sets `store.pendingVersionInstall = { packageName: pkg.name, version: selected, installedVersion: pkg.installed }` and opens `store.showVersionModal = true`.
- **Select Interaction**:
  - Keep `@change="onVersionSelect(pkg)"`.
  - Also allow clicking the status pill / button to trigger installation.

### 2.2 ActionPanel UX (`ActionPanel.vue`)
- **Awareness of Specified Versions**:
  - Compute `versionSpecifiedCount`:
    `store.packages.filter(p => store.selectedVersions[p.name] && store.selectedVersions[p.name] !== p.installed).length`
  - If `updateCount === 0` and `versionSpecifiedCount > 0`:
    - The primary button text reflects the action: `↻ Install Specified (${versionSpecifiedCount})`.
    - Clicking the primary button prompts confirmation for the specified package(s) or triggers the first/batch specified install.
  - If a single package has a specified version differing from installed, it can trigger `VersionConfirmModal` directly.

### 2.3 Backend & Bridge Contract
- `window.pywebview.api.install_versioned_package(packageName, version)` remains unchanged.
- Backend uninstalls existing version and installs specified version from wheel source using `pip install --find-links=<source> <pkg>==<version>`.
- Session-level `_auto_update_disabled` is set to `True` for downgrades.
