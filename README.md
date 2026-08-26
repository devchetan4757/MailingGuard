# GitHub Team Workflow

This guide explains the basic Git/GitHub workflow for working with this repository.

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

---

## 1. Clone the Repository

Clone the repository:

```bash
git clone https://github.com/devchetan4757/MailingGuard.git
```

Enter the repository:

```bash
cd MailingGuard
```

Check the current status:

```bash
git status
```

---

## 2. Check Your Current Branch

```bash
git branch
```

Example output:

```
* main
```

The `*` shows the branch you are currently working on.

---

## 3. Get the Latest Changes

Before starting new work, always update your local `main`:

```bash
git checkout main
git pull origin main
```

---

## 4. Create Your Own Branch

Never work directly on `main`.

Create a new branch:

```bash
git checkout -b feature/<feature-name>
```

Examples:

```bash
git checkout -b feature/login
git checkout -b feature/dashboard
git checkout -b feature/file-upload
```

---

## 5. Check Your Branch

```bash
git branch
```

Example output:

```
  main
* feature/login
```

You are now working on your feature branch.

---

## 6. Make Your Changes

Work normally and save your files.

Check what changed:

```bash
git status
```

To see the exact changes:

```bash
git diff
```

---

## 7. Add Your Changes

Add all changed files:

```bash
git add .
```

Or add a specific file:

```bash
git add <file-path>
```

Check again:

```bash
git status
```

---

## 8. Commit Your Changes

Create a meaningful commit:

```bash
git commit -m "Describe what you changed"
```

Good examples:

```bash
git commit -m "Add login page"
git commit -m "Fix navbar layout"
git commit -m "Update API integration"
```

Avoid vague messages like:

- ❌ `update`
- ❌ `changes`
- ❌ `done`
- ❌ `final`

Use a message that explains what was actually changed.

---

## 9. Push Your Branch to GitHub

The first time you push a new branch:

```bash
git push -u origin feature/<feature-name>
```

Example:

```bash
git push -u origin feature/login
```

After the first push, you can simply run:

```bash
git push
```

---

## 10. Create a Pull Request

After pushing your branch:

1. Open the repository on GitHub.
2. GitHub should show your recently pushed branch.
3. Click **Compare & pull request**.
4. Make sure:
   - **Base:** `main`
   - **Compare:** `feature/<your-feature>`
5. Add a short description of your changes.
6. Add a reviewer if required.
7. Create the Pull Request.

---

## 11. After Your Pull Request Is Merged

Once your Pull Request has been merged:

Switch back to `main`:

```bash
git checkout main
```

Get the latest version:

```bash
git pull origin main
```

Delete your old local branch:

```bash
git branch -d feature/<feature-name>
```

If the branch still exists on GitHub:

```bash
git push origin --delete feature/<feature-name>
```

---

## 12. Starting Another Task

Always start from the latest `main`:

```bash
git checkout main
git pull origin main
```

Create a new branch:

```bash
git checkout -b feature/<new-feature>
```

Then repeat the cycle:

```
Code → Test → git status → git add . → git commit → git push → Pull Request → Review → Merge
```

---

## 13. If Someone Else Updated main

If another teammate merged changes while you were working:

First save your work:

```bash
git add .
git commit -m "Save current work"
```

Update `main`:

```bash
git checkout main
git pull origin main
```

Return to your branch:

```bash
git checkout feature/<feature-name>
```

Bring the latest `main` into your branch:

```bash
git merge main
```

Then continue working.

---

## 14. Merge Conflicts

If Git reports a conflict:

```bash
git status
```

Git will show which files have conflicts. You may see something like this inside the file:

```
<<<<<<< HEAD
Your changes
=======
Changes from main
>>>>>>> main
```

Edit the file and decide which changes should remain, then remove the conflict markers:

```
<<<<<<<
=======
>>>>>>>
```

Stage the resolved file:

```bash
git add .
```

Commit the resolution:

```bash
git commit -m "Resolve merge conflict"
```

Then push:

```bash
git push
```

> If you are unsure how to resolve a conflict, ask the person responsible for that code before changing it.

---

## 15. Useful Commands

| Action | Command |
|---|---|
| Check status | `git status` |
| See branches | `git branch` |
| Switch branches | `git checkout <branch-name>` |
| Create and switch to a branch | `git checkout -b <branch-name>` |
| Download latest changes | `git pull` |
| See commit history | `git log --oneline` |
| See changes | `git diff` |
| Stage changes | `git add .` |
| Commit | `git commit -m "Message"` |
| Push | `git push` |

---

## 16. Recommended Branch Names

**Features**

```
feature/<name>
```

Examples:

```
feature/login
feature/navbar
feature/file-upload
```

**Bug fixes**

```
fix/<name>
```

Examples:

```
fix/login-validation
fix/mobile-layout
```

**Refactoring**

```
refactor/<name>
```

Example:

```
refactor/api-client
```

---

## 17. Basic Workflow to Remember

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

Always follow this cycle:

```
main → feature branch → changes → commit → push → Pull Request → review → merge
```
