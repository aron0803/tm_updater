---
description: Hotfix - smart commit, patch version bump, build, push, and upload to PNT52
user-invocable: true
---

You are a Hotfix Release Agent. Your job is to execute a complete hotfix workflow in sequence:

1. **Smart Commit** - Analyze and commit staged changes
2. **Patch Version Bump** - Increment patch version (x.y.z -> x.y.z+1)
3. **Build** - Build the wheel package
4. **Push** - Push to remote repository
5. **Upload to PNT52** - Copy wheel to network share

## Workflow Execution

### Step 1: Smart Commit

First, check if there are any staged or unstaged changes:

```bash
git status
git diff --staged
```

If there are changes to commit:
1. Analyze the changes to understand their purpose
2. Group files into logical commits using conventional commit format:
   - `fix:` for bug fixes (most common for hotfix)
   - `feat:` for new features
   - `refactor:` for code refactoring
   - `chore:` for maintenance tasks
3. Keep subject line under 72 characters
4. Use imperative mood ("Fix bug" not "Fixed bug")
5. Add `Co-Authored-By: Claude <noreply@anthropic.com>` at the end
6. Ask for confirmation before committing

If no changes to commit, proceed to Step 2.

### Step 2: Patch Version Bump

1. Read current version from `pyproject.toml`
2. Calculate new patch version (e.g., 1.8.5 -> 1.8.6)
3. Update version in:
   - `pyproject.toml`
   - `CHANGELOG.md` (add entry with today's date)
4. Ask user for a brief changelog description
5. Commit version bump:
   ```bash
   git add pyproject.toml CHANGELOG.md
   git commit -m "Bump version to {version}

   Co-Authored-By: Claude <noreply@anthropic.com>"
   ```

### Step 3: Update Release Notes

Update both English and Chinese release notes:
1. Read `docs/RELEASE_NOTES_EN.md` and `docs/RELEASE_NOTES_ZH.md`
2. Prepend new version entry at top (after header)
3. Include sections:
   - **Summary** - Brief description of the release
   - **Changes** - What was Added/Changed/Fixed
   - **Impact** - How this affects users
   - **Upgrade Notes** - Any special upgrade instructions
4. Commit release notes:
   ```bash
   git add docs/RELEASE_NOTES_EN.md docs/RELEASE_NOTES_ZH.md
   git commit -m "docs: add release notes for v{version}

   Co-Authored-By: Claude <noreply@anthropic.com>"
   ```

### Step 4: Build Package

Detect which build path to use:

1. Check if `scripts\build_pyc_wheel.bat` exists in the project root.
   - **If yes** → use the pyc-protected build:
     ```bash
     call scripts\build_pyc_wheel.bat
     ```
     The output wheel will be named `{package_name}-{version}-cp311-cp311-win_amd64.whl`.
   - **If no** → fall back to the standard build:
     ```bash
     python -m build
     ```
     The output wheel will be named `{package_name}-{version}-py3-none-any.whl`.

Verify the wheel was created in `dist/` directory.

### Step 5: Push to Remote

Push to the remote repository:

```bash
git push
```

### Step 6: Upload to PNT52

Copy the wheel to the network share using robocopy. The filename depends on which build was used:

- pyc build: `{package_name}-{version}-cp311-cp311-win_amd64.whl`
- standard build: `{package_name}-{version}-py3-none-any.whl`

```bash
robocopy "{project_dist_path}" "//pnt52/研發本部_技術服務處/技術服務處/DS-TA/Test_Matrix/packages" "{wheel_filename}"
```

Notes:
- Detect the project's dist path from current working directory
- Package name uses underscore (e.g., `scope_driver-1.7.2-cp311-cp311-win_amd64.whl`)
- robocopy exit codes 0-7 indicate success

### Step 7: Report Completion

Report completion with:
- New version number
- Commits created
- Location of wheel file
- Network share upload status

## Important Notes

- Execute steps in exact order: commit -> version -> release notes -> build (pyc if available, else standard) -> push -> upload
- If any step fails, stop and report the error
- Always use specific file paths for git add, not `git add -A`
- Never commit files containing secrets (.env, credentials, etc.)
- Use English for all commit messages
- Detect package name from pyproject.toml `[project] name` field
