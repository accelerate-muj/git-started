# <team name>

A team repository for Phase 3 of Accelerate's **git started** workshop.

Everyone here has push access, so there are no forks and no `upstream`. This is what
working with colleagues looks like, rather than contributing to a stranger's project.

## What to do

1. Clone this repo.
2. `git switch -c line/<your-username>`
3. Open `team-sonnet.md`. Rewrite your assigned line, and add your username to the
   **Credits** block at the bottom.
4. Commit, push, and open a pull request.
5. Wait. The first pull request merges cleanly. Yours probably will not.

Step 5 is the point of the exercise. Full instructions and the fix are in
[the Phase 3 handbook](https://accelerate-muj.github.io/git-started/#phase3).

## Leader

You merge the pull requests. Every time you do, everybody else's branch goes stale
and someone has to rebase. Get used to that feeling, it is most of what maintaining
a project is.

```bash
gh pr list
gh pr diff <number>
gh pr merge <number> --squash --delete-branch
```
