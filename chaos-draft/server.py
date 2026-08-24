"""
Chaos Draft: a collaborative story, one word at a time, with a filter in the way.

Run it on the machine that will act as the server:

    python server.py

It prints a LAN address. Everyone on the same wifi opens that, types a name, and
starts adding words. There is no turn order, which is the point.

    python server.py --cooldown 0     no rate limit at all
    python server.py --port 8080

THE PIPELINE
------------
Every word takes a dictionary lookup and nothing else. Nothing on this path waits
for anything.

    blocked         -> rejected instantly, only the sender is told
    near a blocked  -> published instantly, and underlined for the host
    clean           -> published instantly

The host can remove any word at any time with one click, which also writes it into
the dictionary so it is caught instantly from then on.

WHY THERE IS NO MODEL IN HERE
-----------------------------
There was, briefly. It was measured and removed.

The best local model tested answered in ~750 ms warm and idle. With thirty people
typing that becomes a queue, on the same laptop that is serving all of them, with
a multi-gigabyte model resident in RAM. And it did not buy anything: on a 250-case
labelled set the dictionary alone scored 250/250, while the model scored 228/250,
missed every regional-language term it was shown, and wanted to block "kill" and
"die".

The model is still used, just not here. expand.py runs it BEFORE the session to
propose new dictionary entries for a human to approve, where taking a second per
word costs nobody anything.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import secrets
import socket
import time
from contextlib import suppress
from dataclasses import dataclass, field, asdict
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, PlainTextResponse

from filter import Decision, Dictionary

HERE = Path(__file__).parent
MAX_WORD_LEN = 40
MAX_NAME_LEN = 24


@dataclass
class Word:
    i: int
    text: str
    author: str
    flagged: bool = False
    ts: float = field(default_factory=time.time)


class Room:
    """All the state. One room, which is all a single workshop needs."""

    def __init__(self, cooldown: float):
        self.words: list[Word] = []
        self.clients: dict[WebSocket, str] = {}
        self.hosts: set[WebSocket] = set()
        self.last_post: dict[str, float] = {}
        self.blocked_count = 0
        self.cooldown = cooldown
        self.dictionary = Dictionary()
        self.lock = asyncio.Lock()

    # -- sending ------------------------------------------------------------

    async def send(self, ws: WebSocket, payload: dict) -> None:
        with suppress(Exception):
            await ws.send_text(json.dumps(payload))

    async def broadcast(self, payload: dict) -> None:
        message = json.dumps(payload)
        dead = []
        for ws in list(self.clients):
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.clients.pop(ws, None)

    def snapshot(self) -> dict:
        return {
            "type": "state",
            "words": [asdict(w) for w in self.words],
            "users": sorted(set(self.clients.values())),
            "blocked": self.blocked_count,
        }

    async def broadcast_presence(self) -> None:
        await self.broadcast({"type": "presence",
                              "users": sorted(set(self.clients.values()))})

    # -- the pipeline -------------------------------------------------------

    async def submit(self, ws: WebSocket, name: str, raw: str) -> None:
        text = " ".join(raw.split())[:MAX_WORD_LEN]
        if not text:
            return
        if " " in text:
            await self.send(ws, {"type": "rejected", "word": text,
                                 "reason": "One word at a time. That is the whole game."})
            return

        now = time.time()
        elapsed = now - self.last_post.get(name, 0.0)
        if self.cooldown and elapsed < self.cooldown:
            await self.send(ws, {"type": "rejected", "word": text,
                                 "reason": f"Slow down, {self.cooldown - elapsed:.1f}s to go."})
            return

        # Picks up edits to wordlist.txt mid-session without a restart.
        self.dictionary.reload_if_changed()
        verdict = self.dictionary.check(text)

        # Tier 1 said no. Nothing else runs.
        if verdict.decision is Decision.BLOCK:
            await self.reject(ws, text, verdict.micros)
            return

        # Tier 1 was unsure: near a blocked term but not a match. Publish it and
        # flag it, so the host sees it underlined and can remove it with one click.
        #
        # Nothing waits for a model here. That was tried and removed. Even at its
        # best a local model answered in about 750 ms warm and idle, which with
        # thirty people typing turns into a queue, on the same laptop that is
        # serving all of them. The dictionary scores 250/250 on the test set
        # without it. See expand.py for where the model is genuinely useful.
        if verdict.decision is Decision.REVIEW:
            await self.publish(name, text, verdict.micros, flagged=True)
            return

        # Tier 1 found nothing to worry about, so it goes straight up.
        await self.publish(name, text, verdict.micros)

    async def reject(self, ws: WebSocket, text: str, micros: int, tier: int = 1) -> None:
        self.blocked_count += 1
        name = self.clients.get(ws, "someone")

        # The sender is told, and nobody else in the room is. Everyone just sees
        # the counter move, which keeps the filter part of the game without
        # putting the word up on the projector.
        await self.send(ws, {"type": "rejected", "word": text,
                             "reason": "Not that one.", "micros": micros, "tier": tier})
        await self.broadcast({"type": "blocked_count", "blocked": self.blocked_count})

        # The host does see it. During a session that is how you notice one person
        # repeatedly trying it on. It is also the only way to demonstrate that the
        # filter is doing anything at all, since by design the evidence is invisible.
        for host in list(self.hosts):
            await self.send(host, {"type": "caught", "word": text,
                                   "author": name, "micros": micros})

    async def publish(self, name: str, text: str, micros: int,
                      flagged: bool = False) -> Word | None:
        async with self.lock:
            word = Word(i=len(self.words), text=text, author=name, flagged=flagged)
            self.words.append(word)
        self.last_post[name] = time.time()
        await self.broadcast({"type": "word", "word": asdict(word), "micros": micros})
        return word

    # -- tier 3, the host ---------------------------------------------------

    async def withdraw(self, i: int, learn: bool) -> None:
        """Remove a word that is already live, and optionally remember it."""
        async with self.lock:
            if not (0 <= i < len(self.words)):
                return
            text = self.words[i].text
            if not text:
                return
            self.words[i].text = ""
            self.words[i].flagged = False
            self.blocked_count += 1
        if learn and text:
            with suppress(Exception):
                self.dictionary.add(text)
        await self.broadcast({"type": "withdrawn", "i": i,
                              "blocked": self.blocked_count})

    async def undo(self) -> None:
        async with self.lock:
            if self.words:
                self.words.pop()
        await self.broadcast(self.snapshot())

    async def reset(self) -> None:
        async with self.lock:
            self.words.clear()
            self.blocked_count = 0
        self.last_post.clear()
        await self.broadcast(self.snapshot())

    def as_text(self) -> str:
        return " ".join(w.text for w in self.words if w.text)


def make_app(room: Room, host_key: str) -> FastAPI:
    app = FastAPI(title="Chaos Draft")

    @app.get("/")
    async def index():
        return FileResponse(HERE / "static" / "index.html")

    @app.get("/story.txt", response_class=PlainTextResponse)
    async def story():
        return room.as_text()

    @app.websocket("/ws")
    async def ws_endpoint(ws: WebSocket):
        await ws.accept()
        name = ""
        is_host = False
        try:
            while True:
                msg = json.loads(await ws.receive_text())
                kind = msg.get("type")

                if kind == "join":
                    proposed = " ".join(str(msg.get("name", "")).split())[:MAX_NAME_LEN]
                    if not proposed:
                        await room.send(ws, {"type": "error", "reason": "Pick a name."})
                        continue
                    name = proposed
                    is_host = msg.get("key") == host_key
                    room.clients[ws] = name
                    if is_host:
                        room.hosts.add(ws)
                    await room.send(ws, {**room.snapshot(), "you": name,
                                         "isHost": is_host})
                    await room.broadcast_presence()

                elif kind == "word" and name:
                    await room.submit(ws, name, str(msg.get("text", "")))

                elif is_host and kind == "withdraw":
                    await room.withdraw(int(msg.get("i", -1)),
                                        learn=bool(msg.get("learn", True)))
                elif is_host and kind == "undo":
                    await room.undo()
                elif is_host and kind == "reset":
                    await room.reset()

        except WebSocketDisconnect:
            pass
        except Exception:
            pass
        finally:
            room.clients.pop(ws, None)
            room.hosts.discard(ws)
            if name:
                await room.broadcast_presence()

    return app


KEY_FILE = HERE / ".host-key"


def host_key_for_run(explicit: str | None, rotate: bool) -> tuple[str, str]:
    """
    Work out the host key, and say where it came from.

    Order of preference:
      1. --host-key on the command line, for when you want to choose it yourself
      2. .host-key next to this file, so the URL survives a restart
      3. a fresh random one, saved to .host-key for next time

    There is deliberately no fixed default. This repository is public, so any key
    written into the code or the README would be a key everybody in the room
    already has, and the host controls include wiping the story for everyone.

    .host-key is gitignored. It should never be committed.
    """
    if explicit:
        return explicit, "from --host-key"

    if rotate and KEY_FILE.exists():
        KEY_FILE.unlink()

    if KEY_FILE.exists():
        saved = KEY_FILE.read_text(encoding="utf-8").strip()
        if saved:
            return saved, f"reused from {KEY_FILE.name}"

    key = secrets.token_urlsafe(9)
    try:
        KEY_FILE.write_text(key + "\n", encoding="utf-8")
        # Best effort. Does very little on Windows, and costs nothing to try.
        with suppress(Exception):
            KEY_FILE.chmod(0o600)
        return key, f"new, saved to {KEY_FILE.name}"
    except OSError:
        # Read-only checkout or similar. Still works, just not across restarts.
        return key, "new, could not be saved"


def lan_ip() -> str:
    """Best guess at the address other machines can reach, without sending traffic."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def main() -> None:
    p = argparse.ArgumentParser(description="Chaos Draft server")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--cooldown", type=float, default=1.0,
                   help="Seconds a person waits between words. 0 disables it.")
    p.add_argument("--host-key",
                   help="Pin the host key yourself. Otherwise one is generated and "
                        "remembered in .host-key so your URL survives a restart.")
    p.add_argument("--new-key", action="store_true",
                   help="Throw away the saved key and generate a new one.")
    args = p.parse_args()

    host_key, key_origin = host_key_for_run(args.host_key, args.new_key)

    room = Room(cooldown=args.cooldown)
    app = make_app(room, host_key)

    ip = lan_ip()
    d = room.dictionary
    print()
    print("  Chaos Draft")
    print(f"  dictionary: {len(d.exact)} terms, {len(d.contains)} roots, "
          f"{len(d.allow)} protected")
    print()
    print(f"  Everyone opens:   http://{ip}:{args.port}")
    print(f"  Host controls:    http://{ip}:{args.port}/?key={host_key}")
    print(f"                    ^ yours only, {key_origin}.")
    print("                    Same after a restart. Do not put it on the projector.")
    print()
    print(f"  Cooldown: {args.cooldown}s")
    print("  Edit wordlist.txt during the session and it takes effect immediately.")
    print()

    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
