# Phase 2: fork, branch, pull request

**Roughly 40 minutes.** You will add a file to *this* repository, which you do not
have permission to write to, by forking it and opening a pull request.

Nobody in this phase will hit a merge conflict. That is deliberate, and Phase 3
will fix it.

---

## The problem this solves

You cannot push to `accelerate-muj/git-started`. You are not a collaborator on it.
This is not an obstacle to work around, it is how essentially every open source
project on earth stays sane: strangers cannot write to the project directly, but
anyone can propose a change.

The mechanism has three parts:

1. **Fork.** Your own server side copy of the whole repo, which you fully control.
2. **Branch.** A named line of work inside that copy.
3. **Pull request.** A request that we pull your branch into our repo, plus a place
   to discuss it before anyone does.

## Step 1: fork and clone in one command

```bash
gh repo fork accelerate-muj/git-started --clone
cd git-started
```

Now look at what that set up:

```bash
git remote -v
```

Two remotes:

- **`origin`** points at *your* fork. You can push here.
- **`upstream`** points at *our* repo. You cannot push here, but you can fetch from it.

That pair of names is a near universal convention. When you read a project's
contributing guide and it says "sync with upstream", this is what it means.

## Step 2: branch

```bash
git switch -c poem/<your-github-username>
```

Use your real GitHub username, so for example `git switch -c poem/theqmlguy`.

Branching before you work is a habit worth forming now. It keeps `main` clean, it
lets you have several unfinished ideas at once, and it means the pull request you
open contains only the thing you meant to propose.

## Step 3: write your file

Create exactly one file:

```
phase-2/poems/<your-github-username>.md
```

The filename rule is what makes this phase conflict free. Your username is unique
on GitHub, so no two people can create the same file, so nobody's change can
overlap with anybody else's. Thirty pull requests will merge in a row without a
single collision.

Put whatever you want inside. Some ideas that have worked well:

- Sonnet 18 rewritten in modern English
- Sonnet 18 rewritten in Hindi, or Hinglish, or your first language
- Sonnet 18 as a group chat
- A parody with the same rhyme scheme
- A straight annotation explaining what each line means

There is a worked example in [`poems/`](poems/) if you want to see the shape of one.

## Step 4: commit and push

```bash
git add phase-2/poems/<your-github-username>.md
git commit -m "Add <your-github-username>'s take on Sonnet 18"
git push -u origin poem/<your-github-username>
```

`git add` with the specific filename rather than `git add .` is a good reflex.
`git add .` stages everything, including files you forgot you touched.

## Step 5: open the pull request

```bash
gh pr create --repo accelerate-muj/git-started --fill
```

`--fill` uses your commit message as the title and body, which is fine here. For
real work write them by hand, because the description is where you explain *why*
you did something, and that is the part reviewers actually need.

Watch it:

```bash
gh pr status
gh pr view --web
```

A bot will comment within a minute confirming your file is named correctly. It does
not block anything, it just means whoever is merging can move fast.

## Step 6: watch it merge

Your PR gets merged live. When it does, your file is in the real repository, with
your name in the contributor list, permanently and publicly.

Then update your local copy:

```bash
git switch main
gh repo sync <your-github-username>/git-started
git pull
ls phase-2/poems/
```

You now have everyone else's files too. Your fork was behind by thirty commits and
`gh repo sync` caught it up.

---

## If you want to go further in this phase

**Review somebody else's:**

```bash
gh pr list
gh pr view <number>
gh pr checkout <number>
```

That last one puts their branch on your machine so you can actually run and read
their work, then `git switch main` to come back. Reviewing code you can only see as
a diff in a browser is much harder than people admit.

**Comment on one:**

```bash
gh pr comment <number> --body "This rhyme in line 4 is very good"
```

---

## You should now be able to answer

1. What is the difference between `origin` and `upstream`?
2. Why did the filename rule guarantee nobody would conflict?
3. Your fork is thirty commits behind. What command fixes that?
4. Is a pull request a git feature or a GitHub feature?

That last one catches people. Pull requests are **not** part of git. Git has no
idea what a PR is. It is a GitHub product built on top of git branches, which is
exactly why you need `gh` and not `git` to make one.

---

**Next:** [Phase 3](../phase-3/), where we remove the safety net.
