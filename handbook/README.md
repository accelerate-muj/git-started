# Rabbit Holes

The handbook. It picks up where the workshop stops, at **Phase 4**, and keeps going
until it runs out of git.

Thirteen phases, about 120 pages, one PDF each so they can be handed out separately
or read in order. Every phase ends with questions you should be able to answer, and
each one points at the next.

---

## Contents

| | Phase | About |
|---|---|---|
| **4** | [Undo](pdf/phase-04-undo.pdf) | Every way to take something back. `restore`, the three modes of `reset`, `revert`, `reflog`, `stash`, and the two commands that genuinely destroy work. |
| **5** | [Rewriting history](pdf/phase-05-rewriting.pdf) | Interactive rebase, squashing, splitting a commit in half, `cherry-pick`, the autosquash workflow, and removing a file from every commit that ever held it. |
| **6** | [Forensics](pdf/phase-06-forensics.pdf) | Reading history instead of writing it. Log filtering, the pickaxe, `blame` without the noise, and `bisect run` finding a broken commit while you make tea. |
| **7** | [Merging deeply](pdf/phase-07-merging.pdf) | Fast-forward versus three-way, merge strategies, `-s ours` versus `-X ours`, better conflict markers, and `rerere`. |
| **8** | [Remotes and big repos](pdf/phase-08-remotes.pdf) | Refspecs read aloud, tracking branches, worktrees, shallow and partial clones, sparse checkout, submodules, LFS. |
| **9** | [Plumbing](pdf/phase-09-plumbing.pdf) | What is actually inside `.git`. The four object types, why a commit is not a diff, why a branch is 41 bytes, and building a commit by hand. |
| **10** | [Trust](pdf/phase-10-trust.pdf) | Anyone can commit as you. SSH and GPG signing, what Verified really proves, annotated tags, releases, and the day someone commits a password. |
| **11** | [Configuration and automation](pdf/phase-11-config.pdf) | Config levels, aliases worth having, `.gitignore` versus `.gitattributes`, and hooks that stop a bad commit existing. |
| **12** | [GitHub as a platform](pdf/phase-12-github.pdf) | Everything that is not git. Issues, templates, projects, pages, gists, and a search syntax worth learning properly. |
| **13** | [The gh CLI in full](pdf/phase-13-gh.pdf) | The whole command surface, `gh api` for everything without a command, aliases, extensions, and `gh` inside Actions. |
| **14** | [Actions and CI/CD](pdf/phase-14-actions.pdf) | Workflow anatomy, matrix builds, caching, environments, and the two triggers that can hand your repository to a stranger. |
| **15** | [Being a maintainer](pdf/phase-15-maintainer.pdf) | The longest one, and the least about commands. Licensing, branch protection, reviewing well, triage, saying no, security reports, burnout, succession. |
| **16** | [Scale and origins](pdf/phase-16-scale.pdf) | Where git came from in ten days of 2005, why that explains the strange parts, the email workflow, and making a huge repository fast. |

---

## Reading order

In order, if you have time. Phases build on each other and later ones refer back.

If you are picking:

- **Frightened of git?** Phase 4, then stop. It is the one that matters.
- **Your history is a mess before a review?** Phase 5.
- **Something broke and nobody knows when?** Phase 6.
- **Just inherited a repo?** Phase 15, then 10.
- **Want the moment it all clicks?** Phase 9.

---

## Building it yourself

```bash
cd handbook && python build.py
```

Needs a TeX distribution with `xelatex`: MiKTeX on Windows, TeX Live on Linux,
MacTeX on macOS. The first build is slow because packages download on demand.

```bash
python build.py 9 15
```

Builds only those phases.

```bash
python build.py --clean
```

Removes the `.aux`, `.log` and `.toc` files LaTeX leaves behind.

If `xelatex` is not on your PATH:

```bash
XELATEX="C:/Apps/MikTex/miktex/bin/x64/xelatex" python build.py
```

Source is in [`src/`](src/), one `.tex` per phase plus `rabbithole.sty`, which holds
the shared design: palette, fonts, code listing style, and the callout boxes.

---

## Contributing

Corrections are the most valuable thing this can receive. A command that does not
work on your OS, a flag that changed, an explanation that is subtly wrong. See
[CONTRIBUTING.md](../CONTRIBUTING.md).

Do not commit built PDFs from a feature branch. They are rebuilt when a phase is
finalised, and a PDF in a diff is noise nobody can review.
