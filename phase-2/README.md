# Phase 2: publish your own, then contribute to ours

**Roughly 90 minutes.** Two halves, one question asked twice: *what does it take to
get a change from your machine into a repository other people can see?*

First about a repository you own, where the answer turns out to be almost nothing.
Then about one you do not own, which is the entire rest of this phase.

Every step states what is true **before** the command, the command, and what is true
**after**. If you cannot say what changed, run it again and look properly before
moving on.

| Subphase | What changes |
|---|---|
| 2.1 | No repo, try to publish, refused |
| 2.2 | Untracked folder becomes tracked, staged, committed |
| 2.3 | Committed locally becomes live on GitHub, under your name |
| 2.4 | *(no command)* why nobody gets direct write access to a shared repo |
| 2.5 | Locked repo cloned, branched, edited, committed, entirely locally |
| 2.6 | Push attempted against the locked repo, refused |
| 2.7 | A copy you own is constructed, the same push succeeds |
| 2.8 | Your copy, frozen at fork time, gets synced |
| 2.9 | Branch pushed becomes a request to include it |
| 2.10 | Request reviewed, accepted, our repository changes |

---

# Part A: publishing something you own

In Phase 1 you built a history in `Git-Started` and then deliberately stopped. It is
still on your laptop, invisible to everyone. This half is the one way trip from there
to a real URL, with nobody else involved at any point.

We start in a fresh folder rather than `Git-Started`, because the first thing worth
seeing is what happens when you try to publish a folder git has never touched, and
`Git-Started` is already a repository.

## 2.1: try to publish it, and let the refusal explain itself

**Before:** a folder with a file in it. No `.git`. No relationship to GitHub of any
kind.

```bash
mkdir my-notes
cd my-notes
echo "Things I learned tonight" > notes.md
gh repo create my-notes --private --source=. --push
```

**After:** nothing exists on GitHub. Refused:

```
current directory is not a git repository. Run `git init` to initialize it
```

`gh` never contacted GitHub at all. It checked exactly one thing, got the answer no,
and stopped before opening a single connection.

**Ask the room:** "What precisely is missing here?" Not permissions. Not an account.
A commit. That is the whole gap. Nothing is refusing *you*, there is simply nothing
saved yet to send.

## 2.2: save it properly, before anyone else is involved

**Before:** no `.git`, as just established.

```bash
git init
git status
```

Everything shows as untracked. Git can see the folder and has recorded nothing about
it yet, exactly as in Phase 1.

**Every way to stage, and what each one actually does:**

| Command | What it stages |
|---|---|
| `git add <file>` | one named file |
| `git add folder/` | everything inside that folder |
| `git add .` | everything at or below where you are standing |
| `git add -A` | everything in the whole repo including deletions, wherever you stand |
| `git add -p` | each changed hunk one at a time, accept or skip individually |

```bash
git add .
git commit -m "Initial commit"
```

**A shortcut with a real trap in it:**

```bash
git commit -am "message"
```

That stages and commits in one step, but only for files git **already knows about**.

**Ask the room:** "You create a brand new file after your last commit. Does `-am` pick
it up?" It does not, and it does not warn you either. New files always need an
explicit `git add` first, however well drilled the `-am` habit gets. This is the most
common "wait, where did my file go" moment in any buildathon.

## 2.3: run the identical command again

**Before:** one local commit exists. Still nothing on GitHub.

```bash
gh repo create my-notes --private --source=. --push
```

**After:** a repository exists on GitHub under your account, `origin` is configured
locally pointing at it, and your commit exists in both places.

**Ask the room:** "Compare that command, character for character, with 2.1's." They
are identical. Only the folder underneath it changed. The command was telling the
truth about its precondition the entire time.

`Git-Started` from Phase 1 is already a repository, so the same one line publishes it
whenever you want it on your profile:

```bash
cd ../Git-Started
gh repo create my-poems --public --source=. --push
```

**Hold on to what just happened, because Part B inverts it.** You went from invisible
to live and owned by you, and there was nobody to ask, because the thing had no owner
but you. Part B is a repository that already has an owner, and it is not you.

**Two starting points this command handles:**

