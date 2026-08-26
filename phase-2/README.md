# Phase 2: fork, branch, pull request

**Roughly 40 minutes.** You will add a file to *this* repository, which you do not
have permission to write to, by forking it and opening a pull request.

Nobody in this phase will hit a merge conflict. That is deliberate, and Phase 3
will fix it.

---

## Step 0: try it the obvious way first

You have your own repo from Phase 1. Now you want to contribute to somebody
*else's*. The obvious plan is: download it, edit it, upload it. Try that:

```bash
git clone https://github.com/accelerate-muj/git-started.git
cd git-started
echo "test" >> README.md
git commit -am "Try to edit"
git push origin main
```

```
Permission denied
```

You downloaded the repo onto your laptop fine. You just have no upload access. You
got read, not write. So your changes exist on your laptop and nowhere else — and if
they are not on GitHub, there is nothing to open a pull request *about*.

This is not an obstacle to work around, it is how essentially every open source
project on earth stays sane: strangers cannot write to the project directly, but
anyone can propose a change.

**Before the next step, delete this clone or `cd` out of it.** Otherwise you will
end up with two `git-started` folders and spend ten minutes typing into the wrong
one.

## The fix, in one sentence

Make your own copy on GitHub, one you *can* write to. Push there. Then ask us to
pull your work into ours.

Think of Google Docs. Somebody shares a document and you cannot edit it. What do
you do? **File → Make a Copy.** Now there is a copy in your Drive and you can do
whatever you like to it.

On GitHub, that Make a Copy button is called **Fork**. The mechanism has three
parts:

1. **Fork.** Your own server side copy of the whole repo, which you fully control.
2. **Branch.** A named line of work inside that copy.
3. **Pull request.** A request that we pull your branch into our repo, plus a place
   to discuss it before anyone does.

## Step 1: fork and clone in one command

You can press Fork in the browser, or do both jobs with one command:

```bash
gh repo fork accelerate-muj/git-started --clone
cd git-started
```

That single command makes your copy on GitHub *and* downloads it to your laptop.
GitHub does not duplicate the whole thing on disk — it stores only the differences,
and it records a relationship between the original and your copy. That relationship
is what makes the pull request possible later.

## Step 2: two copies, two names

You now have two copies: yours, which you can push to, and ours, which you want to
contribute to. Typing a full URL every time would be miserable.

So git lets you save a long URL under a short name — the same way your phone has
`Mom` saved against `+91-98765...`. In git's vocabulary that saved name is a
**remote**.

Forking set up two of them for you. Check:

```bash
git remote -v
```

- **`origin`** points at *your* fork. You can push here.
- **`upstream`** points at *our* repo. You cannot push here, but you can fetch from it.

`origin` must show **your** username. If it says `accelerate-muj`, you cloned ours
instead of forking, and everything after this will fail confusingly. Fix it now.

Remote names are per folder, not global — every repo has its own `.git/config`, so
every folder gets its own `origin` and they never collide.

If `upstream` is missing, which happens occasionally, add it yourself:

```bash
git remote add upstream https://github.com/accelerate-muj/git-started.git
```

That pair of names is a near universal convention. When you read a project's
contributing guide and it says "sync with upstream", this is what it means.

## Step 3: catch up, then branch

Our repo may have moved since you made your copy. Catch up first:

```bash
git fetch upstream
git merge upstream/main
```

If nothing changed it says **"Already up to date"**, which is a fine answer.

`fetch` downloads and changes none of your files. `merge` is the half that touches
them. Most people meet these two welded together as `git pull` and never find out
they are separable.

Now branch. Editing `main` directly is risky — if it goes wrong, your `main` is the
thing that is wrong. A branch is a safety net: if it goes badly you delete the
branch and `main` was never touched.

```bash
git checkout -b add-<your-github-username>
```

Check you are actually on it:

```bash
git branch
```

The `*` sits next to your branch.

