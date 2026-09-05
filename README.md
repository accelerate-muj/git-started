# git started

Accelerate's third workshop. You walk in having never made a commit. You walk out
having forked a repository, opened a pull request, hit a merge conflict on purpose,
and resolved it.

Everything here uses a single Shakespeare sonnet as the raw material, so the only
new thing in front of you at any moment is the git.

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
| **1** | [git, and only git](phase-1/) | A real history in a folder on your own laptop | git works alone, offline, before GitHub is involved at all |
| **2** | [Publish, then contribute](phase-2/) | Your own repo on GitHub, then a poem file merged into *this* one | Publishing something you own, then getting a change into something you do not |
| **3** | [Teams and conflicts](https://accelerate-muj.github.io/git-started/#phase3) | A shared repo where your edits collide | What happens when two people change the same line, and how you fix it |

Phase 1 never touches the network. Phase 2 is where GitHub arrives, and it ends on a
merge conflict we cause on purpose and deliberately do not resolve.

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
The git is. In Phase 1 you edit it offline, and in Phase 2 you write your own version
of it and get that version merged into this repository.

The numbered copy lives in [`phase-2/sonnet-18.md`](phase-2/sonnet-18.md).

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

If you are teaching rather than attending, each phase README carries its own running
order, the questions to ask the room, and per subphase timings.

Phase 3 has no README of its own. It lives entirely in
[the handbook](https://accelerate-muj.github.io/git-started/#phase3), conflict
mechanism included, along with why it fires reliably. [CONTRIBUTING.md](CONTRIBUTING.md)
has the rule that keeps thirty simultaneous pull requests from colliding.

See [`handbook/`](handbook/) for the thirteen-phase PDF handbook.

Licensed MIT. Fork it, run it at your own club, change whatever you like.
