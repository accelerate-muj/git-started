"""
Chaos Draft: a collaborative story, one word at a time, with a bot in the way.

Run it on the machine that will act as the server:

    python server.py

It prints a LAN address. Everyone on the same wifi opens that, types a name, and
starts adding words. There is no turn order, which is the point.

    python server.py --port 8080 --cooldown 0        no rate limit at all
    python server.py --audit                          enable the ollama second pass

The filter is in filter.py and answers in single-digit microseconds, so a word
appears on everyone's screen as fast as the network allows. Read the comment at the
top of filter.py for why it is a set lookup and not a language model.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import socket
import time
from contextlib import suppress
from dataclasses import dataclass, field, asdict
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, PlainTextResponse

from filter import Filter, audit

HERE = Path(__file__).parent
MAX_WORD_LEN = 40
MAX_NAME_LEN = 24


@dataclass
class Word:
    i: int
    text: str
    author: str
    ts: float = field(default_factory=time.time)


class Room:
    """All the state. One room, which is all a single workshop needs."""

    def __init__(self, cooldown: float, use_audit: bool):
        self.words: list[Word] = []
        self.clients: dict[WebSocket, str] = {}
        self.last_post: dict[str, float] = {}
        self.blocked_count = 0
        self.retracted_count = 0
        self.cooldown = cooldown
        self.use_audit = use_audit
        self.filter = Filter()
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
            "retracted": self.retracted_count,
        }

    async def broadcast_presence(self) -> None:
        await self.broadcast({
            "type": "presence",
            "users": sorted(set(self.clients.values())),
        })

    # -- the hot path -------------------------------------------------------

    async def submit(self, ws: WebSocket, name: str, raw: str) -> None:
        text = " ".join(raw.split())[:MAX_WORD_LEN]

        if not text:
            return
        if " " in text:
            await self.send(ws, {
                "type": "rejected", "word": text,
                "reason": "One word at a time. That is the whole game.",
            })
            return

        now = time.time()
        if self.cooldown and now - self.last_post.get(name, 0.0) < self.cooldown:
            wait = self.cooldown - (now - self.last_post.get(name, 0.0))
            await self.send(ws, {
                "type": "rejected", "word": text,
                "reason": f"Slow down, {wait:.1f}s to go.",
            })
            return

        # Picks up edits to wordlist.txt mid-session without a restart.
        self.filter.reload_if_changed()
        verdict = self.filter.check(text)

        if not verdict.allowed:
            self.blocked_count += 1
            # Only the sender is told what was rejected. Everyone else sees the
            # counter tick up, which turns the filter into part of the game
            # without broadcasting the word to the room.
            await self.send(ws, {
                "type": "rejected", "word": text,
                "reason": "The bot ate that one.", "micros": verdict.micros,
            })
            await self.broadcast({"type": "blocked_count", "blocked": self.blocked_count})
            return

        async with self.lock:
            word = Word(i=len(self.words), text=text, author=name)
            self.words.append(word)
        self.last_post[name] = now

        await self.broadcast({"type": "word", "word": asdict(word),
                              "micros": verdict.micros})

        if self.use_audit:
            asyncio.create_task(self._audit_later(word))

    async def _audit_later(self, word: Word) -> None:
        """
        Second opinion, after the fact. Never blocks the word appearing.

        If the model says the word should not have passed, it is struck through for
        everyone and added to wordlist.txt so it is caught instantly next time.
        """
        should_block = await audit(word.text)
        if not should_block:
            return
        async with self.lock:
            if word.i >= len(self.words) or self.words[word.i].text != word.text:
                return
            self.words[word.i].text = ""
            self.retracted_count += 1
        with suppress(Exception):
            self.filter.add(word.text)
        await self.broadcast({
            "type": "retracted", "i": word.i,
            "retracted": self.retracted_count,
        })

    # -- host controls ------------------------------------------------------

    async def undo(self) -> None:
        async with self.lock:
            if self.words:
                self.words.pop()
        await self.broadcast(self.snapshot())

    async def reset(self) -> None:
        async with self.lock:
            self.words.clear()
            self.blocked_count = 0
            self.retracted_count = 0
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
        try:
            while True:
                msg = json.loads(await ws.receive_text())
                kind = msg.get("type")

                if kind == "join":
                    proposed = " ".join(str(msg.get("name", "")).split())[:MAX_NAME_LEN]
                    if not proposed:
                        await ws.send_text(json.dumps({
                            "type": "error", "reason": "Pick a name."}))
                        continue
                    name = proposed
                    room.clients[ws] = name
                    await ws.send_text(json.dumps({
                        **room.snapshot(), "you": name,
                        "isHost": msg.get("key") == host_key,
                    }))
                    await room.broadcast_presence()

                elif kind == "word" and name:
                    await room.submit(ws, name, str(msg.get("text", "")))

                elif kind in ("undo", "reset") and msg.get("key") == host_key:
                    await (room.undo() if kind == "undo" else room.reset())

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
    """Best guess at the address other machines can reach, without any traffic."""
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
                   help="Seconds a person must wait between words. 0 disables it.")
    p.add_argument("--audit", action="store_true",
                   help="Second-opinion pass via ollama. Slow, imperfect, optional.")
    p.add_argument("--host-key", default="host",
                   help="Secret that unlocks undo and reset. Append ?key=... to the URL.")
    args = p.parse_args()

    room = Room(cooldown=args.cooldown, use_audit=args.audit)
    app = make_app(room, args.host_key)

    ip = lan_ip()
    print()
    print("  Chaos Draft")
    print(f"  {len(room.filter.exact)} blocked terms, {len(room.filter.contains)} roots")
    print()
    print(f"  Everyone opens:  http://{ip}:{args.port}")
    print(f"  You open:        http://{ip}:{args.port}/?key={args.host_key}")
    print()
    print(f"  Cooldown: {args.cooldown}s   Audit: {'on' if args.audit else 'off'}")
    print("  Add words to wordlist.txt mid-session and they take effect immediately.")
    print()

    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
