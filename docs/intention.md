# Current Active Intentions

## [2026-11-05 13:55] 任務意圖：徹底清除 PNT52 殘留引用與日誌錯誤，保證純本地/離線運作 [Status: In-Progress]
- **核心目標 (Objective)**：
  - 解決使用者在完全離線/內網環境下更新 whl 時，仍在 Log Console 或設定中看到檢查 `\\pnt52\...` 網路碟的問題。
  - 根除日誌顯示錯誤：修復 `app.py:_do_update` 誤用 `self._config.source` 印出舊設定而非當前生效之 `_source_path()`。
  - 徹底斷開 PNT52 網路依賴：將 `_BUILTIN_SOURCE` 與 `updater.toml` 預設值調整為本地目錄（`"packages"` 或 `"whls"`），避免在未設定來源時自動退回並嘗試連線 `\\pnt52` 造成 Windows SMB 逾時卡頓。
- **驗收標準 (Acceptance Criteria)**：
  1. `app.py:_do_update` 掃描日誌必須顯示 `self._source_path()`，與上方 TargetBar 顯示的生效來源 100% 一致。
  2. `src/updater/config.py` 中的 `_BUILTIN_SOURCE` 移除 `\\pnt52\...`，改為本地目錄預設值（`"packages"`），禁止預設發起任何網路 UNC 探測。
  3. 專案根目錄、`src/updater/gui/updater.toml` 以及發佈目錄 `dist/onefile/updater.toml`、`dist/pyinstaller/updater_gui/updater.toml` 中的 `source` 移除 `pnt52`，改為本地常用之 `"whls"` 或 `"packages"`。
  4. 既有單元測試（包含設定讀取、target 解析）更新對應斷言並全部通過。
  5. 重新以 PyInstaller 打包產出 onedir 與 onefile 執行檔，確認成品無任何 PNT52 殘留連線。
- **範疇邊界 (In-Scope & Out-of-Scope)**：
  - 涵蓋範圍：`src/updater/config.py`、`src/updater/gui/app.py`、`updater.toml`、`dist/*/updater.toml`、單元測試、PyInstaller 建置。
  - 本次不做 (Non-Goals)：不變更 GUI 介面樣式與佈局。
