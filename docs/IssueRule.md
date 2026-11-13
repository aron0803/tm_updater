# Issue Management Rules

This document defines the issue management rules for the Test Matrix project.

## Documentation Structure

All issues must have a corresponding local documentation folder:

```
docs/
├── features/           # Feature requests
│   └── {issue-slug}/
│       └── README.md
├── refactors/          # Code refactoring
│   └── {issue-slug}/
│       └── README.md
└── bugs/               # Bug reports
    └── {issue-slug}/
        └── README.md
```

### Folder Naming Convention
- Use kebab-case: `frontend-logger-tabs`, `api-batch-export`
- Keep it short but descriptive
- Match the issue title slug

### README.md Template
```markdown
# {Issue Title}

**GitHub Issue:** #{issue-number}
**Reporter:** {Unit} - {Name}
**Created:** {YYYY-MM-DD}

## Description
{Brief description}

## Scope
- [ ] Frontend
- [ ] Backend

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
```

---

## Labels

### Type Labels
| Label | Color | Hex Code | Description |
|-------|-------|----------|-------------|
| `bug` | Red | `#d73a4a` | Something isn't working |
| `feature` | Green | `#0e8a16` | New feature request |
| `enhancement` | Blue | `#1d76db` | Improvement to existing feature |
| `documentation` | Purple | `#5319e7` | Documentation updates |
| `refactor` | Orange | `#f9a825` | Code refactoring |
| `test` | Cyan | `#0097a7` | Test related |

### Priority Labels
| Label | Color | Hex Code | Description |
|-------|-------|----------|-------------|
| `P0-critical` | Dark Red | `#b60205` | Must fix immediately, blocking |
| `P1-high` | Red | `#d93f0b` | Should fix in current sprint |
| `P2-medium` | Yellow | `#fbca04` | Plan for next sprint |
| `P3-low` | Light Gray | `#c5def5` | Nice to have |

### Status Labels
| Label | Color | Hex Code | Description |
|-------|-------|----------|-------------|
| `todo` | White | `#ffffff` | Not started |
| `in-progress` | Light Blue | `#0052cc` | Currently working on |
| `review` | Pink | `#e99695` | Waiting for review |
| `done` | Dark Green | `#006b75` | Completed |
| `blocked` | Black | `#000000` | Blocked by something |

### Component Labels
| Label | Color | Hex Code | Description |
|-------|-------|----------|-------------|
| `frontend` | Teal | `#006b75` | Frontend related (static/) |
| `backend` | Brown | `#795548` | Backend related (src/test_matrix/) |
| `api` | Indigo | `#3f51b5` | API related |
| `database` | Navy | `#0d47a1` | Database/data related |

### Reporter Labels
| Label | Color | Hex Code | Description |
|-------|-------|----------|-------------|
| `reporter:dev` | Green | `#0e8a16` | Reported by Developer |
| `reporter:dq` | Blue | `#1d76db` | Reported by DQ (Design Quality) |
| `reporter:ee` | Purple | `#9c27b0` | Reported by EE (Electrical Engineer) |
| `reporter:pl` | Orange | `#ff9800` | Reported by PL (Production Line) |

## Naming Convention

### Issue Title Format
```
[Component] Brief description of the issue
```

### Examples
| Type | Example Title |
|------|---------------|
| Bug | `[Frontend] Login button not responding on mobile` |
| Bug | `[Backend] API returns 500 on empty input` |
| Feature | `[Frontend] Add dark mode support` |
| Feature | `[API] Add batch export endpoint` |
| Enhancement | `[Backend] Improve CSV parsing performance` |
| Documentation | `[Docs] Update API documentation` |
| Refactor | `[Backend] Refactor test item validation logic` |

### Branch Naming (linked to Issue)
```
<type>/<issue-number>-<short-description>
```

Examples:
- `feature/42-dark-mode`
- `bugfix/55-login-error`
- `refactor/60-validation-logic`

## Issue Template

