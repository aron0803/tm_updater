# Change Log

### [2026-10-29 12:10] 目錄選擇存檔（updater_state.json）＋「還原自動」，packages 仍自動找上一層

- **對應規格 (Spec/Schema)**：
  - `docs/specs/gui_folder_dialog_spec.md` 新增 §3.3 第 5~9 點：只有**明確選擇**才寫檔（`clear_target()` 後 `project` 變回 `null`，不把自動解析結果凍結）、`--project/--source` 只影響本次啟動不刪已存選擇、`get_target()` 新增 `project_saved` / `source_saved`（bool）、啟動時的狀態判讀以 `state_notes` 進 GUI log
  - §5 驗收新增 `tests/test_state.py` 與 `tests/test_gui.py::TestStatePersistence` 對應案例
  - 新模組 `src/updater/gui/state.py`：`GuiState{project,source,updated_at}`、`STATE_SCHEMA=1`、`state_path()`、`fallback_state_dir()`、`state_files()`、`load_saved_state()`、`load_state()`、`save_state()`（tmp + `os.replace`）、`usable()`
- **修改原因 (Why)**：
  - 現場需求：「這些目錄的設定會存檔嗎？我想要存檔，又希望 packages 可以自動找上一層」。
  - 現況两者互斥的風險：把 GUI 選的路徑寫回 `updater.toml` 會蓋掉部署設定，且一旦寫死就不再走自動鏈（`exe 上一層含 .whl` 這層失效）。
- **解耦與修改方式 (Decoupling & How)**：
  - 分工：`updater.toml` = 部署/團隊設定（人工）、`updater_state.json` = 這台機器上次選的資料夾（GUI 自動），兩者互不覆蓋。
  - `state.py` 純 I/O 模組（無 webview 相依，可獨立測試）；寫入位置首選 exe 同層，失敗退回 `%LOCALAPPDATA%\Test Matrix\Updater`。
  - `app.py:Api`：`_project_override` / `_source_override` 是「明確選擇」的單一來源；`_persist_state()` 只寫這兩個值（`set_target` / `set_source` 成功後觸發）；`clear_target()` / `clear_source()` 清欄位並立刻回到自動解析；`main()` 用 `load_saved_state()` 讀檔，`--project` 缺席且目錄仍存在才套用 `state.project`，判讀結果放 `state_notes` → 第一次 scan 時輸出（與 config parse error 同一視窗時機机制）。
  - `set_source()` 改存**解析後的絕對路徑**（原本存 raw，相對路徑 `..` 重啟後無意義）。
  - `TargetBar.vue`：兩列各加「還原自動」按鈕（`.btn-reset-target` / `.btn-reset-source`），`project_saved` / `source_saved` 為 False 時停用；專案路徑後顯示 `（已保存）`。
- **驗證與測試 (Verification & Testing)**：
  - `pytest tests/ -q` → **207 passed / 7 failed（全部為 HEAD 既有失敗）/ 3 skipped**；新增 `tests/test_state.py` 16 案例（缺檔不報錯、dirty JSON/schema 不符、不残 `.tmp`、自動建父目錄、不可寫→回報不丟例外、`state_files()` 順序、exe 層無檔時讀 `%LOCALAPPDATA%`、`usable()`）與 `TestStatePersistence` 7 案例（沒選過就不寫檔、選過的 source 重啟沿用、`clear_target` 保留 source 且 `project` 回 `null`、`clear_source` 回到自動鏈、壞路徑被忽略、exe 唯讀→退回 LOCALAPPDATA + warning、`state_notes` 只輸出一次）
  - `npx vitest run` → **66 passed**（新增 3：未存檔時按鈕停用、`clear_source` 後 input 跟随且按鈕轉停用、`clear_target` 只清專案）
  - PyInstaller 重打包並啟動實測：`dist\pyinstaller\updater_gui\updater_gui.exe --project C:\Test_Matrix` 程序存活；啟動後 exe 目錄與 `%LOCALAPPDATA%` **都沒有** `updater_state.json` → 未動過的使用者仍走 toml → exe 上一層 → 內建自動鏈
