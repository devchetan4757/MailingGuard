# GitHub Team Workflow

This guide explains the Git/GitHub workflow for this repository, step by step.

**No prior Git experience needed.** Just follow the steps in order. Every command tells you what it does and what you should see happen. If something looks different from the example, stop and check the [Troubleshooting](#troubleshooting) section before continuing.

## Table of Contents

1. [Clone the Repository](#1-clone-the-repository)
2. [Check Your Current Branch](#2-check-your-current-branch)
3. [Get the Latest Changes](#3-get-the-latest-changes)
4. [Create Your Own Branch](#4-create-your-own-branch)
5. [Check Your Branch](#5-check-your-branch)
6. [Make Your Changes](#6-make-your-changes)
7. [Add Your Changes](#7-add-your-changes)
8. [Commit Your Changes](#8-commit-your-changes)
9. [Push Your Branch to GitHub](#9-push-your-branch-to-github)
10. [Create a Pull Request](#10-create-a-pull-request)
11. [After Your Pull Request Is Merged](#11-after-your-pull-request-is-merged)
12. [Starting Another Task](#12-starting-another-task)
13. [If Someone Else Updated main](#13-if-someone-else-updated-main)
14. [Merge Conflicts](#14-merge-conflicts)
15. [Useful Commands](#15-useful-commands)
16. [Recommended Branch Names](#16-recommended-branch-names)
17. [Basic Workflow to Remember](#17-basic-workflow-to-remember)
18. [Golden Rule](#golden-rule)
19. [Troubleshooting](#troubleshooting)

---

## 1. Clone the Repository

"Cloning" downloads a full copy of the repository onto your computer. **You only do this once**, the first time you set up the project.

```bash
git clone https://github.com/devchetan4757/MailingGuard.git
```

This creates a new folder called `MailingGuard` on your computer. Move into it:

```bash
cd MailingGuard
```

Confirm everything is in order:

```bash
git status
```

✅ You should see: `On branch main` and `nothing to commit, working tree clean`.

> If you already have the folder from before, **skip this step** — don't clone it again. Go to Step 3 instead.

---

## 2. Check Your Current Branch

A "branch" is your own separate copy of the code where you can safely make changes without affecting anyone else's work. Think of `main` as the official, working version of the project — nobody edits it directly.

```bash
git branch
```

Example output:

```
* main
```

The `*` marks the branch you're currently on. Right after cloning, you'll always be on `main`.

---

## 3. Get the Latest Changes

**Do this every single time before you start new work**, even if you did it yesterday. Teammates may have added changes since you last checked.

```bash
git checkout main
git pull origin main
```

- `git checkout main` — switches you to the `main` branch.
- `git pull origin main` — downloads the latest changes from GitHub into your local copy.

✅ You should see either `Already up to date.` or a summary of files that were updated. No errors.

---

## 4. Create Your Own Branch

**Never write code directly on `main`.** Always create a new branch first — this keeps `main` safe and stable at all times.

```bash
git checkout -b feature/<feature-name>
```

Replace `<feature-name>` with a short, clear description of what you're building (no spaces — use dashes).

```bash
git checkout -b feature/login
git checkout -b feature/dashboard
git checkout -b feature/file-upload
```

See [Recommended Branch Names](#16-recommended-branch-names) for the naming rules (`feature/`, `fix/`, `refactor/`).

---

## 5. Check Your Branch

Double-check you're on the right branch before making changes:

```bash
git branch
```

Example output:

```
  main
* feature/login
```

The `*` should now be next to your feature branch, **not** `main`. If it's still on `main`, go back to Step 4 — you skipped creating your branch.

---

## 6. Make Your Changes

Now write your code and save your files normally in your code editor.

To see which files you've changed:

```bash
git status
```

Changed files will show up in red (unstaged).

To see the exact line-by-line changes you made:

```bash
git diff
```

> Press `q` to exit the diff view if it opens a scrolling screen.

---

## 7. Add Your Changes

"Adding" (or "staging") tells Git which changes you want to include in your next commit.

Add everything you changed:

```bash
git add .
```

Or, to be more careful and add just one file:

```bash
git add <file-path>
```

Check that it worked:

```bash
git status
```

✅ Your changed files should now show up in **green** instead of red — this means they're staged and ready to commit.

---

## 8. Commit Your Changes

A "commit" is a saved snapshot of your staged changes, with a message explaining what you did.

```bash
git commit -m "Describe what you changed"
```

**Good commit messages** (specific, describe *what* changed):

```bash
git commit -m "Add login page"
git commit -m "Fix navbar layout"
git commit -m "Update API integration"
```

**Avoid vague messages** that don't tell anyone anything:

- ❌ `update`
- ❌ `changes`
- ❌ `done`
- ❌ `final`

Rule of thumb: someone should understand what changed just by reading the message, without opening the code.

---

## 9. Push Your Branch to GitHub

"Pushing" uploads your commits from your computer to GitHub, so your team can see them.

**The very first time** you push a new branch, use `-u` (this links your local branch to GitHub):

```bash
git push -u origin feature/<feature-name>
```

Example:

```bash
git push -u origin feature/login
```

**Every push after that**, this shorter command is enough:

```bash
git push
```

✅ You should see a link in the terminal output that goes straight to a "Create pull request" page on GitHub — you can click it to jump to Step 10.

---

## 10. Create a Pull Request

A Pull Request (PR) is a request asking your team to review and merge your branch into `main`. **This is required — code never goes into `main` without one.**

1. Open the repository on GitHub.
2. GitHub usually shows a yellow banner with your recently pushed branch — click **Compare & pull request**. (If not, go to the **Pull requests** tab → **New pull request**.)
3. Make sure the direction is correct:
   - **Base:** `main` (where the code is going)
   - **Compare:** `feature/<your-feature>` (your branch)
4. Add a short, clear description: what you changed and why.
5. Add a reviewer if your team requires one.
6. Click **Create Pull Request**.

> ⚠️ Don't click "Merge" yourself unless your team says it's okay. Usually a teammate reviews and merges it for you.

---

## 11. After Your Pull Request Is Merged

Once someone has approved and merged your PR on GitHub, clean up locally:

Switch back to `main`:

```bash
git checkout main
```

Pull down the newly merged code (which now includes your changes):

```bash
git pull origin main
```

Delete your local feature branch — you don't need it anymore:

```bash
git branch -d feature/<feature-name>
```

If GitHub still shows the branch online too, delete it there as well:

```bash
git push origin --delete feature/<feature-name>
```

> This cleanup step is optional but keeps things tidy. Skipping it won't break anything.

---

## 12. Starting Another Task

Every new task starts the exact same way — from a clean, up-to-date `main`:

```bash
git checkout main
git pull origin main
```

Then create a fresh branch:

```bash
git checkout -b feature/<new-feature>
```

The full cycle, from start to finish:

```
main → new branch → code → test → git status → git add . → git commit → git push → Pull Request → Review → Merge
```

---

## 13. If Someone Else Updated main

This happens when a teammate's PR gets merged **while you're still working** on your own branch. Your branch is now "behind" — bring it up to date like this:

**Step 1 — Save your current work first** (don't skip this, or you may lose changes):

```bash
git add .
git commit -m "Save current work"
```

**Step 2 — Update your local `main`:**

```bash
git checkout main
git pull origin main
```

**Step 3 — Go back to your feature branch:**

```bash
git checkout feature/<feature-name>
```

**Step 4 — Bring the new `main` changes into your branch:**

```bash
git merge main
```

If Git says the merge completed with no conflicts, you're done — continue working. If it mentions conflicts, go to Step 14 below.

---

## 14. Merge Conflicts

A conflict happens when you and someone else changed the **same lines** of the **same file**. Git can't decide which version to keep, so it asks you to choose.

**Don't panic — this is normal and expected.** Here's how to fix it:

```bash
git status
```

This lists which files have conflicts (marked "both modified").

Open each conflicted file in your editor. You'll see markers like this inserted directly into the code:

```
<<<<<<< HEAD
Your changes
=======
Changes from main
>>>>>>> main
```

- Everything between `<<<<<<< HEAD` and `=======` is **your** version.
- Everything between `=======` and `>>>>>>> main` is **their** version.

**Manually edit the file** to keep whichever lines should actually remain (sometimes it's one side, sometimes a bit of both). Then **delete the marker lines themselves** — `<<<<<<<`, `=======`, and `>>>>>>>` should not remain in the file.

Once every conflict in the file is resolved, stage it:

```bash
git add .
```

Commit the resolution:

```bash
git commit -m "Resolve merge conflict"
```

Push as usual:

```bash
git push
```

> 🛑 **If you are unsure which version of the code is correct, stop and ask the teammate who wrote the conflicting code before you decide.** Guessing wrong can silently delete someone else's work.

---

## 15. Useful Commands

Quick reference — the commands you'll use constantly, all in one place.

| Action | Command | What it does |
|---|---|---|
| Check status | `git status` | Shows what's changed, staged, or on which branch you are |
| See branches | `git branch` | Lists all local branches, `*` marks current one |
| Switch branches | `git checkout <branch-name>` | Moves you to a different existing branch |
| Create and switch to a branch | `git checkout -b <branch-name>` | Creates a new branch and switches to it immediately |
| Download latest changes | `git pull` | Fetches and merges the latest code from GitHub |
| See commit history | `git log --oneline` | Shows a short list of past commits |
| See changes | `git diff` | Shows exact line-by-line edits not yet staged |
| Stage changes | `git add .` | Marks all changed files as ready to commit |
| Commit | `git commit -m "Message"` | Saves a snapshot of staged changes |
| Push | `git push` | Uploads your commits to GitHub |

---

## 16. Recommended Branch Names

Always prefix your branch name so anyone can tell what kind of work it contains, at a glance.

**Features** — new functionality

```
feature/<name>
```

```
feature/login
feature/navbar
feature/file-upload
```

**Bug fixes** — fixing something broken

```
fix/<name>
```

```
fix/login-validation
fix/mobile-layout
```

**Refactoring** — improving existing code without changing behavior

```
refactor/<name>
```

```
refactor/api-client
```

> Use dashes, not spaces or underscores, and keep names short and specific.

---

## 17. Basic Workflow to Remember

The 11 steps, every single time you do any task:

1. `git checkout main`
2. `git pull origin main`
3. `git checkout -b feature/<name>`
4. Make your changes
5. `git status`
6. `git add .`
7. `git commit -m "Describe changes"`
8. `git push -u origin feature/<name>`
9. Create Pull Request on GitHub
10. Review
11. Merge

---

## Golden Rule

**Never work directly on `main`.**

Always follow this cycle, no exceptions:

```
main → feature branch → changes → commit → push → Pull Request → review → merge
```

---

## Troubleshooting

**"fatal: not a git repository"**
You're not inside the project folder. Run `cd MailingGuard` first, then try again.

**`git status` shows files you didn't expect to see**
You might be on the wrong branch. Run `git branch` to check, and switch with `git checkout <branch-name>` if needed.

**"Your branch is behind 'origin/main'"**
Someone pushed changes you don't have yet. Run `git pull origin main` while on `main`.

**"error: failed to push some refs"**
Usually means GitHub has changes you don't have locally yet. Run `git pull` first, resolve any conflicts (see [Step 14](#14-merge-conflicts)), then push again.

**You made changes on `main` by accident**
Don't panic and don't push. Create a branch right now to save the work, then reset `main`:

```bash
git checkout -b feature/save-my-work
git checkout main
git reset --hard origin/main
```

Your changes are now safely preserved on `feature/save-my-work` instead.

**Still stuck?**
Run `git status` and share the exact output with a teammate — it almost always explains exactly what's going on.