> **Modern alternative:** `git switch -c add-<your-github-username>`.
> `git checkout` is the old command and it does several unrelated jobs, which is
> exactly why it confused people for a decade. `git switch` only switches branches.
> You will read `checkout` in every Stack Overflow answer you ever open, so you need
> to recognise it. `switch` is the one to type.

## Step 4: write your file, and sign it

Create exactly one file, named after your GitHub username:

```bash
echo "Hi, I'm <your-name>. I'm learning Git at this workshop!" > phase-2/poems/<your-github-username>.md
```

Then open that file, write your version of Sonnet 18 in it, and put this line at
the end:

```
Written by <your-name>
```

Some versions that have worked well:

- Sonnet 18 rewritten in modern English
- Sonnet 18 rewritten in Hindi, or Hinglish, or your first language
- Sonnet 18 as a group chat
- A parody with the same rhyme scheme
- A straight annotation explaining what each line means

There is a worked example in [`poems/`](poems/) if you want to see the shape of one.

**Everything you touch goes in that one file.** Your username is unique on GitHub,
so no two people can create the same file, so nobody's change can overlap with
anybody else's. Thirty pull requests will merge in a row without a single collision.
Sign your own file, not `poem/sonnet-18.md` — editing a file everybody shares is
Phase 3's job, and doing it here just invents Phase 3 forty minutes early.

## Step 5: look at what you changed

```bash
git status
git diff
```

`git status` calls your file **untracked**. And `git diff` shows you *nothing* —
which surprises almost everybody.

That is correct behaviour. `git diff` only looks at files git is already tracking,
and your file is brand new. Git has not been introduced to it yet.

Stage it, then look again:

```bash
git add .
git diff --staged
```

Now the whole file appears with a `+` in front of every line, including
`+ Written by <your-name>`. **The `+` means addition.** If you had deleted
something you would see a `-`.

`git add .` needs the space. `git add.` is not a command and fails.

## Step 6: commit and push to your fork

```bash
git commit -m "Add <your-name>'s take on Sonnet 18"
```

Check it landed:

```bash
git log --oneline -1
```

Your commit is on top.

Now, where does that commit get uploaded? Not our repo — no permission. Your copy.
That is `origin`. First time, with `-u`:

```bash
git push -u origin add-<your-github-username>
```

**What `-u` does:** it creates a tracked link between your local branch and the
remote one. After that git knows which remote branch you mean, so from then on bare
`git push` and `git pull` work with no arguments. In Phase 1, `gh repo create
--push` did this for you invisibly. This is the first time you have done it by hand.

## Step 7: why you could not skip straight to the pull request

Worth asking before you run the next command: why push first? Why not just open the
PR?

Because **a pull request is not an upload command. It is a comparison** — between
two branches that are both already on GitHub. If your work only exists on your
laptop, there is nothing on GitHub to compare against, and GitHub will tell you
there is nothing to compare.

**The order is fixed: commit → push → pull request.**

## Step 8: open the pull request

The base command is:

```bash
gh pr create
```

Everything else is answering questions GitHub still has.

**Where does this PR go?** You worked on your copy, but the PR has to land on ours.
Because `upstream` is configured, `gh` works this out on its own — it can see you
are contributing from a fork and aims at the original. You do not have to say
anything. If `gh` ever gets confused and picks the wrong repo, force it with
`--repo accelerate-muj/git-started`.

**Which branch into which branch?** Source is your current branch, which `gh`
detects. Destination defaults to `main`, which is what you want here. Neither needs
specifying.

**What is the title?** That is the line that shows up in the PR list, so keep it
short and clear. Write it with `--title`, and give it a description with `--body`,
which is what people see when they open the PR.

The other flags, for when you are doing this on real work:

| Flag | When you want it |
|---|---|
| `--fill` | Auto-fill title and body from your last commit message |
| `--draft` | Work is unfinished and you want early feedback. Cannot merge until you click "Ready for review" |
| `--reviewer <username>` | Request a review from a specific person |
| `--assignee <username>` | Put the PR in somebody's name |
| `--label documentation` | Tag it |
| `--web` | Skip the terminal and fill GitHub's PR form in a browser |
| `--repo <owner>/<repo>` | Force the destination when `gh` guesses wrong |

