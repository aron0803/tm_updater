---
description: Run pytest tests with auto-approval (turbo mode)
---

// turbo-all

This workflow runs pytest tests automatically without requiring user approval.

## Usage Examples

When the user says:
- `/run-tests` - Run all tests
- `/run-tests unit` - Run unit tests only
- `/run-tests excel_condition` - Run specific test folder
- `/run-tests --failed` - Show only failed tests

## Steps

1. Determine the test scope based on user input:
   - No argument: Run all tests in `src/test_matrix/`
   - With path: Run tests in `src/test_matrix/util/tests/unit/<path>/`
   - With `--failed` flag: Filter output to show only FAILED tests

2. Run the pytest command:
```powershell
.venv\Scripts\python.exe -m pytest <test_path> -v --tb=line
```

3. If `--failed` flag is specified, filter the output:
```powershell
.venv\Scripts\python.exe -m pytest <test_path> -v --tb=line 2>&1 | findstr /i "FAILED"
```

## Common Test Paths

- All tests: `src/test_matrix/`
- Unit tests: `src/test_matrix/util/tests/unit/`
- Excel condition tests: `src/test_matrix/util/tests/unit/excel_condition/`
- Integration tests: `src/test_matrix/util/tests/integration/`

## Notes

- Always use `.venv\Scripts\python.exe` to ensure the virtual environment is used
- Use `-v` for verbose output
- Use `--tb=line` for concise traceback
- Use `--tb=short` for more detailed traceback if needed
