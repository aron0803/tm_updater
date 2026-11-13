# Git Branch Management Guide

## Why Use Branches?

Imagine you're writing a document. Without branches, everyone edits the same file at the same time - chaos! Branches let each person work on their own copy, then merge changes back safely.

**Benefits:**
- Work on features without breaking the main code
- Review changes before they go live
- Easy rollback if something goes wrong
- Clear history of what changed and why

---

## Branch Structure

```
Release-Public (Customer Release)
    ^
    |  PR (after QA approval)
    |
Release-DQ (Internal Testing)
    ^
    |  PR (after internal validation)
    |
main (Development Base)
    ^
    |  PR (after code review)
    |
feature/* or fix/* (Your Work)
```

### Branch Descriptions

| Branch | Purpose | Who Uses It |
|--------|---------|-------------|
| `main` | Latest stable development code | All developers |
| `Release-DQ` | Internal testing / QA validation | QA Team |
| `Release-Public` | Production-ready for customers | Release Manager |
| `feature/*` | New features | Developers |
| `fix/*` | Bug fixes | Developers |

---

## What is a Pull Request (PR)?

A **Pull Request** is like asking: "I finished my work, can someone review it before we add it to the main code?"

### PR Workflow (Simple Version)

```
1. Create branch    -->  2. Write code    -->  3. Create PR    -->  4. Review    -->  5. Merge
   (feature/xxx)          (commit changes)      (request review)     (team checks)     (add to main)
```

### Why PRs Matter

1. **Code Review**: Someone else checks your work for bugs
2. **Discussion**: Team can comment and suggest improvements
3. **History**: Clear record of what changed and why
4. **Safety**: Prevents broken code from reaching main branch

---

## Daily Workflow

### Starting New Work

```bash
# 1. Make sure you're on main and up-to-date
git checkout main
git pull origin main

# 2. Create your feature branch
git checkout -b feature/your-feature-name

# 3. Do your work, then commit
git add .
git commit -m "feat: add new feature description"

# 4. Push to remote
git push origin feature/your-feature-name

# 5. Create PR on GitHub (or use command line)
gh pr create --title "Add new feature" --body "Description of changes"
```

### Naming Conventions

| Type | Branch Name | Commit Message |
|------|-------------|----------------|
| New Feature | `feature/add-login-page` | `feat: add login page` |
| Bug Fix | `fix/issue-42-button-error` | `fix: resolve button click error` |
| Refactor | `refactor/cleanup-api-code` | `refactor: simplify API handlers` |

---

## Release Process

### Development to Internal Testing (DQ)

```
feature/xxx  -->  main  -->  Release-DQ
                   ^            ^
                   |            |
                  PR           PR
              (code review)  (ready for QA)
```

1. Developer creates PR from `feature/*` to `main`
2. Team reviews and approves
3. Merge to `main`
4. When ready for QA: create PR from `main` to `Release-DQ`

### Internal Testing to Public Release

```
Release-DQ  -->  Release-Public
      ^               ^
      |               |
   QA Testing      Customer Release
```

1. QA tests on `Release-DQ` branch
2. After validation: create PR from `Release-DQ` to `Release-Public`
3. Final approval from release manager
4. Merge and tag version

---

## Common Commands

```bash
# Check current branch
git branch

# Switch to a branch
git checkout branch-name

# Create and switch to new branch
git checkout -b new-branch-name

# See what files changed
git status

# Save your changes
git add .
git commit -m "your message"

# Push to GitHub
git push origin branch-name

# Get latest changes from remote
git pull origin branch-name

# See commit history
git log --oneline -10
```

---

## Branch Protection Rules (Recommended)

For `main`, `Release-DQ`, and `Release-Public`:

- [ ] Require pull request before merging
- [ ] Require at least 1 approval
- [ ] Require status checks to pass (tests)
- [ ] No direct push allowed

---

## Quick Reference Card

| I want to... | Command |
|-------------|---------|
| Start new feature | `git checkout -b feature/name` |
| Save my work | `git add . && git commit -m "message"` |
| Share my work | `git push origin branch-name` |
| Get team's updates | `git pull origin main` |
| See my changes | `git status` |
| Create PR | `gh pr create` or use GitHub website |

---

## FAQ

**Q: What if I made changes on the wrong branch?**
```bash
# Stash your changes
git stash
# Switch to correct branch
git checkout correct-branch
# Apply your changes
git stash pop
```

**Q: How do I undo my last commit?**
```bash
# Keep changes, undo commit
git reset --soft HEAD~1
```

**Q: My branch is behind main, how do I update?**
```bash
git checkout your-branch
git merge main
# Or use rebase for cleaner history
git rebase main
```

---

## Summary

1. **Never push directly to main** - always use PR
2. **One feature = one branch** - keep changes focused
3. **Write clear commit messages** - your future self will thank you
4. **Review others' PRs** - learn and help the team
5. **Delete merged branches** - keep the repo clean