So the smallest command that works today is:

```bash
gh pr create --title "Add <your-name>" --body "Added my poem file and signed it."
```

Or, the lazy and perfectly effective version:

```bash
gh pr create --fill
```

Check it exists:

```bash
gh pr list
gh pr status
gh pr view --web
```

A bot will comment within a minute confirming your file is named correctly. It does
not block anything, it just means whoever is merging can move fast.

## Step 9: watch it merge

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
3. Why did `git diff` show nothing until you ran `git add`?
4. Why can you not open a pull request before pushing?
5. Your fork is thirty commits behind. What command fixes that?
6. Is a pull request a git feature or a GitHub feature?

That last one catches people. Pull requests are **not** part of git. Git has no
idea what a PR is. It is a GitHub product built on top of git branches, which is
exactly why you need `gh` and not `git` to make one.

---

## Running this phase

**For whoever is presenting.** Everything above is the participant path. This part
is the delivery: the order to reveal it in, the questions to ask out loud, and the
lines that make it land. Told out loud it runs the full 40 minutes including hands
on time.

The Hinglish below is how it is actually said in the room. Do not put it on a slide
— the moment it is on screen they read ahead and the pauses stop working.

### The shape of it

**Let them hit the wall first, then hand them the tool.** Every step above is an
answer to a question they have just felt. Introduce nothing before the problem it
solves.

### Beat by beat

**Step 0, the wall.** Let them actually run the failing push. The temptation is to
warn them first and save two minutes. Do not — `Permission denied` is the only thing
that makes fork feel like a solution rather than a ritual.

> Aapne repo apne laptop pe download toh kar liya, but upload access nahi hai. Aapne
> sirf read kiya, write permission nahi hai. Toh aapke changes sirf aapke laptop pe
> hain, GitHub pe nahi. Aur GitHub pe nahi hoga toh PR bhi nahi hoga.

**Ask the room:** so where is your work right now? Wait for somebody to say "on my
laptop". That is the whole problem stated in four words.

Then make them delete the clone before Step 1. Otherwise they end up with two
`git-started` folders and spend ten minutes typing into the wrong one. This is the
single biggest time sink in the phase.

**Step 1, Make a Copy.** The analogy is what makes it land:

> Google Docs ki tarah socho. Kisi ne document banaya hai, aapko edit nahi karne
> denge. Toh aap kya karte ho? File → Make a Copy. Ab aapke Drive mein ek copy aa
> gayi, aap usme kuch bhi kar sakte ho. GitHub pe yeh "Make a Copy" ka button hai.

> Yeh ek hi command GitHub pe aapki copy banata hai aur laptop pe download bhi kar
> deta hai. Copy banate waqt GitHub sirf differences copy karta hai, saara data nahi
> — aur original repo aur aapki copy ke beech ek relationship establish karta hai.

Say that last sentence slowly. A fork is not a duplicate sitting on a disk
somewhere, and it is not disconnected from us. It is a copy that remembers where it
came from, which is exactly what makes the pull request possible later.

**Step 2, remotes.** The phone contact analogy does the work:

> Har baar poora URL type karna mushkil hai. Isliye Git ek system deta hai — aap ek
> lambi URL ko ek chhote naam se save kar sakte ho, jaise phone mein "Mom" save
> karte ho +91-98765... ke liye. Is saved naam ko Git ki bhasha mein "remote" kehte
> hain.

> Yeh naam per-folder hota hai, global nahi — har folder ka apna `.git/config` hai,
> toh har folder ka `origin` alag hota hai, collision nahi hota.

**This is the beat people quietly miss.** If somebody's `origin` says
`accelerate-muj`, they cloned ours instead of forking, and every command after this
fails in a confusing way. Catch it here, not at the push.

