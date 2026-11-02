# Current Active Intentions

## [2026-11-02 14:10] 任務意圖：降版 Timeout 根因排查與分段診斷日誌強化 [Status: In-Progress]
- **核心目標 (Objective)**：
  - 解決使用者回報在降版時偶發 Timeout（120秒無回應後失敗）的問題。
  - 根絕 pip install 因缺少 `--no-index` 導致嘗試對外連線 PyPI 造成的連線逾時。
  - 在降版過程中導入結構化、分階段（Phased）的除錯與進度日誌（包含階段名稱、執行命令、耗時、wheel 檔案存在性檢驗、詳細錯誤），讓排查問題一目瞭然。
- **驗收標準 (Acceptance Criteria)**：
  1. `pip install` 指定版本時強制加上 `--no-index --no-input`，確保離線環境下絕對不向外部 PyPI 發起連線查詢。
  2. 降版流程清楚區分兩階段輸出 Log：
     - **[1/2 解除安裝]**：輸出即將解除安裝之版本、執行指令，完成時記錄耗時；若逾時或失敗輸出詳細原因。
     - **[2/2 安裝版本]**：驗證來源 wheel 檔案、輸出安裝指令，完成時記錄耗時；若逾時或失敗輸出完整 stdout / stderr。
  3. 各階段獨立處理 `TimeoutExpired`，日誌清楚標註逾時發生在「解除安裝」或「安裝指定版本」階段，並提供可能排查方向（如檔案被其他行程佔用等）。
  4. 單元測試（`test_core.py`、`test_version_downgrade_integration.py`）對 `--no-index` 的斷言全部通過。
- **範疇邊界 (In-Scope & Out-of-Scope)**：
  - 涵蓋範圍：`src/updater/core.py`、`src/updater/gui/app.py`、單元測試、建置腳本與日誌更新。
  - 本次不做 (Non-Goals)：不變更 GUI 介面架構；不縮短既有 120 秒安全超時時間閥值。
