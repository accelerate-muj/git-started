# Chaos Draft

The warm-up activity, run in the fifteen minutes before the git workshop starts.

Everyone writes one story together. One word each, no turn order, as fast as they
can type. It descends into nonsense almost immediately, which is the point. A bot
reads every word before it reaches the page and quietly eats the ones that should
not be there.

It runs on your laptop. Everyone joins over the room's wifi. Nothing leaves the
network and there are no accounts.

---

## Running it

```bash
cd chaos-draft && python server.py
```

```
  Chaos Draft
  163 blocked terms, 38 roots

  Everyone opens:  http://192.168.1.42:8000
  You open:        http://192.168.1.42:8000/?key=host
```

Put the first URL on the projector. Open the second one yourself, which gives you
Undo and Reset buttons nobody else has.

Requirements: Python 3.9 or newer, and `pip install fastapi uvicorn`.

### Options

```bash
python server.py --port 8080
python server.py --cooldown 0
python server.py --cooldown 2.5
python server.py --host-key something-else
python server.py --audit
```

`--cooldown` is seconds each person must wait between words. It defaults to 1. Set
it to `0` for genuine chaos, or raise it if two fast typists are drowning everyone
else out.

---

## How the filter works, and why

Every word is checked before it goes anywhere. The check takes **single-digit
microseconds**, so a word appears on thirty screens as fast as the wifi can carry
it.

The obvious design was to ask a small local language model whether each word was
acceptable. That was measured first, on `gemma3:1b` through ollama, and it failed
badly enough to throw out:

| | Result |
|---|---|
| Latency | **~2,500 ms per word.** Nowhere near real time. |
| `behenchod` | **Allowed.** One of the worst words, waved straight through. |
| `randi` | **Allowed.** |
| `kutta` | **Blocked.** It means "dog". |
| `saala` | **Blocked.** Mild, extremely common, and fine in a story. |

So the model is not the gate. A normalised set lookup is the gate. It is about
300,000 times faster and, on the words that matter, considerably more accurate.

### Normalisation is the interesting part

People try to get past filters, and a plain wordlist is beaten in seconds. Every
one of these hits the single blocklist entry `chutiya`:

```
chutiya    CHUTIYAAAAA    ch00tiya    c-h-u-t-i-y-a    ch@t1ya    chootiya
```

The pipeline that gets them all there:

1. Lowercase, and strip accents.
2. Fold leetspeak. `0` becomes `o`, `3` becomes `e`, `@` becomes `a`, and so on.
3. Delete everything that is not a letter, so punctuation and spacing tricks die.
4. Collapse stretched letters, so `fuuuuck` becomes `fuck`.
5. Fold long-vowel spellings, so `chootiya` becomes `chutiya` and `raandi`
   becomes `randi`. Romanised Hindi has no single correct spelling, and this is
   what lets the wordlist carry one entry instead of eight.

Devanagari is matched directly, without any of that, because decomposing it would
pull the matras off the consonants and break the match.

### Not blocking ordinary words

The opposite failure is worse in a story game. If `class` and `pass` and `grass`
get eaten because they contain `ass`, the activity stops being fun immediately.

Two things prevent it:

- The wordlist has **two sections**. `[exact]` terms must match the whole word,
  which is where short risky ones like `ass` live. `[contains]` is only for long
  roots that cannot appear inside anything innocent, like `madarchod`.
- An **allowlist** is checked first. It includes `chudail`, which means witch, is a
  perfectly good story word, and contains a root we block.

Verified against 184 ordinary English and Hindi words: **zero false positives.**

### Check it yourself

```bash
python filter.py
```

```
  allow  chudail                   0 us  allowlisted
  BLOCK  b3h3nch0d                 4 us  blocked  <- behenchod
  BLOCK  ch00tiya                  7 us  blocked  <- chutiya
  allow  grass                     0 us  allowlisted
  BLOCK  गांडू                     1 us  blocked  <- गांडू
```

```bash
python filter.py somevword anotherword
```

---

## During the session

**Adding a word to the blocklist live.** Open `wordlist.txt`, add the word under
`[exact]`, save. The server notices the file changed and reloads on the next
submission. No restart, nobody gets disconnected.

**Someone got something through.** Undo removes the last word. Reset clears
everything. Both are yours only, via the `?key=` URL.

**Saving the story.** Copy story, or open `/story.txt`.

**The counter.** Everyone sees how many words the bot has eaten, but never which
ones. That keeps the filter part of the fun without putting the words on the
projector, which is the entire reason it is only a number.

---

## The optional second opinion

```bash
python server.py --audit
```

With this on, words that pass the blocklist are *also* sent to a local ollama model
in the background. This happens **after** the word is already visible and never
delays anything. If the model objects, the word is struck through a few seconds
later and written into `wordlist.txt` so it is caught instantly from then on.

It is off by default because, per the measurements above, it misses obvious cases
and objects to harmless ones. Its one real virtue is that the list improves during
a session. Treat it as a supplement, never as the gate.

Needs ollama running with a model pulled:

```bash
ollama serve
```

```bash
ollama pull gemma3:1b
```

---

## Troubleshooting

**Nobody else can connect.** Almost always the firewall. On Windows the first run
pops a dialog asking whether to allow Python on the network, and it is easy to
dismiss by accident. Allow it for Private networks, or:

```bash
netsh advfirewall firewall add rule name="Chaos Draft" dir=in action=allow protocol=TCP localport=8000
```

**Campus wifi blocks device-to-device traffic.** Some networks isolate clients from
each other, so no amount of firewall fixing will help. Test with one phone before
the session. If it fails, a phone hotspot works fine for thirty people.

**The address is wrong.** The server guesses your LAN IP and can pick the wrong
adapter if you have VPNs or virtual machines. Get the right one with `ipconfig` on
Windows or `ip addr` elsewhere, and hand out that address on the same port.

**It says reconnecting.** The page reconnects by itself when the wifi drops, which
it will. The story is held on the server, so nothing is lost.

---

## Files

| File | What |
|---|---|
| `server.py` | WebSocket server, room state, host controls |
| `filter.py` | The gate. Normalisation and matching. Run it directly to test. |
| `wordlist.txt` | The blocklist, with a long comment explaining the two sections |
| `static/index.html` | The whole client. No build step, no dependencies. |

---

## Why this is in a git workshop repo

It is not about git, and it is a good thing to have built. If anyone asks how it
works after the session, the answer touches Unicode normalisation, WebSockets,
adversarial input, and the habit of measuring an approach before committing to it.

The filter is what it is because the first design was tested and found wanting.
That is worth more than the code.