```bash
# Mode 1: the code already exists locally, which is what you just did
gh repo create <name> --private --source=. --remote=origin --push

# Mode 2: nothing exists yet, let GitHub build the folder
gh repo create <name> --private --clone
```

Mode 2 makes an empty repository on GitHub *and* clones it down as a new folder, and
you move files in afterwards. Use Mode 1 whenever the code came first, which is most
of the time.

**The full flag set:**

| Group | Flags |
|---|---|
| Visibility, pick exactly one | `--public`, `--private`, `--internal` (orgs only) |
| Metadata | `--description "<text>"`, `--homepage <url>` |
| Source and output | `--source <path>`, `--clone`, `--remote <name>`, `--push` |
| Scaffolding for a fresh repo | `--add-readme`, `--gitignore <template>`, `--license <template>` |
| Org | `--team <name>` |
| Templates | `--template <owner/repo>`, `--include-all-branches` |
| Feature toggles | `--disable-issues`, `--disable-wiki` |

**One caveat.** `--add-readme`, `--gitignore` and `--license` assume you are building
from nothing. Combine them with `--source` on a folder that already has commits and
they will not do what you expect, because that folder has already decided what is in
it. Real `.gitignore` work, and what to do about a secret that has already reached a
commit, is in the handbook.

**What `--push` actually replaced:**

```bash
git remote add origin https://github.com/<you>/<name>.git
git branch -M main
git push -u origin main
```

Three lines, one flag. Nothing more magical than that.

---

# Part B: contributing to something you do not own

## 2.4: why nobody just gets write access

No command for this one.

**Ask the room:** "We are collecting one poem file from every person here, into this
repository. Simplest possible setup: give all forty of you write access. What
breaks?"

Land it properly. One careless push overwrites somebody else's work. Nobody can tell
who broke what without reading the entire history. And there is no point at which
anyone looks at a change *before* it is in the project, because it is in the project
the moment it is pushed. That is true at forty people and just as true at two, the
moment more than one person cares what the final version says.

**The fix is not "be more careful".** It is structural. Nobody writes into the real
repository directly. Everyone proposes from a copy they own, and exactly one person
decides what actually lands. Everything below is that structure, one piece at a time.

## 2.5: clone it and do real work, nothing stops you yet

**Before:** `accelerate-muj/git-started` exists and you are not a collaborator on it.

```bash
git clone https://github.com/accelerate-muj/git-started.git
cd git-started
git switch -c poem/<your-github-username>
```

**Watch the folder name.** Your Phase 1 folder is `Git-Started` and this clone is
`git-started`. On Windows and Mac those look identical to you and different to the
terminal. Run `pwd` if you are ever unsure which one you are standing in, because
ten minutes of typing into the wrong folder is the single most common way to lose
this part of the evening.

Now write your file. One file, named after your GitHub username:

```bash
echo "# Sonnet 18, my way" > phase-2/poems/<your-github-username>.md
```

Put whatever you like in it. Sonnet 18 in modern English, in Hindi or Hinglish, as a
group chat, as a parody keeping the rhyme scheme, or a straight annotation of what
each line means. There is a worked example in [`poems/`](poems/).

```bash
git diff
git add phase-2/poems/<your-github-username>.md
git commit -m "Add <your-github-username>'s take on Sonnet 18"
```

Note `git add` with the actual filename rather than `git add .`. It is a good reflex:
`git add .` stages everything, including the three files you forgot you touched.

**Ask the room:** "Did any of that fail, warn you, or ask permission?" No. Clone,
branch, edit, diff, commit: every one ran entirely on your own machine and never once
checked whether you are allowed to touch our copy. Whatever "you do not have access"
is going to mean, it clearly is not about any of this.

## 2.6: push, which is the first thing that actually checks

**Before:** a commit exists locally on your branch. `origin` still points at our
repository, unchanged since you cloned.

```bash
git push -u origin poem/<your-github-username>
```

**After:** nothing changed remotely. Refused:

```
remote: Permission to accelerate-muj/git-started.git denied
fatal: unable to access ... 403
```

**Ask the room:** "You were not stopped at clone, or branch, or edit, or commit. Only
here. What does that tell you about what git is actually protecting?"

