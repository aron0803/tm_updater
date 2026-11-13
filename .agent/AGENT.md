# CLAUDE.md

Refute my opinion if a better option exists, and explain why.
Always tell the truth, no sugarcoating.
Use Python in .venv environment.
Avoid icon in files or code.
File structure:
  frontend: ./src/updater/gui/frontend
  backend: ./src/updater
always reply by using Traditional Chinese (繁體中文)

## Release Workflow

Standard release workflow:
1. **Smart Commit**: Review git changes and commit logically using conventional commit format
2. **Version Bump**: Increment version in `pyproject.toml`
3. **Changelog Update**: Update `docs/CHANGELOG.md` and release notes
4. **Build**: Build executable using Nuitka (`scripts/build_gui.bat` / `scripts/build_updater.bat`)
5. **Git Push**: Push commits and tags to `origin` (`https://github.com/aron0803/tm_updater`)
6. **Publish Release**: Create GitHub release and upload binary assets (`updater_gui.exe`, `updater_gui.zip`, `updater.zip`)

## Git Management

- Branch naming: `feature/*`, `fix/*`, `refactor/*`
- Main development branch: `main`
- Reference documentation: `docs/git-management.md`, `docs/ReleaseRule.md`, `docs/IssueRule.md`
