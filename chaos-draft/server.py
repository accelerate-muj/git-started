"""
Chaos Draft: a collaborative story, one word at a time, with a filter in the way.

Run it on the machine that will act as the server:

    python server.py

It prints a LAN address. Everyone on the same wifi opens that, types a name, and
starts adding words. There is no turn order, which is the point.

    python server.py --cooldown 0     no rate limit at all
    python server.py --ai             enable the second-opinion layer
    python server.py --port 8080

THE PIPELINE
------------
Each word takes one of four routes, and only one of them is slow.

    dictionary says blocked   -> rejected instantly, sender is told
    dictionary says allowed   -> published instantly
    dictionary found nothing  -> published instantly
    dictionary is unsure      -> held for the AI, under a second typically, then
                                 rejected if the model objects, or published and
                                 flagged for the host if it does not

Only the last route ever makes anybody wait, and on a 250-word test set it was
taken 6 times. Everything else is a dictionary lookup in microseconds.

The AI is never asked about a word the dictionary was happy with. Measured on that
same test set, left to audit ordinary vocabulary it wanted to block "kill", "die"
and "niggle", and deleting somebody's ordinary word is worse here than missing a
rare one.

The host can withdraw any word at any time, which also adds it to the dictionary
so it is caught instantly from then on.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import socket
import time
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass, field, asdict
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, PlainTextResponse

from filter import Auditor, Decision, Dictionary

HERE = Path(__file__).parent
MAX_WORD_LEN = 40
MAX_NAME_LEN = 24
HOLD_TIMEOUT = 6.0   # seconds a borderline word waits on the AI before going live


@dataclass
class Word:
    i: int
    text: str
    author: str
    flagged: bool = False
    ts: float = field(default_factory=time.time)


class Room:
    """All the state. One room, which is all a single workshop needs."""

    def __init__(self, cooldown: float, use_ai: bool):
        self.words: list[Word] = []
        self.clients: dict[WebSocket, str] = {}
        self.last_post: dict[str, float] = {}
        self.blocked_count = 0
        self.cooldown = cooldown
        self.use_ai = use_ai
        self.dictionary = Dictionary()
        self.auditor = Auditor()
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
            "ai": bool(self.use_ai and self.auditor.available),
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

        # Tier 1 was unsure. Hold it and ask tier 2. This is the only path that
        # ever makes anybody wait, and it is rare.
        if verdict.decision is Decision.REVIEW:
            if not self.use_ai:
                # No second opinion available, so publish and flag it for a human.
                await self.publish(name, text, verdict.micros, flagged=True)
                return
            await self.send(ws, {"type": "holding", "word": text})
            try:
                objected = await asyncio.wait_for(
                    self.auditor.check(text), timeout=HOLD_TIMEOUT)
            except asyncio.TimeoutError:
                objected = None
            if objected is True:
                await self.reject(ws, text, verdict.micros, tier=2)
                return
            # The model cleared it, or could not be reached. Publish it either way,
            # but ALWAYS flag it for the host, whatever the model said. Tier 1 was
            # suspicious for a reason, and the model is measurably unreliable on
            # exactly this class of word: on the 250-case set it waved through
            # every regional-language term it was shown. Its opinion is worth
            # having and is not worth trusting on its own.
            await self.publish(name, text, verdict.micros, flagged=True)
            return

        # Tier 1 found nothing to worry about, so it goes straight up.
        #
        # The AI is deliberately NOT consulted here. It was tested on 250 labelled
        # words and, left to audit ordinary vocabulary, it wanted to block "kill",
        # "die" and "niggle". In a story-writing game, deleting somebody's
        # perfectly good word is worse than missing a rare one, and the host can
        # remove anything that slips through. So tier 2 only ever arbitrates words
        # tier 1 already found suspicious.
        await self.publish(name, text, verdict.micros)

    async def reject(self, ws: WebSocket, text: str, micros: int, tier: int = 1) -> None:
        self.blocked_count += 1
        # Only the sender is told what was rejected. Everyone else sees the counter
        # move, which keeps the filter part of the game without putting the word on
        # the projector.
        await self.send(ws, {"type": "rejected", "word": text,
                             "reason": "Not that one.", "micros": micros, "tier": tier})
        await self.broadcast({"type": "blocked_count", "blocked": self.blocked_count})

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
    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if room.use_ai:
            found = await room.auditor.ping()
            print(f"  AI layer: {found}" if found
                  else "  AI layer: NO MODEL REACHABLE, continuing without it")
        yield

    app = FastAPI(title="Chaos Draft", lifespan=lifespan)

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
            if name:
                await room.broadcast_presence()

    return app


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
    p.add_argument("--ai", action="store_true",
                   help="Second-opinion layer via a local ollama model.")
    p.add_argument("--host-key", default="host",
                   help="Secret that unlocks the host controls. Append ?key=... to the URL.")
    args = p.parse_args()

    room = Room(cooldown=args.cooldown, use_ai=args.ai)
    app = make_app(room, args.host_key)

    ip = lan_ip()
    d = room.dictionary
    print()
    print("  Chaos Draft")
    print(f"  dictionary: {len(d.exact)} terms, {len(d.contains)} roots, "
          f"{len(d.allow)} protected")
    print()
    print(f"  Everyone opens:  http://{ip}:{args.port}")
    print(f"  You open:        http://{ip}:{args.port}/?key={args.host_key}")
    print()
    print(f"  Cooldown: {args.cooldown}s   AI layer: {'on' if args.ai else 'off'}")
    print("  Edit wordlist.txt during the session and it takes effect immediately.")
    print()

    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
