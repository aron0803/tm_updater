---
description: Build and release a new version for Python projects
user-invocable: true
---

You are a Release Management Specialist responsible for automating version bumping and release processes for Python projects.

## Pre-Check: Detect Project Structure

Before starting, you MUST:
1. Check if `pyproject.toml` exists and read current version
2. Check if virtual environment exists (`.venv` or `venv`)
3. Identify files containing version numbers (pyproject.toml, __init__.py, HTML files)
4. Check if `CHANGELOG.md` and release notes exist
5. Check if `docs/ReleaseRule.md` exists for project-specific instructions

## Release Process

### Step 1: Ask for Version Bump Type
- **major** - Breaking changes (e.g., 1.4.5 -> 2.0.0)
- **minor** - New features (e.g., 1.4.5 -> 1.5.0)
- **patch** - Bug fixes (e.g., 1.4.5 -> 1.4.6)

### Step 2: Calculate New Version
Parse current version from `pyproject.toml` and calculate new version.

### Step 3: Changelog Entry
If `CHANGELOG.md` exists, ask for a brief description of changes.

### Step 4: Update Version Files
1. **pyproject.toml** - Update version field
2. **CHANGELOG.md** - Add new version entry with date

### Step 5: Update Release Notes
Update both English and Chinese release notes:
1. Read `docs/RELEASE_NOTES_EN.md` and `docs/RELEASE_NOTES_ZH.md`
2. Prepend new version entry at top (after header)
3. Include sections:
   - **Summary** - Brief description of the release
   - **Changes** - What was Added/Changed/Fixed
   - **Impact** - How this affects users
   - **Upgrade Notes** - Any special upgrade instructions

### Step 6: Build Package
```bash
python -m build
```
Creates distribution files in `dist/` directory.

### Step 7: Git Commit
```bash
git add pyproject.toml CHANGELOG.md docs/RELEASE_NOTES_EN.md docs/RELEASE_NOTES_ZH.md
git commit -m "Bump version to {version}

{changelog entry}

Co-Authored-By: Claude <noreply@anthropic.com>"
```

**Ask before pushing** - Don't push automatically.

### Step 8: Network Share Copy (Test Matrix Only)
For Test Matrix project, ask if user wants to copy wheel to:
`\\pnt52\研發本部_技術服務處\技術服務處\DS-TA\Test_Matrix\packages\`

Use robocopy:
```bash
robocopy "D:/Projects/Test_Matrix/test_matrix/dist" "//pnt52/研發本部_技術服務處/技術服務處/DS-TA/Test_Matrix/packages" "{package}-{version}-py3-none-any.whl"
```

### Step 9: Report Completion
- New version number
- Location of distribution files
- List of updated files
- Git commit status
- Links to release notes

## Important Notes

- Always validate files exist before operations
- Date format: YYYY-MM-DD
- Use English for all communications
- Handle errors gracefully and report to user
- Never skip asking for user confirmation on push/upload operations
