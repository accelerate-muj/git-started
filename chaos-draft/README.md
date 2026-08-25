# Chaos Draft

The warm-up activity, run in the fifteen minutes before the git workshop starts.

One page. Everybody types into it at the same time, like a shared document. It
falls apart almost immediately, which is the point.

It runs on one laptop. Everyone joins over wifi or a phone hotspot. Nothing leaves
the network and nobody makes an account.

---

## The activity

1. Start the server and put the QR on the projector.
2. Everyone scans it and types a name.
3. Write. Anywhere on the page, at the same time as everyone else. Whole
   sentences, backspace, go back and change what somebody wrote a minute ago.
4. After ten minutes, read the result out loud.

There is no turn order, no ownership and no plan. Two people will steer the story
in opposite directions in the same paragraph, and that is the entire joke.

A filter removes anything inappropriate before it reaches the page, in English and
Hindi. Participants do not need to think about it. Everyone sees a counter of how
many words were removed, but never which ones.

---

## Running it

```bash
cd chaos-draft
```

```bash
pip install -r requirements.txt
```

```bash
python server.py
```

It prints a QR code in the terminal and two links:

```
  Everyone scans that, or opens:  http://10.44.201.78:8000
  Your host link:                 http://10.44.201.78:8000/?key=XXXXXXXXXXXX
                                  ^ yours only.
```

Show the QR, or the first link. Open the second one yourself.

Needs Python 3.9 or newer.

### Running off a phone hotspot

Usually easier than campus wifi, which often isolates devices from each other so
they cannot see the laptop at all.

1. Turn on the hotspot, connect the laptop to it.
2. Start the server. It picks up the hotspot address by itself.
3. Show the QR. Everyone joins the same hotspot and scans.

If the printed address looks wrong, override it:

```bash
python server.py --ip 192.168.43.1
```

### The host link

The key is generated on first run and saved to `.host-key`, so **your host link is
the same every time**, including after a restart mid-session. It is printed only in
your terminal, and `.host-key` is gitignored so it never reaches the repository.

There is no fixed default, deliberately. This repository is public, so any key
written down here would be a key everyone in the room already has, and the host
controls include wiping the page.

If it leaks:

```bash
python server.py --new-key
```

### What the host gets

| | |
|---|---|
| **Stopped by the filter** | A live list of what the filter removed, and who typed it. Nobody else sees this. |
| **Block a word** | Type a word, press Add. It is removed from the page immediately and blocked for the rest of the session. |
| **Reset** | Clears the page for everyone. |
| **Copy** | The whole page to your clipboard. Also at `/story.txt`. |

---

## How the shared page works

One string on the server, and operational transform to keep everyone agreed on it.
See `ot.py`.

Every edit you make is sent as "at position 12, delete 3 characters, insert this
text", along with the version you last saw. The server adjusts it for anything
that landed in the meantime, applies it, and tells everyone. That adjustment is
the whole of collaborative editing:

> Alice edits at position 10 and Bob at position 3, both against version 7. Bob
> lands first and inserts 5 characters. Alice's edit now has to move to position
> 15 or it lands in the wrong place.

Verified converging: two people typing at opposite ends of the page at the same
instant, and all three copies, both browsers and the server, ended up identical
with neither edit lost.

If a client ever does drift, it notices the length disagrees and asks for the
whole page again. That is the safety net under all of it.

---

## How the filtering works

**A dictionary lookup, and nothing slower.** After every edit the page is scanned
and anything blocked is deleted, as an ordinary edit that everyone receives. So a
word disappears mid-sentence as you finish typing it, for you and the room at the
same instant.

Terms are normalised before lookup, so spacing, punctuation, number substitutions,
stretched letters, long-vowel spellings and aspirated consonants all collapse onto
one entry. The dictionary carries one line instead of forty.

**Phrases too.** Some abuse is innocent word by word. `behen ke lode` is the
reason this exists: `behen` means sister and is protected, `ke` is a postposition,
and only the last word is blockable. Removing just that word left the rest of the
phrase sitting on the page reading exactly like what it is.

