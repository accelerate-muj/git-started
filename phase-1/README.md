# Phase 1: git, and only git

**Roughly 30 minutes.** You will make a repository on your own machine and build a
real history inside it.

GitHub does not appear in this phase. No account, no browser, no internet. Not as a
teaser, and not because we ran out of time: the whole point is that everything below
works with your wifi switched off.

---

## Why we start offline

Almost everyone learns GitHub first and git second, and then spends years quietly
unsure which one is doing what. So for the next thirty minutes, GitHub does not
exist. Git is a program on your computer that records versions of a folder. It
worked this way for three years before GitHub was founded, and it still works with
no internet connection at all.

Phase 2 is where the other half arrives: publishing what you built here, and then
getting a change into a repository somebody else owns.

---

## Step 1: make a folder and claim it

```bash
mkdir Git-Started
cd Git-Started
git init
```

`git init` created a hidden folder called `.git`. Look at it:

```bash
ls -a
```

That `.git` directory **is** the repository. Everything git knows about your
project lives inside it: every version, every message, every branch. Delete it and
you have an ordinary folder again with no history. Copy it and you have copied the
entire project including all of its past.

## Step 2: write something

Copy [the sonnet](../phase-2/sonnet-18.md) into a file called `poems.txt`, then
change something. Rewrite a line in your own words, add a line of your own at the
bottom, translate a couplet into Hindi. It genuinely does not matter. You need a
file with your fingerprints on it.

```bash
git status
```

Git says `poems.txt` is **untracked**. It can see the file but it is not watching it
yet. Git never assumes you want a file recorded, which is why build output and
password files do not end up in your history by accident.

## Step 3: stage it

```bash
git add poems.txt
git status
```

Now it is a **change to be committed**. You have not saved anything yet. You have
put the file on a shelf called the staging area, which holds what will go into the
next commit.

People find the staging area annoying until the first time they need it. It exists
so you can split messy work into clean commits: you changed five files, three belong
to one idea and two belong to another, so you stage and commit them separately.

## Step 4: commit

```bash
git commit -m "Add my version of Sonnet 18"
```

That is a permanent snapshot. Look at it:

```bash
git log
```

You get a forty character hexadecimal string, your name, the date, your message.
That string is the commit's ID, and it is a hash of the commit's entire contents,
which is why git can tell instantly if anything has been tampered with. There is a
much longer version of that story in the handbook.

## Step 5: do it twice more

Make another change, then `git add` and `git commit` again. Do it a third time.

```bash
git log --oneline
```

Three lines, newest at the top. You have a history. This is the loop you will
repeat for the rest of your life as a programmer: change something, stage it,
describe it, record it.

## Step 6: see exactly what changed

Edit `poems.txt` again, but do not stage it yet.

```bash
git diff
```

Lines starting `-` are what was there. Lines starting `+` are what you replaced them
with. Now stage it and run the same command:

```bash
git add poems.txt
git diff
```

Nothing. `git diff` shows what is **unstaged**, and you just staged it all. To see
what is about to go into the commit instead:

```bash
git diff --staged
```

Two questions, two commands. "What have I changed but not shelved yet" and "what is
on the shelf right now". Mixing these up is the single most common early confusion.

## Step 7: work somewhere other than main

```bash
git switch -c experiment
```

You are now on a branch called `experiment`. Rewrite the sonnet badly, on purpose.
Commit it.

```bash
git switch main
cat poems.txt
```

Your bad rewrite is gone, and your good version is back, because the two commits
live on two different branches. Nothing was lost. Switch back and look:

```bash
git switch experiment
cat poems.txt
```

A branch is not a copy of your folder. It is a movable label pointing at one commit,
and `git switch` rewrites the files in your folder to match whatever that label
points at. That is why switching is instant even on a huge project.

```bash
git switch main
git merge experiment
```

If you liked the experiment, `merge` brings it into `main`. If you did not, delete
the branch with `git branch -d experiment` and nothing about `main` ever knew it
existed.

---

## Where your work lives right now

```bash
git log --oneline --all
```

Everything you just did is inside one `.git` folder on one laptop. Not backed up.
Not visible to anyone. If this machine dies tonight, so does all of it, and there is
no version of you that can prove any of this work happened.

That is not a flaw. It is just the half of the tool you have learned so far. Phase 2
is the other half: getting this onto the internet under your name, and then getting
a change of yours into a repository you do not own.

---

## You should now be able to answer

1. What exactly is the `.git` folder, and what happens if you delete it?
2. Why does git make you `add` before you `commit`? Name a case where that helps.
3. What is the difference between `git diff` and `git diff --staged`?
4. A branch is not a copy of your files. So what is it?
5. Where does your history live right now, and who else can see it?

---

**Next:** [Phase 2](../phase-2/), where GitHub finally shows up.
