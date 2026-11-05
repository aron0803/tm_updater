# Specification: Offline Source Decoupling (PNT52 Elimination)

## 1. 概述 (Overview)
本規格定義完全離線環境下，移除所有內建之外部/網路碟（`\\pnt52\...`）依賴與殘留日誌引用，確保系統預設完全運作於本機目錄（如 `packages`、`whls`），絕不對外發起任何 SMB / UNC 探測。

---

## 2. 根因分析 (Root Causes)

1. **GUI 執行更新時日誌來源變數引用錯誤**：
   - 檔案：`src/updater/gui/app.py`
   - 現況：`_do_update()` 中使用 `self._push_log("info", f"Scanning source: {self._config.source}")`。
   - 問題：即便使用者在 GUI 選擇了 `D:\Test_Matrix\whls` 或自動偵測到本地 sibling，`self._config.source` 仍為 `updater.toml` 載入時的原始字串（`\\pnt52\...`），導致日誌噴出 `Scanning source: \\pnt52\...`。
   - 修正：改用 `self._source_path()`。

2. **內建預設值硬編碼外部網路 UNC**：
   - 檔案：`src/updater/config.py`
   - 現況：`_BUILTIN_SOURCE = r"\\pnt52\研發本部_技術服務處\技術服務處\DS-TA\Test_Matrix\packages"`。
   - 問題：當找不到設定檔或未指定 source 時，退回 `_BUILTIN_SOURCE`，觸發 Windows SMB 廣播探測導致 2~3 秒網路連線逾時卡頓與錯誤警示。
   - 修正：預設改為本地目錄名稱 `"packages"`。

3. **預設設定檔內含 `pnt52`**：
   - 檔案：`updater.toml`、`src/updater/gui/updater.toml`、`dist/onefile/updater.toml`、`dist/pyinstaller/updater_gui/updater.toml`
   - 現況：`source = '\\pnt52\研發本部_技術服務處\技術服務處\DS-TA\Test_Matrix\packages'`。
   - 修正：改為本地 `"whls"` 或 `"packages"`。

---

## 3. 變更契約 (Contract Changes)

### 3.1 `src/updater/config.py`
- `_BUILTIN_SOURCE`:
  ```python
  _BUILTIN_SOURCE = "packages"
  ```

### 3.2 `src/updater/gui/app.py`
- `_do_update`:
  ```python
  self._push_log("info", f"Scanning source: {self._source_path()}")
  ```

### 3.3 `updater.toml` (包含發佈目錄)
- `[updater]` 區段中的 `source`：
  ```toml
  source = "whls"
  ```
  （使用者現場目錄名為 `whls`，設定為 `whls` 或 `packages`，可被自動解析為專案/exe 同層或相對路徑）。
