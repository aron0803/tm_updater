# Specification: Package Context Menu, Immediate Modal Dismissal & Reinstall

## 1. 概述 (Overview)
本規格定義：
1. 彈窗確認後立即關閉（無感延遲）與背景處理時的微型 Spinner / 載入狀態指示。
2. 套件清單之右鍵快捷選單（安裝 / 重新安裝 / 移除）。
3. 同版本號強制重新安裝 (Reinstall) 機制。
4. 套件移除 (Uninstall) 之獨立 API 與確認流程。

---

## 2. 彈窗與背景載入體驗契約 (Modal & Background Loading Contract)

### 2.1 彈窗立即關閉
- 使用者在 `VersionConfirmModal` 點擊「Install / Reinstall」，或在 `UninstallConfirmModal` 點擊「Uninstall」時：
  1. **立即關閉彈窗**：設定 `store.showVersionModal = false` 或 `store.showUninstallModal = false`。
  2. **註冊作用中操作**：
     `store.activeOperation = { packageName: pkg.name, type: 'install' | 'reinstall' | 'uninstall', version: ... }`。
  3. **進入更新狀態**：設定 `store.isUpdating = true`。
  4. 視窗焦點回到主介面，右側 Console 清楚展示後端日誌。

### 2.2 背景載入指示 (In-Row Spinner)
- 當 `store.isUpdating` 且 `store.activeOperation?.packageName === pkg.name`：
  - 套件列的 `col-status` 顯示藍色轉圈 Spinner (`.spinner-mini`) 與動態文字：
    - `type === 'uninstall'`：`移除中... (Uninstalling...)`
    - `type === 'reinstall'`：`重新安裝中... (Reinstalling vX.X.X...)`
    - `type === 'install'`：`安裝中... (Installing vX.X.X...)`
  - 該列背景呈現平滑呼吸效果（`.row-operating`）。
- 操作完成時：
  - `window.onVersionedInstallComplete` 或 `window.onUninstallComplete` 被調用。
  - 清空 `store.activeOperation = null`，設定 `store.isUpdating = false`。
  - 套件列更新為最新狀態，停止轉圈。

---

## 3. 右鍵選單 UX 契約 (Context Menu UX Contract)

### 3.1 觸發與定位
- 觸發：在 `PackageTable.vue` 的 `.table-row` 上監聽 `@contextmenu.prevent`。
- 定位：取得 `event.clientX`, `event.clientY`，並考量選單寬高（clamp 於視窗內，防溢出）。
- 關閉條件：點擊選單項目、點擊選單外部、滾動滑鼠或按下 `Escape`。

### 3.2 選單項目
1. **安裝 / 重新安裝 (Install / Reinstall)**：
   - 套件未安裝（`!pkg.installed`）：顯示 `安裝 (Install)`。
   - 套件已安裝：顯示 `重新安裝 (Reinstall)`。
   - 點擊後設定 `pendingVersionInstall` 並打開 `VersionConfirmModal`。
2. **移除 (Uninstall)**：
   - 標籤：`移除 (Uninstall)`（紅字危險樣式）。
   - 狀態：若套件未安裝（`!pkg.installed`），項目反灰禁用（`disabled`）。
   - 點擊後設定 `pendingUninstall` 並打開 `UninstallConfirmModal`。

---

## 4. 後端 API 契約 (Backend API Contract)

### 4.1 `Api.uninstall_package(package_name: str) -> dict[str, object]`
- 在 `_run_with_lock` 保護下執行。
- 呼叫 `core.uninstall_package(package_name, python_exe, on_progress)`。
- 完成後重新整理已安裝套件資訊並推播 `window.onUninstallComplete({packageName, success, error})`。

### 4.2 `Api.install_versioned_package(package_name: str, version: str) -> dict[str, object]`
- 呼叫 `core.install_updates(..., target_version=version, reinstall=True)`。
- 完成後推播 `window.onVersionedInstallComplete(summary)`。

---

## 5. 核心模組契約 (`updater.core`)

### 5.1 `uninstall_package(package_name, python_exe, on_progress) -> tuple[bool, str]`
- 執行 `pip uninstall -y --no-input <package_name>`，逾時 120 秒，全離線執行。

### 5.2 `install_updates(..., target_version, reinstall=False)`
- 當 `reinstall=True` 時，即使 `s.installed == target_version` 仍強制將狀態轉為 `STATUS_VERSION_SPECIFIED` 進入更新佇列。
