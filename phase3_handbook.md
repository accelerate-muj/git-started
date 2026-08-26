# 🟠 Phase 3 – Team Collaboration & Merge Conflicts

### Scenario

Now the repository has **multiple collaborators** with direct write access. Everyone works on the same file (`team.txt`). Conflicts can arise when two people edit the same line.

### 1️⃣ Repository Creation (by the team lead)

```bash
gh repo create team-<team‑name> --public
mkdir team-<team‑name>
cd team-<team‑name>
git init
```

### 2️⃣ Initial `team.txt` Template

```bash
cat > team.txt << 'EOF'
# Team <Team Name>

## Members
1. Name: _______  Favorite language: _______  Fun fact: _______
2. Name: _______  Favorite language: _______  Fun fact: _______
3. Name: _______  Favorite language: _______  Fun fact: _______
4. Name: _______  Favorite language: _______  Fun fact: _______
5. Name: _______  Favorite language: _______  Fun fact: _______

## Team Goal
We are here to learn Git and _______
EOF
```

### 3️⃣ Commit & Push Initial Version

```bash
git add .
git commit -m "Initial team file"
git branch -M main
git remote add origin https://github.com/<leader‑username>/team-<team‑name>.git
git push -u origin main
```

### 4️⃣ Add Collaborators

Leader can invite teammates via the web UI or the CLI:

```bash
# Using GH CLI (requires maintainer permission)
gh api repos/<leader‑username>/team-<team‑name>/collaborators/<teammate‑username> -X PUT
```

Each teammate then clones the repository **directly** (no fork needed):

```bash
gh repo clone <leader‑username>/team-<team‑name>
cd team-<team‑name>
```

### 5️⃣ Work on Your Own Branch

```bash
git checkout -b add-<your‑name>
```

Edit `team.txt` and fill your slot, e.g.:

```text
1. Name: Rahul    Favorite language: Python    Fun fact: I can solve a Rubik's cube in 30 seconds
```

Stage, commit, push, and open a PR (same as Phase 2).

### 6️⃣ Handling Merge Conflicts

If another teammate’s PR merges first, your branch may diverge.

#### Pull Latest `main` into Your Branch

```bash
# Ensure you have the latest upstream `main`
git checkout main
git pull origin main

# Switch back and merge
git checkout add-<your‑name>
git merge main   # or: git rebase main
```

You’ll see conflict markers in `team.txt`:

```text
<<<<<<< HEAD
1. Name: Ananya   Favorite language: JavaScript  Fun fact: I love hiking
=======
1. Name: Rahul    Favorite language: Python      Fun fact: I can solve a Rubik's cube
>>>>>>> main
```

#### Resolve the Conflict

1. Keep **both** entries (or whichever is correct).
2. Delete the `<<<<<<< HEAD`, `=======`, `>>>>>>> main` lines.
3. Save the file so it looks like:

```text
1. Name: Rahul    Favorite language: Python      Fun fact: I can solve a Rubik's cube
2. Name: Ananya   Favorite language: JavaScript  Fun fact: I love hiking
3. Name: _______  Favorite language: _______  Fun fact: _______
```

#### Finalise

```bash
git add team.txt
git commit -m "Resolve conflict with Rahul's entry"
git push origin add-<your‑name>
```

Now the PR is conflict‑free and can be merged.

### 7️⃣ Maintaining the Team Repo

- **List open PRs**: `gh pr list`
- **View a PR**: `gh pr view <number>`
- **Merge** (as maintainer): `gh pr merge <number> --merge`
- After each merge, pull the latest `main` before starting new work:

```bash
git checkout main
git pull origin main
```

---

## ✅ Summary

- **Phase 2** – Fork, create a feature branch, push, and open a PR using the GitHub CLI.
- **Phase 3** – Direct collaboration, branch per‑person, resolve merge conflicts, and merge PRs responsibly.
- Keep `origin` (your fork/clone) and `upstream` (original) correctly configured.
- Use `git fetch`/`git merge` (or `rebase`) to stay up‑to‑date before pushing.
- Resolve conflicts by editing the file, removing conflict markers, and committing the resolution.

Happy Git‑hacking! 🚀