### Bug Report
```markdown
## Description
[Brief description of the bug]

## Steps to Reproduce
1. Go to '...'
2. Click on '...'
3. See error

## Expected Behavior
[What should happen]

## Actual Behavior
[What actually happens]

## Environment
- Browser: [e.g., Chrome 120]
- OS: [e.g., Windows 11]

## Screenshots
[If applicable]

## Additional Context
[Any other information]
```

### Feature Request
```markdown
## Description
[Brief description of the feature]

## Use Case
[Why is this feature needed?]

## Proposed Solution
[How should it work?]

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Additional Context
[Any other information]
```

## Workflow

1. **Create Issue** - Use proper title format and labels
2. **Create Local Docs** - Create `docs/{type}/{slug}/README.md`
3. **Assign** - Assign to team member
4. **Set Priority** - Add priority label
5. **Update Status** - Move through todo -> in-progress -> review -> done
6. **Link PR** - Reference issue number in PR (e.g., `Fixes #42`)
7. **Close Issue** - Close when PR is merged or issue is resolved

---

## Parent Issue with TaskList (Complex Issues)

For issues with larger scope, create a parent issue with a TaskList and child issues.

### Parent Issue Structure
```markdown
## Description
{Overview of the feature/refactor/bug}

## Reporter
**Unit:** {DQ/EE/PL/Dev}
**Name:** {Reporter Name}

## Scope
- [x] Frontend
- [x] Backend

## Tasks
- [ ] #{child-issue-1} - Task description
- [ ] #{child-issue-2} - Task description
- [ ] #{child-issue-3} - Task description

## Acceptance Criteria
- [ ] All child issues completed
- [ ] Tests pass
- [ ] Code reviewed
```

### Child Issue Structure
```markdown
## Description
{Specific task description}

## Parent Issue
Tracked by #{parent-issue-number}

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2

## Definition of Done
- [ ] Implementation complete
- [ ] Tests written
- [ ] Documentation updated (if applicable)
```

### Child Issue Title Format
```
[Component] Parent: Specific task
```

Example:
- Parent: `[Frontend] Add logger tabs feature`
- Child 1: `[Frontend] Logger tabs: Create tab component`
- Child 2: `[Frontend] Logger tabs: Implement tab switching logic`
- Child 3: `[Backend] Logger tabs: Add API endpoint for tab data`

---

## Closing Issues from PR

When a PR is merged, close all related issues:

### Single Issue
In PR description or commit message:
```
Fixes #42
```

### Multiple Issues (Parent + Children)
In PR description:
```
Fixes #42
Fixes #43
Fixes #44
Closes #40
```

Or use `/issue close-pr <PR-number>` to automatically close all linked issues.

## GitHub CLI Commands Reference

### Create Issue
```bash
gh issue create --title "[Component] Title" --body "Description" --label "bug,P1-high,frontend"
```

### List Issues
```bash
gh issue list
gh issue list --label "bug"
gh issue list --assignee "@me"
```

### Update Issue
```bash
gh issue edit <number> --add-label "in-progress"
gh issue edit <number> --remove-label "todo"
gh issue edit <number> --add-assignee "username"
```

### Close Issue
```bash
gh issue close <number>
gh issue close <number> --comment "Fixed in PR #XX"
```

### View Issue
```bash
gh issue view <number>
```

### Create Child Issue (linked to parent)
```bash
gh issue create --title "[Component] Parent: Task" --body "Tracked by #<parent>" --label "feature,P2-medium,frontend"
```

### Add TaskList to Parent Issue
```bash
gh issue edit <number> --body "$(gh issue view <number> --json body -q .body)

## Tasks
- [ ] #<child-1>
- [ ] #<child-2>
"
```

### Close All Issues from PR
```bash
# Get PR linked issues
gh pr view <pr-number> --json closingIssuesReferences -q '.closingIssuesReferences[].number'

# Close each issue
gh issue close <number> --comment "Fixed in PR #<pr-number>"
```
