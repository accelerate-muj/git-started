# Contributing

Two different situations, two different sets of rules.

---

## During the workshop, Phase 2

**One rule: one file, named after you.**

```
phase-2/poems/<your-github-username>.md
```

Nothing else in the same pull request. Do not edit anyone else's file, the phase
READMEs, `phase-2/sonnet-18.md`, or anything at the root. Your version of the sonnet
and the `Written by <your-name>` line that signs it both go inside that one file.

The rule exists for a mechanical reason. Thirty people are submitting at the same
time, and GitHub usernames are unique, so if everyone only ever touches their own
file then no two pull requests can overlap and every one of them merges cleanly.
Break the rule and you will conflict with somebody, which is a fine thing to
experience but it is Phase 3's job, not Phase 2's. Signing a shared file rather than
your own is the usual way people trip over this.

Work on a branch named after you, not on `main`:

```bash
git checkout -b add-<your-github-username>
```

A bot comments on your pull request telling you whether the filename is right. It
does not block anything. If it complains about the name:

```bash
git mv <wrong-name> phase-2/poems/<your-github-username>.md
```

```bash
git commit -m "Rename to match my username"
```

```bash
git push
```

The pull request updates itself. You do not need to open a new one, and that
surprises almost everybody the first time. A pull request tracks a *branch*, not a
snapshot, so anything you push to that branch appears in the PR automatically.

### Content

Anything you like, as long as it is your own work and it follows the
[Code of Conduct](https://github.com/accelerate-muj/.github/blob/main/CODE_OF_CONDUCT.md).
Translations, parodies, annotations, modern rewrites, and complete reimaginings have
all been good. It does not need to be polished.

---

## After the workshop, or if you are not at it

Normal open source rules. Fork, branch, pull request, describe what you changed and
why.

Things that are genuinely useful:

- **Corrections.** A command that does not work on your OS, a flag that has changed,
  a step that assumes something it should not. These are the most valuable pull
  requests this repo can get, because a wrong instruction wastes thirty people's
  time simultaneously.
- **Platform notes.** Most of this was tested on Windows and Linux. If something
  behaves differently on macOS, say so.
- **Handbook material.** See below.

Things to raise as an issue first, before writing anything:

- Restructuring the phases
- New phases in the handbook
- Anything that changes what happens in the room during a live session

### Handbook contributions

The handbook is LaTeX, in [`docs/src/`](docs/src/). Build it with:

```bash
cd docs && make
```

You need a TeX distribution (TeX Live, MiKTeX, or MacTeX). The first build is slow
because it downloads packages, later ones are quick.

Do not commit the built PDFs from a feature branch. They are rebuilt and committed
when a phase is finalised, and PDFs in a diff are noise nobody can review.

---

## Commit messages

Say what changed, in the imperative, on one line under about seventy characters.

```
Fix gh auth flag in Phase 2 step 6
Add Marathi translation
Explain why force-with-lease is not force
```

Not:

```
update
fixed stuff
asdfgh
```

You will be reading your own history in six months and you will not remember what
`asdfgh` did. This is the cheapest good habit in software and almost nobody forms
it early enough.

---

## Reporting a problem

Open an issue. Include your operating system, the exact command you ran, and the
complete error message, pasted as text rather than a screenshot. Text can be
searched by the next person who hits the same wall.
