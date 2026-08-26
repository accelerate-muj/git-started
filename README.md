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
| **3** | [Teams and conflicts](https://accelerate-muj.github.io/git-started/#phase3) | A shared repo where your edits collide | What happens when two people change the same line, and how you fix it |

Phase 2 has no conflicts by design. Phase 3 is nothing but conflicts by design.
That contrast is the whole point of splitting them.

---

## The poem

Every phase uses this same text. Copy it straight from here.

```
Shall I compare thee to a summer's day?
Thou art more lovely and more temperate:
Rough winds do shake the darling buds of May,
And summer's lease hath all too short a date;
Sometime too hot the eye of heaven shines,
And often is his gold complexion dimm'd;
And every fair from fair sometime declines,
By chance or nature's changing course untrimm'd;
But thy eternal summer shall not fade,
Nor lose possession of that fair thou ow'st;
Nor shall death brag thou wander'st in his shade,
When in eternal lines to time thou grow'st:
   So long as men can breathe or eyes can see,
   So long lives this, and this gives life to thee.
```

Sonnet 18, William Shakespeare, 1609. Out of copyright, so do what you like to it.

**Why the same poem three times.** It is fourteen lines, everybody half knows the
first one, and reusing it means the poem is never the new thing you are learning.
The git is. In Phase 2 you write your own version of it. In Phase 3 your team
rewrites it together and stands on each other's toes doing it.

The numbered copy lives in [`poem/sonnet-18.md`](poem/sonnet-18.md).

---

## What you actually learn

**git**, the tool on your computer: `init`, `add`, `commit`, `status`, `log`,
`switch`, `checkout`, `branch`, `merge`, `rebase`, `fetch`, `pull`, `push`, `remote`,
`diff`.

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

If you are teaching rather than attending, start with
[`facilitator/`](facilitator/) for the Phase 1 opening and the running order. Phase
2 keeps its delivery notes at the bottom of its own README, under
[Running this phase](phase-2/README.md#running-this-phase).

Phase 3 has no README of its own. It lives entirely in
[the handbook](https://accelerate-muj.github.io/git-started/#phase3), conflict
mechanism included, along with why it fires reliably. [CONTRIBUTING.md](CONTRIBUTING.md)
has the rule that keeps thirty simultaneous pull requests from colliding.

See [`handbook/`](handbook/) for the thirteen-phase PDF handbook.

Licensed MIT. Fork it, run it at your own club, change whatever you like.
