Refute my opinion if a better option exists, and explain why.
Always tell the truth, no sugarcoating.
The project is still under development and has not yet been launched.
Use Python in .venv environment.
Avoid icon in files or code.
File structure:
  frontend: .src/static, URL: 127.0.0.1:5000
  backend: ./src/test_matrix
  startup: .start_api_server.py (or .bat)
Kill the backend terminal after tests.
Read AI_GUIDE.md in each folder before checking full structure.
always reply by using English
Add under a ## Release Workflow section or ## Definitions section at the top of AGENTS.md\n\nWhen asked to 'upload' or 'push to PNT52', this means copying built distribution files to the PNT52 network share, NOT building the files. The upload step comes AFTER the build step.
Add under ## Code Style or ## Architecture section\n\nFor architecture questions, start by asking about the actual scope and constraints before suggesting solutions. This codebase has separate sub-packages with their own tests - avoid over-engineering advice.
Add under ## Release Workflow section\n\nStandard release workflow: 1) smart commit, 2) version bump, 3) changelog update, 4) build, 5) git push, 6) upload to PNT52 network share. Always confirm upload destination before proceeding.

## Issue Management

Default reporter: Vincent Lee (dev)