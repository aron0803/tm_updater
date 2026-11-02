# Current Active Intentions

## [2026-11-02 14:35] 任務意圖：對話框立即關閉與背景轉圈、套件右鍵選單（移除/安裝）及同版重新安裝 [Status: In-Progress]
- **核心目標 (Objective)**：
  - **改善降版/安裝互動體驗（即時反饋）**：解決使用者點擊「Install」後對話框卡在畫面上看似當掉的問題；點擊確認後**對話框立即消失**，背景處理期間該套件列與動作面板顯示**明顯的轉圈載入動畫 (Spinner)**，右側 Console 能完整無阻礙地顯示分段即時進度日誌。
  - **套件右鍵選單 (Context Menu)**：在套件清單列上按右鍵，彈出快捷選單提供「安裝 / 重新安裝 (Reinstall)」與「移除 (Uninstall)」。
  - **同版本號重新安裝 (Reinstall)**：支援同一版號測試時覆蓋重裝（先卸載、再由本地 wheel 重新安裝）。
  - **套件安全移除 (Uninstall)**：提供移除確認對話框，確認後立即關閉對話框，背景轉圈執行 pip uninstall，成功後自動更新狀態為未安裝。
- **驗收標準 (Acceptance Criteria)**：
  1. **確認後對話框立即關閉**：
     - 點擊 `VersionConfirmModal` 的 Install 或 `UninstallConfirmModal` 的 Uninstall 後，對話框立即關閉（`showModal = false`），絕不滯留於畫面上。
  2. **背景轉圈與狀態指示 (Loading Spinner)**：
     - 背景執行期間（`store.isUpdating`）：
       - 當前操作的套件列狀態欄顯示旋轉 Spinner 與「處理中...」文字，整列呈現動態更新效果。
       - `ActionPanel` 按鈕同步顯示 Spinner 與禁用狀態防重複點擊。
       - 右側 Log Console 即時滾動顯示兩階段執行紀錄（1/2 移除、2/2 安裝、耗時）。
     - 操作完成時（`onVersionedInstallComplete` / `onUninstallComplete`）自動停止轉圈，更新套件列表。
  3. **右鍵選單 (Context Menu)**：
     - 在 `PackageTable` 套件列右鍵點擊，游標處彈出選單（含「安裝/重新安裝」、「移除」）。
     - 點選任一項目、點擊選單外或按 ESC 鍵立即關閉選單。
     - 套件未安裝時「移除」項目反灰禁用。
  4. **後端 API 與解除安裝契約**：
     - `Api.uninstall_package(package_name)` 透過背景鎖執行並推播 `onUninstallComplete`。
     - `core.install_updates` 支援 `reinstall=True`，同版本覆蓋不會被判定為無需更新。
     - 卸載與安裝全程強制 `--no-index --no-input` 徹底離線。
- **範疇邊界 (In-Scope & Out-of-Scope)**：
  - 涵蓋範圍：`src/updater/core.py`、`src/updater/gui/app.py`、前端 `PackageTable.vue`、`VersionConfirmModal.vue`、`UninstallConfirmModal.vue`、`ActionPanel.vue`、`main.js`。
  - 本次不做 (Non-Goals)：不修改既有批次全量更新按鈕的排程邏輯。
