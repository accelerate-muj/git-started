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
  Everyone opens:  http://192.168.1.42:8000
  You open:        http://192.168.1.42:8000/?key=host
```

Put the first on the projector. Open the second yourself. It is the same page plus
the host controls, which nobody else gets.

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
python server.py --host-key something-else
```

Changes the secret in your host URL, if you would rather people did not guess it.

```bash
python server.py --ai
```

Turns on the second-opinion check described below. Off by default.

---

## How the filtering works

Three layers, in order, so the fast one does almost all the work.

**1. Dictionary.** A list of terms to block, in English, Hindi and several other
Indian languages. Words are normalised before being looked up, so spacing,
punctuation, number substitutions, stretched letters and alternative spellings all
collapse onto the same entry. This answers in well under a millisecond and handles
the overwhelming majority of cases.

**2. AI.** For words that look close to a blocked term but are not an exact match,
a small language model running locally on the same laptop gives a second opinion.
This is slower, so it only ever sees the handful of borderline words in a session,
never ordinary ones. Off by default, enable with `--ai`. It needs
[ollama](https://ollama.com) running with a model pulled:

```bash
ollama pull gemma4:e2b
```

**3. You.** The host can remove any word that got through, at any time, with one
click. Removing it also adds it to the dictionary permanently, so it is caught
instantly from then on.

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

Runs the AI layer against a labelled test set and reports how many things it got
wrong in each direction. Takes about ten minutes.

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
| `test_ai.py` | Test suite for the AI layer. |
| `static/index.html` | The whole page. No build step, no dependencies. |
