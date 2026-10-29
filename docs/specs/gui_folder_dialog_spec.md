# 規格：GUI 目標資料夾選取 (Folder Dialog Contract) v1

定義 GUI 端「選擇要更新的資料夾」的後端/前端契約與 pywebview 相依契約。
目的：`target_resolution_spec.md` 已允許 updater 放在任何位置，那麼**換資料夾**這個動作本身
也必須有明確契約 — 包含「對話框無法使用」時的降級路徑，避免按了沒反應（ silent no-op ）。

實作模組：
- `src/updater/gui/dialog.py` — 對話框相容層（純相依注入，window 由呼叫端傳入，可 mock）
- `src/updater/gui/app.py:Api.set_target() / Api.choose_target_folder() / Api.get_target()`
- `src/updater/gui/frontend/src/components/TargetBar.vue`

## 1. pywebview 相依契約（本次 bug 的根因）

| 項目 | 契約 |
|---|---|
| 版本 | `pywebview>=6.2,<7`（`pyproject.toml` 必須鎖上限；未鎖時 6.x 的 API 變動會直接打進成品） |
| 建立對話框 | **只能**用 `Window.create_file_dialog(dialog_type, directory=...)` |
| 對話框型別 | `webview.FileDialog.FOLDER`（int 值 20） |
| 禁止 | `webview.create_file_dialog(...)`（module 層函式，5.x/6.x 已不存在 → `AttributeError`） |
| 禁止 | `webview.FOLDER_DIALOG`（6.x 標記 deprecation，僅作為 `<6.2` 的 fallback 常數讀取） |
| 回傳 | 選中時為 sequence（取第 0 筆）或字串；取消時為 `None` / 空 sequence |
| 前置條件 | 視窗已 `create_window` 並 shown；winforms 實作若找不到 `BrowserView.instances[uid]` 會**靜默回 None**，因此「取消」與「對話框沒起來」在回傳值上不可區分 → 不得把「沒起來」當成成功 |

`dialog.folder_dialog_type()` 是唯一允許讀取 pywebview 對話框常數的地方；回歸測試必須斷言
`app.py` 不出現 module 層 `webview.create_file_dialog`。

## 2. `Api.choose_target_folder()` 輸出契約

一律回傳 dict，欄位固定（不得增減）：

| 欄位 | 型別 | 說明 |
|---|---|---|
| `cancelled` | bool | 使用者取消 **或** 對話框無法使用 |
| `reason` | str \| None | 無法使用時的原因（含例外型別與訊息）；純取消時為 `None` |
| `error` | str \| None | 選了但 `set_target()` 解析失敗時的訊息 |
| `target` | dict | 永遠附帶 `get_target()` 的現況（失敗時 target 維持原值） |

分支：

1. 視窗未就緒 / pywebview 不支援 / 建立對話框丟例外 → `cancelled=True, reason=<訊息>`，
   且後端 `_push_log("error", ...)`（**不可用 debug 等級**，否則現場看不到）。
2. 使用者取消（`None` 或空）→ `cancelled=True, reason=None`。
3. 選了資料夾 → 直接回傳 `set_target(chosen)` 的結果，其契約為
   `{"error": None, "target": {...}}` 或 `{"error": "<TargetError>", "target": {現況}}`。

## 3. `TargetBar.vue` 行為契約

| 後端結果 | 前端行為 |
|---|---|
| `cancelled && !reason` | 靜默：不改變 `store.target`、不顯示錯誤 |
| `cancelled && reason` | 顯示 `無法開啟資料夾對話框：<reason>；請手動輸入路徑後按「套用」`，並寫入 log |
| `error` | 顯示該錯誤，`store.target` 不變 |
| 成功 | 更新 `store.target`、`draft`，並呼叫 `reloadTarget()` 重掃套件 |

任何 `cancelled=True` 都**不得**觸發 `set_target`/`reloadTarget`。

## 4. 邊界條件

- `directory` 不存在：pywebview 會自行退為家目錄，不視為錯誤。
- 選到沒有 venv 的資料夾：走 `set_target` → `get_target().error = "找不到 venv，請指定正確的專案資料夾"`，
  目標仍切換（讓使用者看得见解析結果），不回滾。
- UNC 起點（`\\pnt52\...`）作為 `directory`：winforms 對話框可能不接受，失敗即落入分支 1。

## 5. 驗收（契約測試對應）

- `tests/test_dialog.py`：`folder_dialog_type() == 20`；window mock 回傳 tuple/str/None/丟例外 四種分支；
  `window=None` 與無 `create_file_dialog` 屬性時丟 `DialogUnavailable`。
- `tests/test_gui.py::TestChooseTargetFolder`：三種分支的輸出欄位與 `_push_log` 等級。
- 靜態回歸：`app.py` / `dialog.py` 不得呼叫 module 層 `webview.create_file_dialog`。
- `vitest`：`TargetBar.spec.js` 增加「dialog 無法使用時顯示可操作錯誤」案例。
