# Specification: Package Context Menu & Same-Version Reinstall

## 1. 概述 (Overview)
本規格定義 Test Matrix Updater GUI 套件清單之右鍵捷徑功能（安裝 / 重新安裝 / 移除）以及同版本號重新安裝的核心與前端行為契約。

---

## 2. 右鍵選單 UX 契約 (Context Menu UX Contract)

### 2.1 觸發與定位
- 觸發事件：在 `PackageTable.vue` 的 `.table-row` 元素上觸發 `@contextmenu.prevent`。
- 定位計算：以滑鼠游標之 `clientX`, `clientY` 為基準，並限制在視窗邊界內（避免超出螢幕邊緣）。
- 關閉時機：
  1. 點擊選單內部任一可用選項（執行動作並關閉）。
  2. 點擊選單外任何區域（`window.addEventListener('click')`）。
  3. 按下鍵盤 `Escape` 鍵。
  4. 列表滾動時自動關閉。

### 2.2 選單項目與狀態
1. **安裝 / 重新安裝 (Install / Reinstall)**：
   - 標籤：
     - 若 `pkg.installed` 為空或 falsy：顯示 `安裝 (Install)`。
     - 若 `pkg.installed` 存在：顯示 `重新安裝 (Reinstall)`。
   - 動作：
     - 若來源中無可用版本（`!versionsMap[pkg.name]?.length`）：選項反灰停用。
     - 點擊後設定 `store.pendingVersionInstall`（版本預設為當前下拉選中之版本或已安裝版本），開啟 `VersionConfirmModal`。
2. **移除 (Uninstall)**：
   - 標籤：`移除 (Uninstall)`（以警示紅字標記）。
   - 狀態：若 `!pkg.installed` 則反灰停用或隱藏。
   - 動作：點擊後設定 `store.pendingUninstall = { packageName, installedVersion }`，開啟 `UninstallConfirmModal`。

---

## 3. 前端彈窗契約 (Confirmation Modals)

### 3.1 VersionConfirmModal (支援同版本 Reinstall)
- 標題：
  - 若 `version === installedVersion`：顯示 `Reinstall Version?`。
  - 若 `version !== installedVersion`：顯示 `Install Different Version?`。
- 內文：
  - 若同版本：`${packageName}: Reinstall v${version} (will clean uninstall and reinstall from source wheel)`。
- 按鈕：
  - `Cancel`：關閉彈窗，清空 `pendingVersionInstall`。
  - `Confirm`：呼叫 `pywebview.api.install_versioned_package(packageName, version)`。

### 3.2 UninstallConfirmModal
- 標題：`Uninstall Package?`
- 內文：`確定要移除 ${packageName} (v${installedVersion}) 嗎？此操作將會從虛擬環境中完全解除安裝該套件。`
- 按鈕：
  - `Cancel`：關閉彈窗，清空 `pendingUninstall`。
  - `Uninstall`（危險紅色按鈕）：呼叫 `pywebview.api.uninstall_package(packageName)`。

---

## 4. 後端 API 契約 (Backend API Contract)

### 4.1 `Api.uninstall_package(package_name: str) -> dict[str, object]`
- **執行方式**：在 `_run_with_lock` 保護下，於背景執行緒調用 `core.uninstall_package`。
- **輸入**：`package_name: str`（套件名稱，例如 `"test-matrix"`）。
- **輸出**：`{"success": True, "error": None}` 或 `{"success": False, "error": "<reason>"}`。
- **背景通知**：
  - 完成時調用 `window.onUninstallComplete({"packageName": package_name, "success": bool, "error": str | None})`。
  - 自動重新讀取 `get_installed_versions_batch` 並推播最新狀態至前端。

### 4.2 `Api.install_versioned_package(package_name: str, version: str)`
- **同版本重新安裝相容**：
  - 當 `version == installed_version` 時，允許執行，不再因判定相同而略過。
  - `is_downgrade` 計算：若 `version < latest` 則 `_auto_update_disabled = True`；若 `version == latest` 則 `_auto_update_disabled = False`。

---

## 5. 核心模組契約 (`updater.core`)

### 5.1 `uninstall_package(package_name: str, python_exe: Path, on_progress: ProgressCallback | None = None) -> tuple[bool, str]`
- 執行指令：
  ```cmd
  <python_exe> -m pip uninstall -y --no-input <package_name>
  ```
- 逾時限制：120 秒。
- 回傳：`(True, "")` 或 `(False, "<error message>")`。
- 日誌通知：開始、結束耗時、逾時及失敗詳細說明。

### 5.2 `install_updates(statuses, python_exe, target_version, ...)`
- **支援同版本強制重裝**：
  ```python
  if target_version:
      updated_statuses = []
      for s in statuses:
          if s.status == STATUS_UP_TO_DATE:
              # 無論 s.installed 是否等於 target_version，一律轉換為 STATUS_VERSION_SPECIFIED
              updated_statuses.append(replace(s, status=STATUS_VERSION_SPECIFIED))
          else:
              updated_statuses.append(s)
  ```
  確保 `to_update` 在同版本重新安裝時不會被過濾為空串列。
