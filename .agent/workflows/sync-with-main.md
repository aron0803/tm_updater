---
description: Pull latest updates from Main to current branch and check for conflicts
---

1. Fetch the latest changes from origin to ensure we have the most up-to-date Main.
// turbo
   `git fetch origin`

2. Attempt to merge origin/main into the current branch to see if there are conflicts.
   `git merge origin/main`

3. Check the command output from step 2.
   - **If the merge was successful** (output shows "Fast-forward", "Already up to date", or "Merge made by..."):
     - Tell the user the branch is now synced with Main.
   - **If there are conflicts** (output shows "CONFLICT"):
     - Run `git status` to show which files are in conflict.
     - **STOP** and report the conflicted files to the user.
     - Ask the user how they would like to resolve the conflicts (e.g. keep current, accept incoming, or manual edit).
     - **DO NOT** commit or push until conflicts are resolved direction is clear.