Land it: nothing you do on your own machine is ever restricted. The one locked door
is the moment you try to write into a copy you do not own. Your commit is not lost.
It is exactly where you left it. It just has nowhere to go yet.

## 2.7: construct a copy you actually own

**Before:** a local commit that cannot reach anywhere but your laptop.

```bash
gh repo fork accelerate-muj/git-started
git remote -v
```

`origin` still resolves to `accelerate-muj/git-started`, because forking does not
retroactively rewire a clone you made before you forked. Fix the labels so they mean
what they normally mean:

```bash
git remote rename origin upstream
git remote add origin https://github.com/<your-github-username>/git-started.git
git remote -v
```

```
origin    https://github.com/<your-github-username>/git-started.git
upstream  https://github.com/accelerate-muj/git-started.git
```

That naming pair is a near universal convention. When a project's contributing guide
says "sync with upstream", this is what it means.

Now push the exact same commit that failed a moment ago:

```bash
git push -u origin poem/<your-github-username>
```

It works.

**Ask the room:** "What is actually different between this push and the one that just
failed?" Nothing about the commit. It is byte for byte identical. The only thing that
changed is what `origin` resolves to. That is the entire function of a fork: not a
copy of your work, a copy of the *destination*, one with your name on it that you are
allowed to write into.

*(Next time: `gh repo fork accelerate-muj/git-started --clone` does the fork, the
clone and both remotes in one line. Worth doing it by hand once so the shortcut is
not a mystery.)*

## 2.8: your copy does not update itself

**Before:** your fork is frozen at whatever our repository looked like the moment you
forked it. Thirty other people are merging work in tonight and your fork has no idea
unless you ask.

```bash
git fetch upstream
git merge upstream/main
```

`Already up to date.` for now. This is the habit that stops your work from quietly
contradicting somebody else's an hour later.

## 2.9: the request

**Ask the room:** "You want us to add your file. In a shared live document, what is
the actual built in mechanism for proposing a change without simply making it?"
Suggesting mode is the closest thing, and it still lives inside the one document
everybody is editing at once. There is no version of it where you hold your own
complete copy and ask for it to be brought in.

```bash
gh pr create \
  --repo accelerate-muj/git-started \
  --title "Add <your-github-username>" \
  --body "My take on Sonnet 18."
```

This is a computed object, not a claim. GitHub compares your branch against ours and
produces an exact, reviewable difference. That is the real reason this whole fork
structure exists rather than handing out write access: it is the only arrangement
where a change can be inspected *before* it lands.

**`--repo` is the address on the envelope.** Your terminal has never heard of us.
Leave it off and the request files against your own fork, where it does nothing:

```bash
gh repo set-default accelerate-muj/git-started
```

**Ask the room:** "Your branch has five commits on it. Does the request send all five,
or do you choose?" You do not choose. It sends the full difference between your
branch and ours, every time. If you want fewer commits in it, take them off the
branch first. The branch *is* the unit being compared, which is why there is no per
commit selector anywhere in the interface.

It is not frozen at creation either. If our repository changes while your request is
open, the comparison updates live against wherever we now stand.

```bash
gh pr list --repo accelerate-muj/git-started
gh pr view --web
```

A bot comments within a minute confirming your filename is right. It does not block
anything, it just means whoever is merging can move quickly.

## 2.10: we accept it

```bash
gh pr review <number> --repo accelerate-muj/git-started --approve
gh pr merge <number> --repo accelerate-muj/git-started --merge
```

Your file is now in the real repository, publicly, with your name against it. Catch
your own copy up:

```bash
git switch main
git fetch upstream
git merge upstream/main
ls phase-2/poems/
```

You now have everybody else's files too. That is the full loop working exactly as
designed, for one contributor at a time.

**Why nobody conflicted.** Every person wrote to a different filename, because GitHub
usernames are unique. Thirty requests merged in a row and not one touched a line
another one touched. That was not luck, that was the filename rule doing its job.

Which leaves the obvious question, and we are deliberately leaving it open: what
happens the day two of you genuinely need to change the same line? That is a real
problem with a real answer, and it is the whole of the next workshop.

---

## Comprehension checkpoint

1. What exactly does `gh repo create --source=.` need before it will even talk to
   GitHub?
