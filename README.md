# git started

Accelerate's third workshop. You walk in having never made a commit. You walk out
having forked a repository, opened a pull request, hit a merge conflict on purpose,
and resolved it.

Everything here uses a single Shakespeare sonnet as the raw material, so the only
new thing in front of you at any moment is the git.

---

## Before we start: Chaos Draft

Fifteen minutes before the session proper, everyone writes one story together, one
word each, no turn order. It falls apart quickly, which is the intention. A bot
reads every word before it lands and eats the ones that should not be there, in
English and Hindi, in about eight microseconds.

It runs on one laptop over the room wifi. See [`chaos-draft/`](chaos-draft/).

---

## Before you arrive

Do [SETUP.md](SETUP.md). It takes ten minutes and it is the difference between
starting on time and spending the first half hour watching thirty people install
things. Both `git` and the GitHub CLI (`gh`) need to work in your terminal.

Check yourself:

```bash
git --version && gh --version && gh auth status
```

Three green answers and you are ready.

---

## The three phases

| | Phase | You will build | The idea |
|---|---|---|---|
| **1** | [Your own repo](phase-1/) | A repo on your GitHub profile, made from an empty folder | git works on your machine, alone, before GitHub is involved at all |
| **2** | [Fork and contribute](phase-2/) | A poem file in *this* repo, merged through a pull request | How you contribute to a project you do not own |
| **3** | [Teams and conflicts](phase-3/) | A shared repo where your edits collide | What happens when two people change the same line, and how you fix it |

Phase 2 has no conflicts by design. Phase 3 is nothing but conflicts by design.
That contrast is the whole point of splitting them.

---

## What you actually learn

**git**, the tool on your computer: `init`, `add`, `commit`, `status`, `log`,
`switch`, `branch`, `merge`, `rebase`, `fetch`, `pull`, `push`, `remote`, `diff`.

**gh**, the tool that talks to GitHub: `auth login`, `repo create`, `repo fork`,
`repo sync`, `pr create`, `pr list`, `pr view`, `pr checkout`, `pr merge`, `api`.

Most tutorials teach one and leave you to guess the other. The two do different
jobs. `git` moves commits around. `gh` handles the things that only exist because
GitHub exists: forks, pull requests, reviews, issues. Knowing which tool owns
which job stops most of the confusion before it starts.

[CHEATSHEET.md](CHEATSHEET.md) puts them side by side on one page.

---

## After the workshop

[`handbook/`](handbook/) contains **Rabbit Holes**, a set of PDFs picking up at
Phase 4 and running well past anything covered in the session: rewriting history,
recovering work you thought you destroyed, bisecting to find the commit that broke
the build, running a project as a maintainer, and what a commit actually is
underneath.

You do not need any of it to be useful with git. You need it to stop being afraid
of git.

---

## Running this workshop

If you are teaching rather than attending, see [phase-3/README.md](phase-3/README.md)
for the conflict mechanism and why it fires reliably, and
[CONTRIBUTING.md](CONTRIBUTING.md) for the rule that keeps thirty simultaneous
pull requests from colliding.

See [`handbook/`](handbook/) for the thirteen-phase PDF handbook.

Licensed MIT. Fork it, run it at your own club, change whatever you like.
