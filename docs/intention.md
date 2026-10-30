# Current Active Intentions

## [2026-10-30 17:35] 任務意圖：修復指定版本與降版（Downgrade）之 UI 觸發與安裝互動 [Status: In-Progress]
- **核心目標 (Objective)**：
  - 解決使用者在 GUI 介面中欲安裝指定版本（降版）時，畫面上找不到 Install 按鈕、且下拉選單因預選舊版未觸發 `@change` 導致無法彈出確認對話框的問題。
  - 提供直觀、明確的單項安裝與批次指定版本安裝機制，讓使用者能順利執行降版與指定版本安裝。
- **驗收標準 (Acceptance Criteria)**：
  1. 當套件的所選版本與已安裝版本不同（`Version specified` / 降版狀態）時：
     - 在套件列直接提供明確的「Install」按鈕，點擊立即彈出 `VersionConfirmModal` 確認視窗。
     - 點擊紫色的狀態文字或重新選取下拉選單時，亦能可靠彈出確認視窗。
  2. 若有多個套件處於指定版本 / 降版狀態，ActionPanel 動作面板能夠感知並提供明確的引導或安裝入口。
  3. 確認安裝後，正常呼叫後端 `install_versioned_package` 執行降版，並正確觸發 Session 級別的自動更新抑制（避免覆蓋），安裝完成後刷新套件狀態。
  4. 既有單元測試與前端測試維持通過或更新對應測試案例。
- **範疇邊界 (In-Scope & Out-of-Scope)**：
  - 涵蓋範圍：`PackageTable.vue`、`ActionPanel.vue`、`VersionConfirmModal.vue`、`main.js` 與相關測試、重新建置前端 dist 及更新 exe。
  - 本次不做 (Non-Goals)：不修改後端 core pip 安裝協議核心邏輯（後端 `install_versioned_package` 已具備完備功能）。
