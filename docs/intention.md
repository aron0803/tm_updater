# Current Active Intentions

## [2026-11-02 14:30] 任務意圖：套件右鍵選單（移除/安裝/重新安裝）與同版本號覆蓋更新支援 [Status: In-Progress]
- **核心目標 (Objective)**：
  - 解決開發者/測試人員在測試同一版本號時無法重複更新的問題（先前受限於 SemVer 比對相等即判定 `Up to date` 而無操作入口）。
  - 提供直覺的桌面端操作體驗：在套件清單上點擊滑鼠右鍵，彈出快捷選單提供「安裝 / 重新安裝 (Reinstall)」與「移除 (Uninstall)」。
  - 支援已安裝套件的一鍵卸載流程（包含二次確認彈窗防誤觸、即時除錯日誌、狀態更新）。
  - 支援相同版本號的強制重新安裝（先卸載既有檔案、再由本地 wheel 重新安裝，確保替換最新測試構建）。
- **驗收標準 (Acceptance Criteria)**：
  1. **右鍵選單 (Context Menu)**：
     - 在 `PackageTable` 任一列點擊右鍵時，阻止原生瀏覽器選單並在游標處彈出自訂選單。
     - 若套件已安裝，顯示「重新安裝 (Reinstall)」與「移除 (Uninstall)」。
     - 若套件未安裝，顯示「安裝 (Install)」且「移除」反灰或隱藏。
     - 點擊選單外部、滾動或按 ESC 鍵即關閉選單。
  2. **同版本號重新安裝 (Reinstall)**：
     - 點選「重新安裝」時彈出確認視窗，明確提示將先移除既有版本再由 wheel 重新安裝。
     - `core.py:install_updates` 當 `target_version == installed` 時，亦能正確納入待更新名單，完成 `pip uninstall` 與 `pip install` 流程。
  3. **套件移除 (Uninstall)**：
     - 點選「移除」時彈出確認視窗，確認後呼叫後端 `uninstall_package`。
     - 解除安裝過程在後端鎖保護下於背景線程執行，輸出階段與耗時 Log。
     - 移除成功後自動刷新套件列表（狀態變更為 `not_installed`），關閉彈窗並解除 UI 鎖定。
  4. **完全離線保障**：
     - 解除安裝與重新安裝過程嚴格維持 `--no-index --no-input`，100% 絕不對外連網。
  5. **自動化測試**：
     - 新增單元測試驗證 `core.py` 卸載功能、同版本重新安裝邏輯與 API 契約。
     - 前端 Vitest 單元測試驗證右鍵選單與移除互動。
- **範疇邊界 (In-Scope & Out-of-Scope)**：
  - 涵蓋範圍：`src/updater/core.py`、`src/updater/gui/app.py`、前端 `PackageTable.vue`、`UninstallConfirmModal.vue`、`VersionConfirmModal.vue`、單元測試、PyInstaller 建置。
  - 本次不做 (Non-Goals)：不修改既有的全量更新「Check for Updates」按鈕邏輯；批次移除不在此次範疇（單一套件操作為主）。