**Step 3, fetch and branch.** Worth naming the split out loud: `fetch` downloads and
changes nothing, `merge` is the part that touches your files. Most people meet these
two welded together as `git pull` and never learn they are separable.

> Directly `main` pe edit karna risky hai — agar kuch galat ho gaya toh main kharab
> ho jayega. Branch ek safety net hai. Agar kuch galat hua, branch delete karo, main
> safe rahega.

Show `git checkout -b` and `git switch -c` both. They will read `checkout` in every
Stack Overflow answer they ever open, so they need to recognise it; `switch` is what
they should type.

**Step 4, the file.** The filename rule is not bureaucracy, so give it its reason:

> GitHub pe aapka username unique hai, toh koi do log same file nahi bana sakte.
> Matlab kisi ka change kisi se takrayega nahi. Tees pull requests, ek ke baad ek,
> bina kisi conflict ke merge ho jayenge.

If somebody signs `poem/sonnet-18.md` instead of their own file, they have just
invented Phase 3 forty minutes early. Send them back.

**Step 5, the empty diff.** Let it land as a surprise before you explain it:

> `git diff` sirf un files ko dekhta hai jinhe Git already track kar raha hai. Aapki
> file bilkul nayi hai — Git ne use abhi tak dekha hi nahi. Isliye diff khaali hai.

Then `git add .` and `git diff --staged`, and point at the `+`. Every added line
carries one; a deletion would carry `-`.

**Step 6, `-u`.** Callback to Phase 1 — `gh repo create --push` did this same thing
for them invisibly. This is the first time they do it by hand.

> `-u` tracked link banata hai between local branch aur remote branch. Uske baad Git
> jaanta hai ki jab aap `git push` ya `git pull` chalaoge, toh yeh remote branch hai
> jisse baat karni hai.

**Step 7, ask it before you answer it.** Somebody always wonders why they cannot go
straight to the pull request.

> PR ek upload command nahi hai. PR ek comparison hai — do branches jo GitHub pe
> already hain unke beech. Agar code sirf laptop pe hai, GitHub pe nahi, toh compare
> kya karega? Kuch nahi milega. Order fixed hai: commit → upload → PR.

**Step 8, build the command, do not hand it over.** Start from bare `gh pr create`
and ask what GitHub still needs to know. Where does it go? Which branch into which
branch? What is the title? Each flag is an answer to one of those questions, and
because `upstream` is set, most of them answer themselves.

> Agar aapne `upstream` configure kiya hai, toh `gh` itna smart hai ki automatically
> samajh jaata hai — "haan, yeh banda fork se contribute kar raha hai, PR original
> repo pe bhejna hai." Kuch specify karne ki zaroorat nahi.

Then merge them live, on the projector, one at a time. Watching their own name
appear in a repository that is not theirs is the moment the phase pays off, and it
only works if they can see it happen.

### The three lines that carry it

1. "GitHub pe yeh Make a Copy ka button hai."
2. "PR ek upload command nahi hai. PR ek comparison hai."
3. "Order fixed hai: commit → upload → PR."

### Where it maps

| The beat | What it answers |
|---|---|
| `Permission denied` at Step 0 | Why forks exist at all |
| The phone contact analogy | Why `origin` and `upstream` are words and not URLs |
| The branch as safety net | Sets up Phase 3, where the safety net is what gets tested |
| "PR is a comparison" | The "There isn't anything to compare" error, when it arrives |
| One file per username | Why Phase 3 conflicts at all, by removing exactly this rule |

### Where the 40 minutes actually go

The commands take ten. The rest goes on people who cloned instead of forked (Step 2
catches them), people in the wrong folder (Step 0's housekeeping note), and waiting
for thirty pull requests to appear. Start Step 8's flag discussion while the slow
half are still pushing.

**When somebody asks whether a pull request is a git thing** — no, and say it
plainly. Git has no idea what a PR is. It is a GitHub product built on top of git
branches, which is exactly why this phase needs `gh` and not `git` to make one.

---

**Next:** [Phase 3](../phase-3/), where we remove the safety net.
