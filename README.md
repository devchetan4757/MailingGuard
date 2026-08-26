GitHub Team Workflow

This guide explains the basic Git/GitHub workflow for working with this repository.

---

1. Clone the Repository

Clone the repository:

git clone https://github.com/devchetan4757/MailingGuard.git

Enter the repository:

cd MailingGuard

Check the current status:

git status

---

2. Check Your Current Branch

git branch

Example:

* main

The "*" shows the branch you are currently working on.

---

3. Get the Latest Changes

Before starting new work, always update your local "main":

git checkout main
git pull origin main

---

4. Create Your Own Branch

Never directly work on "main".

Create a new branch:

git checkout -b feature/<feature-name>

Examples:

git checkout -b feature/login

git checkout -b feature/dashboard

git checkout -b feature/file-upload

---

5. Check Your Branch

git branch

Example:

  main
* feature/login

You are now working on your feature branch.

---

6. Make Your Changes

Work normally and save your files.

Check what changed:

git status

To see the exact changes:

git diff

---

7. Add Your Changes

Add all changed files:

git add .

Or add a specific file:

git add <file-path>

Check again:

git status

---

8. Commit Your Changes

Create a meaningful commit:

git commit -m "Describe what you changed"

Examples:

git commit -m "Add login page"

git commit -m "Fix navbar layout"

git commit -m "Update API integration"

Avoid messages like:

❌ update
❌ changes
❌ done
❌ final

Use a message that explains what was actually changed.

---

9. Push Your Branch to GitHub

The first time you push a new branch:

git push -u origin feature/<feature-name>

Example:

git push -u origin feature/login

After the first push:

git push

---

10. Create a Pull Request

After pushing your branch:

1. Open the repository on GitHub.
2. GitHub should show your recently pushed branch.
3. Click Compare & pull request.
4. Make sure:

Base: main
Compare: feature/<your-feature>

5. Add a short description of your changes.
6. Add a reviewer if required.
7. Create the Pull Request.

---

11. After Your Pull Request Is Merged

Once your Pull Request has been merged:

Switch back to "main":

git checkout main

Get the latest version:

git pull origin main

Delete your old local branch:

git branch -d feature/<feature-name>

If the branch still exists on GitHub:

git push origin --delete feature/<feature-name>

---

12. Starting Another Task

Always start from the latest "main":

git checkout main
git pull origin main

Create a new branch:

git checkout -b feature/<new-feature>

Then repeat:

Code
 ↓
Test
 ↓
git status
 ↓
git add .
 ↓
git commit
 ↓
git push
 ↓
Pull Request
 ↓
Review
 ↓
Merge

---

13. If Someone Else Updated "main"

If another teammate merged changes while you were working:

First save your work:

git add .
git commit -m "Save current work"

Update "main":

git checkout main
git pull origin main

Return to your branch:

git checkout feature/<feature-name>

Bring the latest "main" into your branch:

git merge main

Then continue working.

---

14. Merge Conflicts

If Git reports a conflict:

git status

Git will show which files have conflicts.

You may see:

<<<<<<< HEAD
Your changes
=======
Changes from main
>>>>>>> main

Edit the file and decide which changes should remain.

Remove the conflict markers:

<<<<<<<
=======
>>>>>>>

Then:

git add .

Commit the resolution:

git commit -m "Resolve merge conflict"

Then push:

git push

If you are unsure how to resolve a conflict, ask the person responsible for that code before changing it.

---

15. Useful Commands

Check status

git status

See branches

git branch

Switch branches

git checkout <branch-name>

Create and switch to a branch

git checkout -b <branch-name>

Download latest changes

git pull

See commit history

git log --oneline

See changes

git diff

Stage changes

git add .

Commit

git commit -m "Message"

Push

git push

---

16. Recommended Branch Names

Features

feature/<name>

Examples:

feature/login
feature/navbar
feature/file-upload

Bug fixes

fix/<name>

Examples:

fix/login-validation
fix/mobile-layout

Refactoring

refactor/<name>

Example:

refactor/api-client

---

17. Basic Workflow to Remember

1. git checkout main
2. git pull origin main
3. git checkout -b feature/<name>
4. Make your changes
5. git status
6. git add .
7. git commit -m "Describe changes"
8. git push -u origin feature/<name>
9. Create Pull Request on GitHub
10. Review
11. Merge

---

Golden Rule

Never work directly on "main".

Always:

main
 ↓
feature branch
 ↓
changes
 ↓
commit
 ↓
push
 ↓
Pull Request
 ↓
review
 ↓
merge
