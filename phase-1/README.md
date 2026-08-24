# Phase 1: your own repo

**Roughly 30 minutes.** You will make a repository on your own machine, put a poem
in it, and push it to your GitHub profile.

No forking, no pull requests, no other people. Just you and the tool.

---

## Why we start offline

Almost everyone learns GitHub first and git second, and then spends years quietly
unsure which one is doing what. So for the next fifteen minutes, GitHub does not
exist. Git is a program on your computer that records versions of a folder. It
worked this way for three years before GitHub was founded, and it still works with
no internet connection at all.

---

## Step 1: make a folder and claim it

```bash
mkdir my-sonnet
cd my-sonnet
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

Copy [the sonnet](../poem/sonnet-18.md) into a file called `sonnet.md`, then change
something. Rewrite a line in your own words, add a line of your own at the bottom,
translate a couplet into Hindi. It genuinely does not matter. You need a file with
your fingerprints on it.

```bash
git status
```

Git says `sonnet.md` is **untracked**. It can see the file but it is not watching it
yet. Git never assumes you want a file recorded, which is why build output and
password files do not end up in your history by accident.

## Step 3: stage it

```bash
git add sonnet.md
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

---

## Step 6: now GitHub exists

Your repo is real and complete, and it is only on your laptop. To put it online the
long way you would create a repo in the browser, copy its URL, add it as a remote,
and push. The GitHub CLI collapses all of that:

```bash
gh repo create my-sonnet --source=. --public --push
```

Read the flags, because this is the most useful command in this whole phase:

- `--source=.` use the repo already in this folder rather than making an empty one
- `--public` anyone can see it
- `--push` upload the commits immediately

Open it:

```bash
gh repo view --web
```

Your three commits are on the internet, with your name on them.

## Step 7: understand what just got wired up

```bash
git remote -v
```

`origin` is a nickname for a URL. It is not special, it is just the conventional
name for "the copy of this project that I consider the main one". A repo can have
several remotes with any names you like, which is exactly what Phase 2 uses.

Make one more change, commit it, and push:

```bash
git add .
git commit -m "One more edit"
git push
```

It just works, with no arguments, because `--push` set up the tracking relationship
between your local `main` and `origin/main`.

---

## You should now be able to answer

1. What is actually inside `.git`, and what happens if you delete it?
2. What is the difference between `git add` and `git commit`?
3. Why does `git push` need no arguments after the first time?
4. Where does your history live if GitHub goes down tomorrow?

That last one has a nicer answer than people expect. Every clone is a full copy of
the entire history. A project with forty contributors has forty complete backups
that nobody had to plan for. That is what "distributed" in "distributed version
control" means.

---

**Next:** [Phase 2](../phase-2/), where you contribute to a repo you do not own.
