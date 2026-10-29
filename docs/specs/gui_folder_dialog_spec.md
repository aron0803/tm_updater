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

## 3.1 目標列版面（TargetBar 版面契約）

三條路徑（專案 / venv / source）**各自一列**，不得在同一列相擠（1.5.0 的單列 flex 排版在
路徑很長時會糊在一起）：

```
.target-bar  : grid，直欄 = [資訊列 | 控制列]
.target-row  : grid，直欄 = [56px 標籤 | minmax(0,1fr) 值]
               每列一笔：專案: / venv: / source: / 設定:
```

- 值一律用完整路徑 + `text-overflow: ellipsis` + `title` 顯示全路徑（不再用 `shorten()` 截字）。
- 控制列兩組：**專案**（input + 套用 + 瀏覽…）與 **packages 來源**（input + 套用 + 瀏覽…）。
- 視窗預設寬 1200、`min_size=(900, 420)`；在最小寬度下三列仍不得重疊。

## 3.2 `Api.set_source()` / `Api.choose_source_folder()` 契約

來源（whl / packages）可在執行期改，解析優先序見 `target_resolution_spec.md` §6 第 1 點。

| 欄位 | 型別 | 說明 |
|---|---|---|
| `error` | str \| None | 路徑不存在或不是目錄時的訊息（此时來源**不-switch**） |
| `target` | dict | 現況，含 `source` / `source_origin` / `source_error` |

- `choose_source_folder()` 另帶 `cancelled` / `reason`，語意同 §2。
- 成功換來源後前端必須重掃（`reloadTarget()`），因為可用版本清單來自 source。

## 3.3 執行期狀態存檔（`updater_state.json`）

目標專案與 packages 來源的**執行期選擇**會保存，重啟後沿用；`updater.toml` 仍是部署設定，
兩者分工：

| 檔案 | 職責 | 誰寫 |
|---|---|---|
| `updater.toml` | 部署/團隊設定（packages、venv 名稱、launcher、source） | 人工 / IT |
| `updater_state.json` | 這台機器上次選的 `project` / `source` | GUI 自動 |

Schema（`schema` 欄位是版號，之後結構變更要遞增）：

```json
{"schema": 1, "project": "C:\\Test_Matrix", "source": "C:\\...\\packages", "updated_at": "ISO8601"}
```

位置與規則：

1. 首選 **exe 同層** `updater_state.json`（可攜式部署跟著資料夾走）；寫入失敗（網路碟唯讀等）
   → 退回 `%LOCALAPPDATA%\Test Matrix\Updater\updater_state.json`，並寫 warning log。
2. 寫入採 **tmp + `os.replace`**（不可被半截檔案破壞）；解析失敗視同無狀態，保留舊檔並記錄。
3. 載入時機：`main()` 在解析 target 前讀取。
   - `--project` / `--source` 給定時**忽略**狀態（參數最大，見 `target_resolution_spec.md` §3、§6）。
   - 狀態里的目錄已不存在 → 忽略該欄位、寫 log，不要讓 GUI 卡在壞路徑上。
4. **只有使用者明確選擇時才寫**（`set_target` / `set_source` 成功後）；啟動時的自動解析結果
   **不寫檔** → 沒動過 packages 的使用者仍然吃「toml → **exe 上一層含 `.whl` 的目錄** → 內建」自動鏈。
5. `clear_target()` / `clear_source()`：清掉對應欄位（寫回檔）並立即回到自動解析結果；
   GUI 需有「還原自動」入口（`store.target.project_saved` / `source_saved` 為 True 時才可用）。
6. **寫入欄位 = 明確選擇，不是解析結果**：`_persist_state()` 只寫
   `project_override` / `source_override`。`clear_target()` 之後檔案裡的 `project` 變回
   `null`，因此下次啟動仍走 §3 自動鏈（不會把某次自動解析到的路徑凍結進檔）。
7. `--project` / `--source` 只影響這次啟動，**不刪除**已存的選擇（下次雙擊 exe 仍沿用）。
8. `get_target()` 另帶 `project_saved` / `source_saved`（bool）：表示該欄位目前來自
   `updater_state.json`（或本次手動選擇），前端據此決定「還原自動」按鈕是否可點。
9. `main()` 讀檔後的事（沿用、或目錄已不存在而忽略）會以 `state_notes` 帶進 GUI log
   （第一次 scan 時輸出，與 config parse error 同一機制）。

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
- `tests/test_state.py`（§3.3 契約）：缺檔→空狀態不報錯、dirty JSON/schema 不符→空狀態＋錯誤訊息、
  `save_state` 原子寫入且不留下 `.tmp` 残檔、`state_files()` 順序、`load_saved_state()` 在 exe 層無檔時
  讀 `%LOCALAPPDATA%` 副本、`usable()` 對不存在路徑回 False。
- `tests/test_gui.py`：`clear_target()` 後狀態檔 `project` 為 `null`（自動解析結果不被凍結）、
  `set_source()` 後重啟（重建 Api）仍沿用該來源、`set_target()` 只寫 project 不影響 source。