2. Will `git commit -am` catch a file you created five minutes ago?
3. State the real difference between the failed `gh repo create` in 2.1 and the
   successful one in 2.3.
4. Why is "just give everyone write access" dangerous rather than merely untidy?
5. Every command in 2.5 succeeded. What does that tell you about what git protects,
   and when?
6. What is genuinely different between the refused push and the successful one?
7. What can a shared live document not do that a pull request does automatically?
8. Can a pull request send only some of your branch's commits? What would you do if
   you wanted fewer?

---

## Condensed command reference

```bash
# 2.1 try to publish, observe the refusal
mkdir my-notes && cd my-notes
echo "Things I learned tonight" > notes.md
gh repo create my-notes --private --source=. --push

# 2.2 save it properly
git init
git status
git add .                # or -A, or a path, or -p to review hunks
git commit -m "Initial commit"

# 2.3 same command, changed precondition, live
gh repo create my-notes --private --source=. --remote=origin --push

# 2.5 clone ours, work entirely locally
git clone https://github.com/accelerate-muj/git-started.git
cd git-started
git switch -c poem/<your-github-username>
echo "# Sonnet 18, my way" > phase-2/poems/<your-github-username>.md
git add phase-2/poems/<your-github-username>.md
git commit -m "Add <your-github-username>'s take on Sonnet 18"

# 2.6 push fails
git push -u origin poem/<your-github-username>

# 2.7 fork, rewire remotes, push again
gh repo fork accelerate-muj/git-started
git remote rename origin upstream
git remote add origin https://github.com/<your-github-username>/git-started.git
git push -u origin poem/<your-github-username>

# 2.8 sync with the real thing
git fetch upstream
git merge upstream/main

# 2.9 the request
gh pr create --repo accelerate-muj/git-started \
  --title "Add <your-github-username>" --body "My take on Sonnet 18."
gh pr list --repo accelerate-muj/git-started

# 2.10 accepted
gh pr review <number> --repo accelerate-muj/git-started --approve
gh pr merge <number> --repo accelerate-muj/git-started --merge

```

---

## Troubleshooting

| Symptom | Cause | Fix | Subphase |
|---|---|---|---|
| `current directory is not a git repository` | No commit exists yet | `git init`, `git add`, `git commit`, then re-run the same command | 2.1 to 2.3 |
| File missing after `git commit -am` | It was never staged before | `git add <file>` explicitly, then commit | 2.2 |
| `gh repo create` says the name already exists | Collides with a repo you already own | Pick another name, or `gh repo delete <old>` | 2.3 |
| `--gitignore` or `--license` did nothing | Combined with `--source` on a folder that already has commits | Those are for repositories built from nothing. See the handbook | 2.3 |
| `Permission denied` on push | `origin` still points at our repository | Fork, rename it to `upstream`, add your fork as `origin` | 2.6 to 2.7 |
| `fatal: not a git repository` | You are not inside the cloned folder | `cd git-started` | 2.5 |
| `remote origin already exists` | You added `origin` before renaming the old one | `git remote rename origin upstream` first | 2.7 |
| Request opened against your own fork | `--repo` was left off | Re-run with `--repo`, or run `gh repo set-default` once | 2.9 |
| Two forks under your name | `gh repo fork` was run twice | `gh repo delete <your-github-username>/git-started` | 2.7 |
| Bot says your filename is wrong | It is not `phase-2/poems/<your-github-username>.md` | Rename, commit, push again. It does not block the merge | 2.9 |

---

## Timing

| Subphase | Time |
|---|---|
| 2.1 try, get refused | 5 min |
| 2.2 save it properly | 8 min |
| 2.3 publish, full flag tour | 10 min |
| 2.4 why not just hand out access | 6 min |
| 2.5 clone and work locally | 8 min |
| 2.6 push, hit the wall | 5 min |
| 2.7 fork, rewire, push again | 10 min |
| 2.8 sync with upstream | 5 min |
| 2.9 the request | 12 min |
| 2.10 accepted | 5 min |
| Buffer | 10 min |

**Total: roughly 92 minutes.**

---

The sonnet all of this is built on is [`sonnet-18.md`](sonnet-18.md), in this folder.
