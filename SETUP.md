# Setup

Ten minutes, done before the session. If you hit trouble, bring the error message
to the workshop rather than skipping ahead.

---

## 1. Install git

**Windows**: download from [git-scm.com](https://git-scm.com/download/win). Accept
the defaults, with one exception: when it asks about a default editor, pick one you
can actually exit. Vim has ended more workshops than any other single cause.

**macOS**: `brew install git`, or just run `git --version` and let the system offer
to install the command line tools.

**Linux**: `sudo apt install git` or your distribution's equivalent.

Verify:

```bash
git --version
```

## 2. Install the GitHub CLI

**Windows**: `winget install --id GitHub.cli`

**macOS**: `brew install gh`

**Linux**: follow [the instructions here](https://github.com/cli/cli/blob/trunk/docs/install_linux.md).

Verify:

```bash
gh --version
```

## 3. Tell git who you are

Every commit is stamped with a name and an email. Git will refuse to commit until
you have set them.

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

Use the email attached to your GitHub account, otherwise your commits will not be
linked to your profile and your contribution graph will stay empty. If you would
rather not publish your real address, GitHub gives you a `noreply` one under
Settings then Emails, and it works fine here.

## 4. Set your default branch name

```bash
git config --global init.defaultBranch main
```

Git's built in default is still `master` on older versions. GitHub uses `main`.
Setting this now avoids a mismatch in Phase 1 that is annoying to untangle later.

## 5. Log in to GitHub from the terminal

```bash
gh auth login
```

Answer: **GitHub.com**, then **HTTPS**, then **yes** to authenticate git with your
GitHub credentials, then **login with a web browser**. Copy the one time code,
press enter, paste it in the browser.

That last "authenticate git with your GitHub credentials" step is the one people
skip. It is what stops `git push` from asking for a password every single time.

Verify:

```bash
gh auth status
```

---

## Everything at once

```bash
git --version && gh --version && gh auth status && git config --get user.name
```

If all four answer, you are set.

---

## Known snags

**`gh: command not found` right after installing.** Your terminal cached the old
PATH. Close it and open a new one.

**Git asks for a username and password on push, and your password is rejected.**
GitHub removed password authentication for git in 2021. Run `gh auth login` again
and say yes to the git credentials question.

**Corporate or campus wifi blocks the browser login.** Run `gh auth login` and
choose "paste an authentication token" instead, then create a token at
github.com/settings/tokens with the `repo` and `read:org` scopes.

**You are on a shared or lab machine.** Use `git config --local` instead of
`--global` inside each repo, so you do not leave your identity behind for the next
person, and run `gh auth logout` before you leave.
