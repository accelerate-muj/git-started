# Phase 1 opening: why any of this exists

**This is presenter material. It is deliberately not in the participant handbook.**

If people can read the reasoning off a page, the session is just you reading aloud
what they already have. They get the commands. You get the story.

Told out loud this runs about 6 to 8 minutes. Do not rush the pauses. The whole
thing works because they recognise themselves in it.

---

## Beat 1: the folder everyone already has

> You are writing a poem. You save it as `poems.txt`.
>
> You change a line. You want the old one back, just in case. So you save a copy.
> `poems_v2.txt`. Then `poems_final.txt`. Then `poems_final_ACTUAL.txt`.

**Ask the room:** who has a folder that looks like this right now? Wait for the
hands. Most of them will go up. That recognition is what the rest of it is built
on, so actually wait.

---

## Beat 2: writing diffs by hand

> You save `Diff_file_0_file_1.txt`. You feel proud of yourself for a second.
>
> Now do it again for file_1 and file_2. And again for file_0 and file_2, just in
> case you need to compare those too.
>
> Three files. Three diffs. And you have barely started the poem.
>
> Now imagine this is not a poem. Imagine it is twenty files, for a real project,
> and every single one needs its own diff, against every other version of itself,
> forever.

> **You are not writing poems any more. You are writing paperwork about poems.**

---

## Beat 3: the changelog

> Okay, new idea. Forget the separate diff files. Just keep one file,
> `changelog.txt`, and every time you save, add a line about what you did.
>
> ```
> Fixed the roses line.
> Added a new stanza.
> Changed the ending, felt too sad.
> ```
>
> One file. One place to check. Feels almost responsible.

**Pause here.** Let them think it is solved. Then:

> Read that second line again. *"Fixed the roses line."*
>
> Fixed it how? What did it say before you fixed it? You do not know. You did not
> write it down. You wrote that you changed something, not what it used to be.
>
> And be honest. The day you were tired, or in a hurry, or just forgot? You did
> not update the changelog that day either. You know you did not.

> **It is not a record. It is a note you are hoping you can trust later.**

That line lands best if you slow down on it.

---

## Beat 4: the friend

> Your friend actually likes your poem. They want to add a line.
>
> You send them `poems.txt`. They add something beautiful, save it, and email it
> back as `poems_returned.txt`.
>
> Except, while you were waiting for them to reply, you kept writing too. You
> added your own line. You have your version. They have theirs.
>
> Both of you did something right. Neither of you did anything wrong.

> **So which file is the poem now?**

**Ask it as a real question.** Let the silence sit. Somebody will say "merge them".
That is your cue.

---

## Beat 5: merging by hand

> Fine. Open both files side by side. Read every single line of both. Find what is
> different. Carefully copy the good parts into a new file.
>
> Call it, of course, `poems_merged_v2_final.txt`.
>
> You did it. It is late, your eyes hurt from comparing two identical-looking
> paragraphs for the fifteenth time, but you did it.

---

## Beat 6: the truth

> You will miss a line eventually. Not because you are careless, but because
> comparing two versions of anything by eye, line by line, for long enough, is
> exactly the kind of task humans are bad at and do not notice they are bad at.
>
> Your friend's favourite line, the one they were proudest of, quietly does not
> make it into the merged file. Nobody meant for that to happen. It just did.
>
> And now think about doing this every time either of you saves. Now think about
> doing it with three friends. Five.

---

## Beat 7: the close

> Look back at everything you just tried. Naming files "final". Numbering them.
> Writing diffs by hand. Keeping a changelog. Comparing two files line by line at
> midnight.
>
> Every single one of them needed you, a tired, distracted, forgetful human, to do
> the right thing, perfectly, every single time, forever.

> **One tired night. One missed line. One overwritten file. That is all it takes
> to lose hours of work you cannot get back.**

Then the turn:

> What if you did not have to remember any of this?
>
> What if something kept every version, automatically, the moment you saved, with
> no renaming required?
>
> What if it could tell you exactly what changed, down to the line, without you
> writing a single diff by hand?
>
> What if two people could edit the same file, at the same time, and it figured
> out how to combine both of your work, without either of you losing a line?

> **Sit with that question for a second before you answer it.**

Then: *"Open your terminal."*

---

## Notes for whoever is presenting

**Do not put this on a slide.** It is spoken material. The moment it is on screen
they read ahead and the pauses stop working.

**The three lines that carry it**, if you only remember three:

1. "You are not writing poems any more. You are writing paperwork about poems."
2. "It is not a record. It is a note you are hoping you can trust later."
3. "So which file is the poem now?"

**Where it maps later in the day.** Worth calling back to, because it makes the
commands feel like answers rather than trivia:

| The story beat | What answers it |
|---|---|
| Renaming files `_final` | `git commit`, in Phase 1 |
| Writing diffs by hand | `git diff` and `git log`, in Phase 1 |
| The changelog you forgot to update | The commit message, written at the moment you change something |
| "Which file is the poem now?" | The merge conflict in Phase 3 |
| Missing your friend's favourite line | Conflict markers showing you both versions, so nothing is lost silently |

When somebody hits their first conflict in Phase 3 and looks panicked, this is the
callback: *"remember the poem? This is git refusing to quietly lose your friend's
line. It is asking you instead."*

---

Participant handbook: <https://accelerate-muj.github.io/git-started/>
