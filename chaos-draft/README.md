# Chaos Draft

The warm-up activity, run in the fifteen minutes before the git workshop starts.

Everyone writes one story together. One word each, no turn order, as fast as they
can type. It falls apart almost immediately, which is the point.

It runs on one laptop. Everyone joins over the room wifi. Nothing leaves the
network and nobody makes an account.

---

## The activity

1. The host starts the server and puts the address on the projector.
2. Everyone opens it on a phone or laptop and types a name.
3. Someone types the first word.
4. Everybody else adds one word at a time, whenever they like.
5. After ten minutes, read the result out loud.

There is no turn order and no plan. Two people will try to steer the story in
opposite directions at the same time, and that is the entire joke.

A filter checks every word before it reaches the page and quietly drops anything
inappropriate, in English and Hindi. Participants do not need to think about it.
Everyone can see a counter of how many words it has dropped, but never which ones.

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

The server prints two addresses:

```
  Everyone opens:   http://192.168.1.42:8000
  Host controls:    http://192.168.1.42:8000/?key=XXXXXXXXXXXX
                    ^ yours only. Do not put this on the projector.
```

Put the **first** on the projector. Open the **second** yourself.

The second one is the same page plus the controls that let you remove words and
wipe the story.

The key is generated the first time you run the server and saved to `.host-key`,
so **your host URL is the same every time**, including after a restart mid-session.
It is printed only in your own terminal, and `.host-key` is gitignored so it never
reaches the repository.

There is no fixed default, deliberately. This repository is public, so any key
written down here would be a key everyone in the room already has, and the host
controls include wiping the story for all thirty of them.

Keep that URL to yourself. If it leaks:

```bash
python server.py --new-key
```

Needs Python 3.9 or newer.

### Host controls

| Button | Does |
|---|---|
| **Copy story** | Puts the whole story on your clipboard. Also at `/story.txt`. |
| **Undo** | Removes the last word. |
| **Reset** | Clears everything and starts over. |

### Options

```bash
python server.py --cooldown 0
```

How many seconds each person waits between words. Defaults to 1. Set it to `0` for
genuine chaos, or raise it if two fast typists are drowning everyone else out.

```bash
python server.py --port 8080
```

```bash
python server.py --host-key your-own-secret
```

Pins a key you choose, instead of the saved random one. Do not pick something
guessable.

```bash
python server.py --new-key
```

Discards the saved key and generates a new one. Use this if your host URL leaks.

---

## How the filtering works

Three layers, and only the first one runs while people are typing.

**1. Dictionary.** A list of terms to block, in English, Hindi, Devanagari and
eight other Indian languages. Words are normalised before lookup, so spacing,
punctuation, number substitutions, stretched letters and alternative spellings all
collapse onto the same entry. If a word is not an exact match but is very close to
one, it still goes up but is underlined for the host.

This is the whole runtime path. Measured end to end, browser to server and back,
firing words as fast as a machine can send them: **median 14 ms, worst case 19 ms.**

**2. You.** Click any underlined word, or any word at all, to remove it. It is also
written into the dictionary, so it is caught instantly from then on.

**3. A model, before the session.** `expand.py` uses a local language model to
propose new dictionary entries, which you approve one at a time. It runs beforehand,
never during.

### Why the model does not run during the session

It used to. It was measured and removed.

The best local model tested answered in about 750 ms per word, warm and idle. With
thirty people typing that becomes a queue, on the same laptop that is also serving
all of them, with a multi-gigabyte model sitting in RAM.

It also was not earning its place. On a 250-word labelled test set:

| | Dictionary | Model |
|---|---|---|
| Correct | 250 / 250 | 228 / 250 |
| Let something through | 0 | 15 |
| Blocked an ordinary word | 0 | 7 |
| Time per word | under 0.03 ms | ~750 ms |

The model missed every regional-language term it was shown, and wanted to block
`kill`, `die` and `niggle`. In a story-writing game, deleting somebody's ordinary
word is worse than missing a rare one.

So the model now does its work in advance, where being slow costs nobody anything,
and everything it finds becomes a dictionary entry that costs microseconds at run
time.

```bash
python expand.py --seed <a term already blocked>
```

It proposes spellings and variants, discards anything already covered or that would
clash with ordinary vocabulary, and asks you before writing anything.

### Adding a term mid-session

Open `wordlist.txt`, add the term under `[exact]`, and save. The server notices the
file changed and picks it up on the next word. No restart, nobody disconnected.

After editing, run the safety check:

```bash
python filter.py --collisions
```

This verifies that nothing in the dictionary accidentally blocks an ordinary word.
That failure matters more than it sounds: a filter that eats `class`, `pass` or
`coming` stops the activity dead. The check runs against a corpus of common English
and Hindi vocabulary and must report no collisions.

### How well it works

Tested against a labelled set of 250 words, half of which should be blocked and
half of which are ordinary English and Hindi vocabulary:

| | Result |
|---|---|
| Dictionary, correct | 250 / 250 |
| Let something through | 0 |
| Blocked an ordinary word | 0 |
| Speed | over 40,000 words per second |

The second number matters more than the first. A filter that eats `class`, `pass`
or `coming` stops the activity dead, so the dictionary is checked against a corpus
of common vocabulary on every change and must never touch any of it.

### Testing

```bash
python filter.py
```

Shows what the dictionary does with a set of sample inputs, and how long it takes.

```bash
python test_ai.py
```

Runs the model against the 250-word labelled set and reports how many it got wrong
in each direction. Only relevant if you are changing `expand.py`. Takes about ten
minutes, because the model is slow, which is the entire reason it is not in the
live path.

---

## Troubleshooting

**Nobody else can connect.** Almost always the firewall. Windows shows a dialog the
first time you run it, and it is easy to dismiss by accident. Allow Python on
Private networks, or:

```bash
netsh advfirewall firewall add rule name="Chaos Draft" dir=in action=allow protocol=TCP localport=8000
```

**Campus wifi blocks device-to-device traffic.** Some networks isolate clients from
each other, and no firewall change will help. Test with one phone before the
session. If it fails, a phone hotspot handles thirty people fine.

**The address is wrong.** The server guesses your network address and can pick the
wrong adapter if you have a VPN or virtual machines. Get the right one with
`ipconfig` on Windows or `ip addr` elsewhere, and hand that out on the same port.

**It says reconnecting.** The page reconnects on its own when wifi drops. The story
lives on the server, so nothing is lost.

---

## Files

| File | What |
|---|---|
| `server.py` | The server. Room state, host controls, connections. |
| `filter.py` | The filtering logic. Run it directly to test. |
| `wordlist.txt` | The terms to block, and the ordinary words to protect. |
| `safe_words.txt` | Vocabulary used by the collision check. Not used at runtime. |
| `expand.py` | Grows the dictionary before a session, using a model, with your approval. |
| `test_ai.py` | Measures how accurate that model actually is. |
| `static/index.html` | The whole page. No build step, no dependencies. |
