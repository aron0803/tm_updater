---
description: Review git changes and commit each feature separately, then update changelog
---

# Commit By Feature Workflow

This workflow reviews all git changes and creates separate commits for each feature/functionality.

## Steps

### 1. Check Git Status
// turbo
```bash
git status
git diff --stat
```

### 2. Review Each Changed File
For each modified file, run:
// turbo
```bash
git diff <filepath>
```

Analyze the changes and group them by feature/functionality.

### 3. Create Feature Groups
Based on the diffs, identify distinct features. Common groupings:
- Bug fixes (prefix: `fix`)
- New features (prefix: `feat`)
- Code refactoring (prefix: `refactor`)
- Documentation changes (prefix: `docs`)
- Style/formatting changes (prefix: `style`)

### 4. Commit Each Feature Separately
For each feature group:

a. Stage only the relevant files:
```bash
git add <file1> <file2> ...
```

b. Commit with descriptive message:
```bash
git commit -m "<type>(<scope>): <short description>

- Detail 1
- Detail 2"
```

**Commit Message Format:**
- `fix(scope)`: Bug fixes
- `feat(scope)`: New features
- `refactor(scope)`: Code refactoring
- `docs`: Documentation
- `style`: Formatting, no code change

### 5. Update CHANGELOG
After all commits, update CHANGELOG.md:

1. Add new entries under `## [Unreleased]` section
2. Group by:
   - `### Added` - New features
   - `### Fixed` - Bug fixes
   - `### Changed` - Changes in existing functionality
   - `### Removed` - Removed features
   - `### Deprecated` - Soon-to-be removed features

### 6. Commit CHANGELOG
```bash
git add CHANGELOG.md
git commit -m "docs: update CHANGELOG with unreleased features"
```

### 7. Verify
// turbo
```bash
git status
git log --oneline -10
```

## Notes
- If a file contains multiple unrelated changes, consider using `git add -p` for interactive staging
- For untracked files (new files), decide if they belong to a specific feature or should be a separate commit
- Always restore version files (`__init__.py`) if they were changed as part of a previous release
