# Phase 3: teams, and things going wrong

**Roughly 50 minutes.** Form a team of any size, pick a leader, and all work on one
repository at the same time. You will hit merge conflicts. That is the exercise, not
an accident.

---

## Why we are engineering a disaster

In Phase 2 the filename rule meant nobody could collide. Real projects do not have
that luxury. Two people edit the same file, sometimes the same line, and git has to
be told what to do about it.

Almost everyone's first conflict happens under pressure, on real work, alone, at
night. It goes badly and they conclude git is hostile. Doing it here instead, on a
poem, with a room full of people hitting the same wall at the same second, turns it
into what it actually is: a routine, five command chore.

---

## Step 1: form teams

Any size. Three to five works best. Pick one **leader**, who owns the repository
and merges the pull requests. Everyone else contributes.

The leader is not the best programmer in the group. The leader is doing an
administrative job, and it is worth understanding because it is what maintainers of
every open source project do all day.

## Step 2: leader creates the repo

Only the leader runs this:

```bash
gh repo create <team-name> --template accelerate-muj/git-started-team --public --clone
```

A **template repository** is not a fork. It gives you the files with a completely
fresh history, one commit, no connection back to the original. That is what you want
when you are starting a project from a skeleton rather than contributing to one.

## Step 3: leader adds everyone

For each teammate:

```bash
gh api -X PUT repos/<leader-username>/<team-name>/collaborators/<teammate-username> -f permission=push
```

**This is the step that eats time, so start it early.** Each teammate gets an
invitation they must accept before they can push. It arrives by email and appears at
[github.com/notifications](https://github.com/notifications). Until they accept,
their push will be rejected with a confusing permission error.

Teammates, accept from the terminal:

```bash
gh api user/repository_invitations
```

```bash
gh api -X PATCH user/repository_invitations/<invitation-id>
```

## Step 4: everyone clones

```bash
git clone https://github.com/<leader-username>/<team-name>.git
```

Note what is different from Phase 2. There is no fork and no `upstream`. You have
push access to `origin` directly, because you are on the inside of this project.
This is how a team of colleagues works, as opposed to how a stranger contributes.

## Step 5: everyone branches and edits the same thing

```bash
git switch -c line/<your-username>
```

Open `team-sonnet.md`. Do two things:

1. **Rewrite your assigned line** of the sonnet. The leader assigns line numbers,
   or just call them out around the table.
2. **Add your name to the Credits block at the bottom.**

Everybody adds their name in the same place, directly under the comment. That
second instruction is what guarantees the conflict.

Commit and push:

```bash
git add team-sonnet.md
```

```bash
git commit -m "Rewrite line 7, add my name to credits"
```

```bash
git push -u origin line/<your-username>
```

```bash
gh pr create --fill
```

## Step 6: the leader merges the first one

```bash
gh pr list
```

```bash
gh pr merge <number> --squash --delete-branch
```

That one goes in cleanly. Everything is fine. It will not be fine for anyone else.

## Step 7: everybody else is now broken

Try to merge the second PR and GitHub refuses: **this branch has conflicts that must
be resolved.**

Nothing has gone wrong. Your branch was built on a version of `main` that no longer
exists. Someone else's name is now sitting on the line where you put yours, and git
will not guess which one of you should win.

Fix it on your own machine:

```bash
git fetch origin
```

```bash
git rebase origin/main
```

Git stops and tells you `team-sonnet.md` has a conflict.

## Step 8: read the markers

Open the file. You will see this:

```
## Credits
<<<<<<< HEAD
- @first-person-who-merged
=======
- @you
>>>>>>> Rewrite line 7, add my name to credits
```

Read it as three parts:

- Between `<<<<<<<` and `=======` is **what is already on main**.
- Between `=======` and `>>>>>>>` is **what you are trying to add**.
- The markers themselves are just text that git inserted. They are not magic and
  nothing is watching them.

**Here is the part people get wrong.** A conflict feels like a question of who wins.
Almost always the correct answer is *both*. You want both names in the credits.
Delete the three marker lines and keep both entries:

```
## Credits
- @first-person-who-merged
- @you
```

Save it.

## Step 9: finish the rebase

```bash
git add team-sonnet.md
```

```bash
git rebase --continue
```

`git add` is how you tell git a conflict is resolved. There is no separate
"resolve" command, which surprises people. Staging the file *is* the resolution.

Then push. Your branch history was rewritten by the rebase, so an ordinary push is
rejected:

```bash
git push --force-with-lease
```

**Use `--force-with-lease`, not `--force`.** They look interchangeable and they are
not. Plain `--force` overwrites the remote branch no matter what is on it, so if a
teammate pushed to your branch while you were resolving, you have just silently
destroyed their commit. `--force-with-lease` checks that the remote is still where
you last saw it and refuses if somebody else has touched it. It is the difference
between overwriting your own work and overwriting someone else's.

## Step 10: repeat, and watch it get worse

Every teammate does steps 7 to 9. The third person conflicts with two names, the
fourth with three. By the fifth the file has the whole team in it.

When you are done:

```bash
git switch main
```

```bash
git pull
```

```bash
git log --oneline --graph --all
```

---

## If you have time: rebase versus merge

You used `git rebase origin/main`. The alternative:

```bash
git merge origin/main
```

Both end with your work combined with everyone else's. They differ in what the
history looks like afterwards.

**Merge** keeps your branch exactly as it happened and adds a commit joining the two
lines together. Honest, and the graph gets tangled with many contributors.

**Rebase** lifts your commits off and replays them on top of the new `main`, as if
you had started from it. The history reads as one clean line. The commits are new
objects with new hashes, which is exactly why the push needed forcing.

The rule most teams settle on: **rebase your own unmerged branch, merge shared
branches.** Rewriting history nobody else has is free. Rewriting history other
people have already pulled causes the kind of afternoon nobody enjoys. There is a
lot more on this in Rabbit Holes.

---

## Leader's job, which is the real lesson

Reviewing:

```bash
gh pr diff <number>
```

```bash
gh pr checkout <number>
```

```bash
gh pr review <number> --approve
```

```bash
gh pr review <number> --request-changes --body "Line 7 does not scan, try again"
```

Notice what you keep doing to your teammates. Every time you merge, everyone else's
branch goes stale and somebody has to redo work. Merge order is a decision with
consequences for other people, and that is the entire job. Maintainers of large
projects think about this constantly.

Try turning on branch protection and watch what changes:

```bash
gh api -X PUT repos/<leader>/<team-name>/branches/main/protection -F required_pull_request_reviews[required_approving_review_count]=1 -F enforce_admins=false -F restrictions=null -F required_status_checks=null
```

Now nobody can push straight to `main`, including the leader.

---

## You should now be able to answer

1. What do `<<<<<<<`, `=======` and `>>>>>>>` separate?
2. Which command marks a conflict resolved?
3. Why did your push get rejected after a rebase?
4. What does `--force-with-lease` check that `--force` does not?
5. Your teammate merged first and your branch is stale. Merge or rebase?

---

**Next:** [Rabbit Holes](../handbook/), which starts at Phase 4 and does not stop
for a while.