- **結果 (Result)**：
  - 「要存檔」與「packages 自動找上一層」不再互斥：存的是明確選擇，自動鏈只在沒有選擇時接手。
  - 待现场确认：實際點擊「瀏覽…／套用／還原自動」後重開 exe，檢查是否沿用且來源顯示 `（gui）`。

### [2026-10-29 11:45] 目標列分三列、視窗加寬、packages 來源可設定（並修「來源離線卻靜默」）

- **對應規格 (Spec/Schema)**：
  - `docs/specs/target_resolution_spec.md` §6 改寫為六層優先序：`gui` → `cli` → toml(project→exe) → **exe 上層 whl 目錄** → 內建 UNC；新增 `source_origin`（`gui|cli|project|exe|exe_sibling|builtin`）與「來源可用性」強制條款
  - `docs/specs/gui_folder_dialog_spec.md` 新增 §3.1（TargetBar 版面：一條路徑一列、grid 欄位、視窗 1200 / min 900x420）與 §3.2（`set_source` / `choose_source_folder` 輸出契約）
  - `UpdaterConfig` 新增 `source_origin` 欄位（`config.py`）；`target.py` 新增 `SourceResolution{path,origin,error}`、`exe_sibling_source()`、`pick_source()`
- **修改原因 (Why)**：
  - 現場回饋：GUI 目標列三條路徑糊在同一列；packages 路徑不能改；「source 指到 \\pnt52 但我沒連 PNT52 怎麼還可以用」。
  - 實測證據：離線 UNC 的 `Path.exists() -> False`（延遲 2.70s、不丟例外），而 `core.py:108 scan_packages()` 對不存在的來源**回傳空 dict** → GUI 看起來正常、其實讀到 0 個 whl（靜默失敗）。
  - 另一實測：exe 放在 `packages\updater\` 時**有**讀到同層 `updater.toml`（其 source 明確寫 PNT52），不是找不到 toml；但 PyInstaller 測試版在 `dist\pyinstaller\updater_gui\` 找不到 toml（搜尋範圍只有 exe 同層與上 2 層）→ 退回內建 PNT52。
- **解耦與修改方式 (Decoupling & How)**：
  - `target.py`：`pick_source()` 單一入口做來源解析＋可用性探測（`probe` 開關；離線 UNC 的 `exists()` 要 2~3s，只在要回報的地方探）；`exe_sibling_source()` 依序取 `exe_dir.parent`（需直接含 `*.whl`）與 `<exe_dir>/packages`；`UpdateTarget.source` 帶解析結果。
  - `gui/app.py`：`_source_resolution()` / `set_source()` / `choose_source_folder()`；GUI 選的來源存於 `Api._source_override`（執行期覆蓋 toml）；`_do_scan()` push「packages 來源: <path> (<origin>)」與來源不可用的 error；視窗 `DEFAULT_WINDOW_WIDTH=1200`、`MIN_WINDOW_SIZE=(900,420)`。
  - `main.py`：`--source` 改走同一個 `pick_source()`（origin 回報 `cli`），來源不可用時印 `[WARNING]`。
  - `TargetBar.vue` 重寫版面：資訊側 4 列（專案 / venv / source / 設定，各自 `.target-row`，完整路徑 + ellipsis + title），控制側兩組（專案、packages 來源，各含 input / 套用 / 瀏覽…）；移除 `shorten()` 截字。
  - `scripts/build_gui_pyinstaller.bat`：打包後把 `updater.toml` 複製到 exe 旁（否則測試版一律吃內建網路碟）。
- **驗證與測試 (Verification & Testing)**：
  - `pytest tests/ -q` → **183 passed / 7 failed（全部為 HEAD 既有失敗）/ 3 skipped**；新增 `TestPickSource` 8 案例（toml 勝過 exe 上層、上層需含 .whl、無 sibling 退回 builtin、gui/cli override 的 origin、不可用→error、`probe=False` 不探測）與 `TestSetSource` 5 案例（切換生效、不存在則不 switch、空路徑、對話框選取、對話框不可用→reason + error log）
  - `npx vitest run` → **63 passed**；新增 `test_each_path_gets_its_own_row`（三條路徑各自一列、互不出現於對方那列）與 source 套用／失敗保留舊值／瀏覽／`source_error` 顯示 等 5 案例
  - CLI 實測：`python src/updater/main.py --project C:\Test_Matrix --dry-run` → `Source : \\pnt52\...\packages (exe)` + `[WARNING] 來源目錄不可用: ...`（不再只說 "No .whl files"）
  - 佈局實測：`exe_sibling_source(C:\Github\Test-Matrix_Release_whl\packages\updater)` → `...\packages`（上層含 133 個 .whl）；同址若讀到 toml 仍是 PNT52（origin `exe`）→ 要用本地 whl 需把 toml 的 `source` 改成 `'..'` 或刪掉該行
  - PyInstaller 重打包：`dist\pyinstaller\updater_gui\updater_gui.exe` 可啟動（程序存活、無 frontend 錯誤）、已自帶 `updater.toml`
- **結果 (Result)**：
  - 來源解析與可用性皆有契約與測試覆蓋；GUI 會顯示來源及其決定層級，離線不再靜默成功。
  - 待现场确认：新版 GUI 實際點擊（三列版面、1200 寬、packages 的瀏覽／套用）。
  - 成品 repo 尚未更換；正式發佈仍走 Nuitka `build_gui.bat`（注意其 entry 是 `app.py`，資源對應與 PyInstaller 的 `entry_gui.py` 不同）。


### [2026-10-29 10:20] 修復 GUI「瀏覽…」資料夾選取失效（pywebview 6.2.1 API 漂移）＋ PyInstaller 測試版

- **對應規格 (Spec/Schema)**：
  - 新增 `docs/specs/gui_folder_dialog_spec.md`：pywebview 相依契約（只准 `Window.create_file_dialog` + `webview.FileDialog.FOLDER`；禁止 module 層 `webview.create_file_dialog` / `FOLDER_DIALOG`）、`choose_target_folder()` 輸出契約 `{cancelled, reason, error, target}`、前端四種分支行為、邊界條件與驗收項目
  - `docs/specs/target_resolution_spec.md` §2：修正命名漂移（`Api.select_target()` → 實作的 `choose_target_folder()` / `set_target()`）
  - `pyproject.toml`：`pywebview>=5.0` → **`pywebview==6.2.1`**（gui / dev extras），並加入 `pyinstaller>=6.0`
- **修改原因 (Why)**：
  - 1.5.0 實測：GUI 目標列的「瀏覽…」按了沒反應，log 出現 `AttributeError: module 'webview' has no attribute 'create_file_dialog'`。
  - 根因：`app.py` 呼叫 **module 層** `webview.create_file_dialog(webview.FOLDER_DIALOG, ...)`；pywebview 5/6 已移除該 module 函式（6.2.1 實測 `hasattr(webview,'create_file_dialog') == False`），且 `FOLDER_DIALOG` 在 6.2 已棄用。例外被 `except` 吞掉後回傳 `{"cancelled": True}`，前端 `browse()` 見 `cancelled` 直接 return → 完全靜默。
  - 依賴只宣告 `pywebview>=5.0`，打包時吃到新版 API 無人察覺。
- **解耦與修改方式 (Decoupling & How)**：
  - 新增 `src/updater/gui/dialog.py`：pywebview 相容層（SRP）。`folder_dialog_type()` 取 `FileDialog.FOLDER`（<6.2 fallback `FOLDER_DIALOG`）；`pick_folder(window, start_dir)` 接受**注入的 window**、回傳路徑或 None，無法建立對話框時丟 `DialogUnavailable`（顯式錯誤流，不吞例外）。
  - `src/updater/gui/app.py:Api.choose_target_folder()`：改用 `pick_folder(self._window, ...)`；失敗時 `_push_log("error", ...)`（原本用 debug 等級，現場看不到）並回傳帶 `reason` 的契約欄位。
  - `TargetBar.vue:browse()`：`cancelled && reason` → 顯示「無法開啟資料夾對話框：<reason>；請手動輸入路徑後按「套用」」；純取消仍靜默（規格 §3）。
  - 打包：新增 `scripts/entry_gui.py`（薄 entry）與 `scripts/build_gui_pyinstaller.bat`（測試版 onedir，含 `pywebview==6.2.1` 環境閘門、不關 console 以便看錯誤）。
    依官方文件而非試誤：PyInstaller `runtime-information` 表明 entry script 會被凍成 `__main__`（`__file__` 在 bundle 根），且 `--add-data` 目標「should mirror」套件路徑 → 故 entry 改薄啟動腳本讓 `updater.gui.app` 以 import 模組進 bundle，`--add-data` 用 `updater\guirontend\dist`。pywebview 官方 `/api/` 僅文件化 `window.create_file_dialog(...)` 與 `FileDialog.OPEN/FOLDER/SAVE`，`/guide/freezing` 建議 Windows 用 pyinstaller + `--add-data` 並 exclude 多餘後端。
- **驗證與測試 (Verification & Testing)**：
  - 根因重現：`.venv/Scripts/python.exe`（pywebview 6.2.1）呼叫 module 層 API → `AttributeError: module 'webview' has no attribute 'create_file_dialog'`
  - 安裝確認：venv 內 `pip list` = `pywebview 6.2.1`（import origin 同 venv）；`pip install --upgrade "pywebview==6.2.1"` → already satisfied（無需升級）
  - 靜態確認：`App.vue:14/31` 掛載 `TargetBar`，成品 bundle 含 `target-bar`/`目標資料夾`/`瀏覽`/`choose_target_folder`，CSS 含 `.target-bar` → UI 有載入，坏的是後端
  - 新測試：`tests/test_dialog.py`（12 案例：`folder_dialog_type()==20`、tuple/str/None/丟例外、`window=None`、無 `create_file_dialog`、靜態防呆不得再用 module 層 API、已裝版本必須為 6.2+）
  - `tests/test_gui.py::TestChooseTargetFolder`（5 案例：選取→`set_target("D:\Work\ProjB")`、取消不動 target、起點目錄＝目前 project、對話框不可用→`reason` + `_push_log("error")`、後端例外→`reason`）
  - 指令：`pytest tests/test_dialog.py tests/test_gui.py tests/test_target.py tests/test_config.py -q` → **59 passed / 2 failed**
  - `npx vitest run` → **58 passed**（新增 `test_browse_reports_unavailable_dialog_with_actionable_hint`）
  - 既有失敗（非本次造成，`git stash` 對照 HEAD 相同失敗）：`TestInstallVersionedPackageSetsFlag::test_install_versioned_package_sets_flag`、`TestCheckUpdatesRespectsAutoUpdateDisabled::test_do_scan_returns_early_when_flag_set`
  - 打包煙測：PyInstaller onedir 產 `dist/pyinstaller/updater_gui/updater_gui.exe`，於 `%TEMP%` 以 `--project C:\Test_Matrix` 啟動 → 解析出 `Venv: C:\Test_Matrix\.venv`、視窗存活（PID 8492）、無 `[ERROR] Frontend not built`
    （第一版煙測曾失敗：`--add-data` 位置錯 → 已依 PyInstaller 文件改為鏡射套件路徑後通過）
- **結果 (Result)**：
  - 後端與前端的對話框契約已對齊 `gui_folder_dialog_spec.md`，失敗不再靜默；pywebview 鎖在 6.2.1 且打包腳本會擋版本不符。
  - 待现场确认：視窗實點「瀏覽…」出現原生資料夾對話框並成功切換 target（目前僅到「視窗可啟動 + 契約測試全綠」）。
  - 成品 repo（`packages/updater*`）尚未更換：依指示本輪只修來源與測試，正式 1.5.1 仍走 Nuitka `build_gui.bat`。


### [2026-10-28 17:55] 發佈 1.5.0：版號升級、重新打包、打 tag 並推到 fork

- **對應規格 (Spec/Schema)**：
  - `pyproject.toml` `[project] version = "1.5.0"`（單一版號來源；`scripts/update_version.py` 同步 `src/updater/__init__.py.__version__`）
  - `docs/CHANGELOG.md`：`[Unreleased]` → `[1.5.0] - 2026-10-28`，補 `[1.5.0]` 比較連結
  - SemVer：新增 `--project`、GUI 目標資料列、`get_target/set_target/choose_target_folder` API → **minor** bump（1.4.0 → 1.5.0）
- **修改原因 (Why)**：
  - 1.4.x 的 exe 只能待在專案目錄內，且單檔版曾被防毒封鎖；本次功能層變更需正式版本與 tag，讓發佈 repo 的成品可追溯。
  - `git tag -l` 與 `git ls-remote --tags` 皆為空 → CHANGELOG 引用的 `updater-1.4.0` 等 tag 實際不存在，需從 `updater-1.5.0` 開始建立。
- **解耦與修改方式 (Decoupling & How)**：
  - 版號只改 `pyproject.toml`，由既有 `update_version.py`  propagating 到 `__init__.py`，避免多处硬寫（build 脚本已自動執行）。
  - exe 內嵌版由 `scripts/print_version.py` → `dist\tm_version.txt` → `--product-version/--file-version`，與 `__version__` 同源。
  - 推送目標：`origin`（`lwsvincent/tm_updater`）對 `aron0803` 為 403 唯讀，改推 `fork`（`aron0803/tm_updater`，`main` track `fork/main`），CLAUDE.md 已記錄；`gitlab` remote 尚未設定。
- **驗證與測試 (Verification & Testing)**：
  - `pytest`：155 passed / 7 failed（既有失敗）/ 3 skipped；`npx vitest run`：5 files / 57 passed（注意 `--reporter=basic` 在此 vitest 版本已移除，會造成 startup error）。
  - `scripts\build_gui.bat` → exit 0；`dist\updater_gui.dist\updater_gui.exe` 14,149,120 B、`dist\onefile\updater_gui.exe` 30,464,000 B，兩版 `ProductVersion/FileVersion = 1.5.0.0`，`dist\tm_version.txt` = `1.5.0`。
- **結果 (Result)**：1.5.0 已打 tag `updater-1.5.0` 並推送 `fork/main`；發佈 repo 的 `packages/updater*` 已換成 1.5.0 成品。未涵蓋：`origin` 寫入權限與 `gitlab` remote。

### [2026-10-28 15:45] Updater 打包：onedir + onefile 雙產物、版號寫入、防毒友善單檔

- **對應規格 (Spec/Schema)**：
  - `docs/README.md` / `docs/README_ZH.md`「打包發佈 (Build)」段落
  - 產物契約：`dist\updater_gui.dist\updater_gui.exe` + `dist\updater_gui.zip`（onedir）、`dist\onefile\updater_gui.exe`（onefile）
- **修改原因 (Why)**：
  - 上一次 build 結束碼 0 但只有 onefile 檔存在：`dist\updater_gui.dist` 與 `updater_gui.zip` 遺失，`Compress-Archive` 報 `ArchiveCmdletPathNotFound`。
  - exe 版資訊為 `ProductVersion/FileVersion = 0.0.0.0`、Company 空，現場無法辨識版本。
- **解耦與修改方式 (Decoupling & How)**：
  - 受影響檔案：`scripts/build_gui.bat`、`scripts/build_updater.bat`、`scripts/print_version.py`
  - 根因 1：兩個 build 都以 `app.py` 為模組名，Nuitka 都輸出到同一個 `dist\app.dist`；`move ... >nul` 與 `Compress-Archive` 的錯誤被吞掉。修法：各自獨立 `--output-dir`（`dist\onedir_build` / `dist\onefile_build`），並對每個產物做 `if not exist ... exit /b 1`。
  - 根因 2：`for /f ('"python.exe" "print_version.py"')` 的引號被 `cmd /c` 剝除，`TM_VER` 恆為空 →  fallback `0.0.0`。修法：版號寫到 `dist\tm_version.txt`，再用 `set /p` 讀入。
  - 單檔版防毒設定：移除 `--mingw64`（改用 MSVC，一般連結的 PE）、補齊 `--product-name/--company-name/--product-version/--file-version/--file-description/--copyright`、`--onefile-tempdir-spec="{CACHE_DIR}/{COMPANY}/{PRODUCT}/{VERSION}"`（固定可重用目錄，非隨機 `%TEMP%\onefile_*`）、`--onefile-cache-mode=cached`、`--onefile-no-compression`（壓縮自解壓最容易被判定可疑）。
  - 保留 onedir 作為現場防毒封鎖單檔時的備援方案。
- **驗證與測試 (Verification & Testing)**：
  - `cmd /c scripts\build_gui.bat` → exit 0；`dist\updater_gui.dist\updater_gui.exe` 14,149,120 B、`dist\updater_gui.zip` 11,412,087 B、`dist\onefile\updater_gui.exe` 30,464,000 B。
  - 兩版 `(Get-Item exe).VersionInfo`：`ProductName=Test Matrix Updater`、`ProductVersion=FileVersion=1.4.0.0`、`CompanyName=Test Matrix`。
  - 防毒實測（本機 Windows Defender，RealTimeProtectionEnabled=True）：單檔版複製到 `%TEMP%\tm_onefile_test` 後以 `--project` 啟動 → 程序存活、`MainWindowTitle="Test Matrix Updater"`、exe 未被移除、`Get-MpThreatDetection` 前後皆 0 筆；解壓目錄 `%LOCALAPPDATA%\Test Matrix\Test Matrix Updater\1.4.0`（38 檔 / 28.9 MB），第二次啟動沿用同一目錄。
  - 編譯報表：`dist\build_report_onedir.txt`、`dist\build_report_onefile.txt`。
- **結果 (Result)**：兩版產物如契約建立，版資訊正確；單檔版在本機 Defender 下存活。未涵蓋：程式碼签章（免費版 Nuitka 無 signing 選項）、其他廠牌防毒與實際 PNT52 分享路徑。

### [2026-10-28 15:20] updater.toml 編碼容錯：BOM / UTF-16 / Big5(cp950) 不再讓程式啟動失敗

- **對應規格 (Spec/Schema)**：
  - 新增 `docs/specs/config_encoding_spec.md`
  - `UpdaterConfig` 新增唯讀欄位：`parse_error: str = ""`、`encoding: str = ""`
  - 新函式契約：`read_toml_text(path) -> tuple[str, str]`（回傳內容與實際編碼）
- **修改原因 (Why)**：
  - 現場以记事本「ANSI」（zh-TW = cp950/Big5）或含 BOM 的 UTF-8 存檔時，`tomllib.loads` 直接丟例外（`tomllib` 只接受不帶 BOM 的 UTF-8）。
  - GUI 以 `--windows-console-mode=disable` 打包，例外發生在視窗建立前 → 視窗不出現、也看不到錯誤，使用者判斷為「無法使用」。
- **解耦與修改方式 (Decoupling & How)**：
  - 受影響檔案/函式：`src/updater/config.py` (`read_toml_text`, `load_config`)、`src/updater/main.py` (`main`)
  - 解耦設計：把「讀位元組 + 判編碼」與「解析 TOML」拆成兩個純函式，`load_config` 只做決策；`read_toml_text` 不依賴全域狀態，可直接測試。
  - 細節：先比對 BOM 旗標（UTF-32 LE/BE、UTF-16 LE/BE、UTF-8-sig）**手動剝除 BOM 再解碼**（留著 BOM 会让 `tomllib` 在 line 1 column 1 失敗）→ 再試 UTF-8 → 再試 `cp950`、`cp1252`；全失敗才丟 `ValueError`。
  - 解析失敗改為**不中斷**：使用內建預設值、設定 `parse_error`，CLI 印到 stderr、GUI 推一筆 log 並在 TargetBar 以橘色警示顯示原因與偵測到的編碼。
- **驗證與測試 (Verification & Testing)**：
  - `pytest tests/test_config.py -k Encoding` → 7 passed：UTF-8、UTF-8+BOM（`encoding == "utf-8-sig"`）、cp950（內容含 `\\pnt52\研發本部_技術服務處\packages`）、UTF-16、語法錯誤仍保留預設值、完全無法解碼 → 訊息含「編碼不支援」、`read_toml_text` 回傳編碼。
  - 全量 `pytest`：155 passed / 7 failed（既有失敗，以 `git stash` 跑 HEAD 基準確認為 124 passed / 同 7 failed）/ 3 skipped。
- **結果 (Result)**：設定檔編碼問題依規格收斂，實作與契約一致且模組可獨立測試；文件已於 `docs/README*.md` 標存檔應用「UTF-8 不含 BOM」。

### [2026-10-28 15:05] 目標資料夾解析：一份 exe 可更新任意專案（CLI + GUI）

- **對應規格 (Spec/Schema)**：
  - 新增 `docs/specs/target_resolution_spec.md`
  - 契約：`UpdateTarget{project_root, config, python_exe, config_origin}`；`config_origin ∈ {project, exe, builtin}`
  - 解析順序：project root = `--project` → 自 cwd 向上 4 層找含 venv 或 `updater.toml` 的目錄 → exe 所在鏈路；config = `<project>/updater.toml` → exe 層級 → 內建；venv = `--venv`（嚴格）→ `<project>/<venv_name>/Scripts/python.exe` → 上層 → 舊鏈路
- **修改原因 (Why)**：
  - `find_config()` 以 `sys.argv[0]` 為基準、venv 由 exe 目錄推估、`launcher.executable` 相對於設定檔 → exe 必須實體放在每個專案裡，無法放網路碟或工具碟。
- **解耦與修改方式 (Decoupling & How)**：
  - 新增 `src/updater/target.py`：純函式、`exe_dir`/`cwd` 由參數注入（可 Mock、不碰本機）；`resolve_source()` 對 UNC 與磁碟機開頭的設定值**完全不 re-anchor**（Python 3.11 `Path(r"\\server\share").is_absolute()` 為 False、`splitdrive` 為空，且 `resolve()` 會附加尾端 `\`），相對路徑才以 `config_dir` 為基準。
  - 「venv 擁有者」回溯 (`python_exe.parents[2]`) 僅在**未**給 `--project` 時啟用，保留舊佈局（exe 位於 `<project>\updater\`）的行為。
  - `src/updater/main.py`：新增 `--project`，改由 `resolve_target()` 取得目標，`TargetError` → stderr + `exit 2`。
  - `src/updater/gui/app.py`：`Api(config, python_exe, target)`、`get_target()`、`set_target()`（換目标後清 pip cache 並重掃；失敗保留原目標）、`choose_target_folder()`（`webview.FOLDER_DIALOG`）。
  - 前端 `TargetBar.vue` + `main.js`：顯示專案/venv/source/設定檔來源，可輸入路徑或選資料夾，`reloadTarget()` 重置套件與更新狀態。
- **驗證與測試 (Verification & Testing)**：
  - 新增 `tests/test_target.py`（24 案例）：明確 `--project`、專案 toml 優先、舊佈局迴歸（`project_root == TestMatrix` 且 `config_origin == exe`）、向上探索、`--venv` 嚴格模式、UNC source 不被改寫、exe 層級設定檔搜尋、`get_target/set_target` 重新綁定與錯誤路徑保留舊值。
  - 前端 `tests`：57 passed（5 files，含 `TargetBar.spec.js`）；`npm run build` 成功（index.html 0.39 kB / css 8.25 kB / js 78.81 kB）。
  - 端到端：於 `%TEMP%` 執行 `python -m updater.main --project C:\Github\acbel\tm_updater --source C:\Github\Test-Matrix_Release_whl\packages --dry-run` → 解析到 `.venv`、載入專案 toml、找到 16 個 wheel 套件。
- **結果 (Result)**：exe 與被更新資料夾解耦，舊部署行為由迴歸測試保障；實作 100% 對齊規格。