**Near misses count.** A deliberate misspelling that is one or two edits away from
a blocked term is removed too. An earlier version merely underlined those, which
was wrong: underlining a slur is not filtering it.

### How well it works

| | Result |
|---|---|
| Labelled cases correct | 279 / 279 |
| Let something through | 0 |
| Blocked an ordinary word | 0 |
| Phrase cases correct | 10 / 10 |
| Ordinary vocabulary damaged | 0 of 927 |
| Speed | tens of thousands of words per second |

The last two rows matter as much as the first. A filter that eats `class`,
`coming` or an ordinary Hindi word stops the activity dead, so the dictionary is
checked against a corpus of common English and Hindi vocabulary on every change.

### Adding a term mid-session

Easiest: type it into **Block a word** in the host sidebar.

Permanently: add it to `wordlist.txt` under `[exact]`, or under `[phrases]` if it
is only abusive as a sequence, and save. The server reloads it on the next edit.
No restart, nobody disconnected.

After editing, always:

```bash
python filter.py --collisions
```

---

## Testing

```bash
python test_filter.py
```

The one to run. Checks the dictionary against the labelled cases in
`test_cases.txt`, checks the phrases, and checks nothing ordinary is damaged.
Takes a fraction of a second, needs nothing installed, exits non-zero on failure
so it works in CI.

Add your own cases to `test_cases.txt` using `[block:name]` and `[allow:name]`
headings.

```bash
python filter.py
```

Shows what the dictionary does with sample inputs, and how long it takes.

---

## The model, and why it is not in the live path

There was one. It was measured and removed.

The best local model tested answered in about 750 ms per word, warm and idle. With
thirty people typing that becomes a queue, on the same laptop serving all of them,
with a multi-gigabyte model resident in RAM.

It also was not earning its place:

| | Dictionary | Model |
|---|---|---|
| Correct | 250 / 250 | 228 / 250 |
| Let something through | 0 | 15 |
| Blocked an ordinary word | 0 | 7 |

It missed every regional-language term it was shown, and wanted to block `kill`
and `die`. In a story game, deleting somebody's ordinary word is worse than
missing a rare one.

So it now runs **before** the session, where slow is free, and everything it finds
becomes a dictionary entry that costs microseconds live:

```bash
python expand.py --seed <a term already blocked>
```

It proposes spellings and variants, discards anything already covered or that
would clash with ordinary vocabulary, and asks you before writing anything.

---

## Troubleshooting

**Nobody else can connect.** Almost always the firewall. Windows shows a dialog
the first time and it is easy to dismiss. Allow Python on Private networks, or run
this in an Administrator terminal:

```bash
netsh advfirewall firewall add rule name="Chaos Draft" dir=in action=allow protocol=TCP localport=8000
```

**Campus wifi blocks device-to-device traffic.** Some networks isolate clients and
no firewall change helps. Use a phone hotspot. Test with one phone before the
session either way.

**The address is wrong.** The server guesses, and can pick the wrong adapter if
you have a VPN or virtual machines. Get the right one with `ipconfig` and pass
`--ip`.

**It says reconnecting.** It reconnects on its own and resyncs. The page lives on
the server, so nothing is lost.

---

## Files

| File | What |
|---|---|
| `server.py` | The server. Shared document, filtering, host controls. |
| `ot.py` | Operational transform. How thirty people edit one string. |
| `filter.py` | The filtering logic. Run it directly to test. |
| `wordlist.txt` | Terms to block, phrases to block, ordinary words to protect. |
| `safe_words.txt` | Vocabulary the collision check runs against. Not used live. |
| `test_filter.py` | Tests. Run after any change to the dictionary. |
| `test_cases.txt` | The labelled cases it tests against. |
| `expand.py` | Grows the dictionary before a session, with your approval. |
| `static/index.html` | The whole page. No build step, no dependencies. |
