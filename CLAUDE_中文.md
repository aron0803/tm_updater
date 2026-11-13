# CLAUDE.md

如果有更好的選項，請反駁我的意見，並說明原因。  
永遠說實話，不要粉飾。  
此專案仍在開發中，尚未正式推出。  
使用 `.venv` 環境中的 Python。  
避免在檔案或程式碼中使用 icon。  
檔案結構：
  frontend: .src/static, URL: 127.0.0.1:5000
  backend: ./src/test_matrix
  startup: .start_api_server.py (or .bat)
測試結束後請關閉 backend terminal。  
檢查完整結構前，先閱讀各資料夾中的 `AI_GUIDE.md`。  
一律使用英文回覆。  
請在 `CLAUDE.md` 頂部的 `## Release Workflow` 或 `## Definitions` 區段下加入：

當被要求「upload」或「push to PNT52」時，意思是把已建置好的 distribution files 複製到 PNT52 network share，**不是**建置檔案。Upload 步驟是在 build 步驟之後。

請在 `## Code Style` 或 `## Architecture` 區段下加入：

針對架構問題，先詢問實際 scope 與 constraints，再提出建議。此 codebase 由多個各自有測試的 sub-package 組成，避免過度工程化的建議。

請在 `## Release Workflow` 區段下加入：

標準 release workflow：1) smart commit, 2) version bump, 3) changelog update, 4) build, 5) git push, 6) upload to PNT52 network share。Proceed 前必須確認 upload destination。

## Issue Management

預設 reporter: Vincent Lee (dev)

## Git Push

此 repository 同時有 `origin` (GitHub) 與 `gitlab` remotes。Push commits 時，請將目前 branch push 到**兩個** remotes；如有 tags，也一併 push。
