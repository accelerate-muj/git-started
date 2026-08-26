# 📖 Phase 2 & 3 Handbook (Hinglish, Continuous Flow)

---

## 📂 Repository Reference

The workshop source material lives at:

[Git Started – Accelerate-Muj Repo](https://github.com/accelerate-muj/git-started/tree/main)

---

## 🟢 Phase 2 – Contributing to Someone Else's Repo

### 1️⃣ Fork & Clone

```bash
# One‑liner: fork *and* clone
gh repo fork <workshop-org>/<workshop-repo> --clone
cd <workshop-repo>
```

- `origin` ➜ **your fork** (write access)
- `upstream` ➜ **original repo** (read‑only)

### 2️⃣ Verify Remotes

```bash
git remote -v
```

You should see something like:

```
origin  https://github.com/<your-username>/<workshop-repo>.git (fetch)
origin  https://github.com/<your-username>/<workshop-repo>.git (push)
upstream  https://github.com/<workshop-org>/<workshop-repo>.git (fetch)
upstream  https://github.com/<workshop-org>/<workshop-repo>.git (push)
```

If `upstream` is missing, add it manually:

```bash
git remote add upstream https://github.com/<workshop-org>/<workshop-repo>.git
```

### 3️⃣ Keep Your Fork Up‑to‑Date

```bash
git fetch upstream
git merge upstream/main   # or: git rebase upstream/main
```

### 4️⃣ Work on a Feature Branch

```bash
# Create a short‑lived branch
git checkout -b add-<your-name>
# or modern alternative
# git switch -c add-<your-name>
```

### 5️⃣ Make Your Changes

```bash
# Example personal file
echo "Hi, I'm <your-name>. I'm learning Git at this workshop!" > <your-name>.txt

# Append signature to existing sonnet
sed -i '$ a Written by <your-name>' sonnet.txt   # or edit manually
```

### 6️⃣ Stage & Commit

```bash
git add .
git commit -m "Add <your-name> and sign the sonnet"
```

### 7️⃣ Push Your Branch

```bash
# First push creates the remote tracking branch
git push -u origin add-<your-name>
```

`-u` links the local branch to the remote so future `git push`/`git pull` need no extra arguments.

### 8️⃣ Open a Pull Request (PR)

```bash
# Minimal command – GH auto‑detects upstream repo & branches
gh pr create --title "Add <your-name>" \
    --body "Added my file and signed the sonnet."
```

*Optional shortcuts*
- `--fill` → auto‑fill title & body from the last commit.
- `--draft` → create a draft PR for early feedback.
- `--reviewer <username>` → request a review.
- `--label documentation` → add a label.

---
