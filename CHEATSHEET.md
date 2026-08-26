# Cheatsheet

One page. Print it, or keep it open in a second tab.

---

## The mental model

Git has three places your work can be. Every basic command is just moving
something from one to the next.

```
  working directory  →  staging area  →  repository  →  remote
       (your edits)      (git add)       (git commit)   (git push)
```

`git status` tells you where everything currently sits. When you are lost, run it.
It is the single most useful command in git and it is impossible to break anything
with it.

---

## Starting out

| Command | What it does |
|---|---|
| `git init` | Turn the current folder into a repository |
| `git clone <url>` | Copy someone else's repository to your machine |
| `git status` | Where is everything right now |
| `git add <file>` | Stage a file for the next commit |
| `git add .` | Stage everything changed |
| `git commit -m "message"` | Record the staged changes permanently |
| `git log --oneline` | List commits, one line each |
| `git diff` | What have I changed but not staged |
| `git diff --staged` | What have I staged but not committed |

## Branches

| Command | What it does |
|---|---|
| `git branch` | List branches |
| `git switch -c <name>` | Make a branch and move to it |
| `git checkout -b <name>` | The older spelling of the same thing |
| `git switch <name>` | Move to an existing branch |
| `git merge <name>` | Pull another branch's work into this one |
| `git branch -d <name>` | Delete a branch you have finished with |

`git switch` replaced `git checkout` for this in 2019. `checkout` still works, but
it does two unrelated jobs and that is exactly why it confused everyone for a decade.

## Remotes

| Command | What it does |
|---|---|
| `git remote -v` | Which GitHub repos does this folder talk to |
| `git remote add <name> <url>` | Save a long URL under a short name |
| `git fetch <remote>` | Download their commits, change nothing locally |
| `git merge <remote>/main` | Merge what you just fetched into your branch |
| `git pull` | Fetch, then merge into your branch |
| `git push` | Send your commits up |
| `git push -u origin <branch>` | Push a new branch and remember the pairing |

`fetch` is safe and never changes your files. `pull` is `fetch` plus a merge, which
can conflict. When you want to know what changed upstream without any risk, fetch.

Remote names are per folder, not global. Every repo has its own `.git/config`, so
every folder gets its own `origin`. By convention `origin` is your fork and
`upstream` is the project you forked from.

## Conflicts

| Command | What it does |
|---|---|
| `git status` | Which files are conflicted |
| `git diff` | Show the conflicting regions |
| `git add <file>` | Mark a conflict as resolved |
| `git rebase --continue` | Carry on after resolving during a rebase |
| `git merge --abort` | Undo the merge, go back to before |
| `git rebase --abort` | Same, for a rebase |

Nothing is ever lost while you are in a conflict. `--abort` always exists.

---

## git vs gh

Two tools, two jobs. `git` moves commits. `gh` does the things that only exist
because GitHub exists.

| I want to | Command |
|---|---|
| Make a repo on GitHub from this folder | `gh repo create --source=. --public --push` |
| Fork a repo and clone my fork | `gh repo fork <owner>/<repo> --clone` |
| Update my fork from the original | `gh repo sync <me>/<repo>` |
| Open a pull request | `gh pr create --fill` |
| See my open pull requests | `gh pr status` |
| List a repo's pull requests | `gh pr list` |
| Read one in the terminal | `gh pr view <number>` |
| Check out someone's PR locally | `gh pr checkout <number>` |
| Merge one | `gh pr merge <number>` |
| Open the repo in a browser | `gh repo view --web` |
| Anything GitHub's API can do | `gh api ...` |

### Building `gh pr create`

The base command is `gh pr create`. Every flag answers one question GitHub still
has. With `upstream` configured, it works out the destination repo, the source
branch and the target branch on its own, so most of these are optional.

| Flag | Answers |
|---|---|
| `--title` | The line shown in the pull request list |
| `--body` | The description underneath it |
| `--fill` | Use my last commit message for both |
| `--draft` | Not finished. Cannot merge until marked ready |
| `--reviewer <user>` | Ask a specific person to look |
| `--assignee <user>` | Put it in somebody's name |
| `--label <label>` | Tag it |
| `--web` | Fill the form in a browser instead of the terminal |
| `--repo <owner>/<repo>` | Force the destination when `gh` guesses wrong |

A pull request is a **comparison between two branches that are already on GitHub**,
not an upload. That is why the order is always commit, then push, then PR. If your
work is only on your laptop there is nothing for GitHub to compare.

---

## The five that save you

| Command | When |
|---|---|
| `git status` | Always. Whenever you are unsure. |
| `git log --oneline --graph --all` | See the actual branch shape |
| `git reflog` | You lost a commit. It is in here. It is almost always in here. |
| `git restore <file>` | Undo edits to a file you have not committed |
| `git commit --amend` | Fix the message or contents of the commit you just made |

`git reflog` is the one to remember. Git keeps a log of everywhere `HEAD` has been
for ninety days, including commits you "deleted". Losing work in git takes real
effort.
