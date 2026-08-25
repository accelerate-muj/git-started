"""
Chaos Draft: one document, everybody typing into it at once.

Run it on the machine that will act as the server:

    python server.py

It prints a LAN address and a QR code. Everyone on the same wifi or hotspot scans
it, types a name, and starts writing into the same document. There is no turn
order and no ownership. It is a shared page and everyone has a pen.

    python server.py --port 8080
    python server.py --new-key        rotate the host link if it leaks
    python server.py --ip 10.0.0.5    if the address is guessed wrong

HOW IT WORKS
------------
One string on the server, and operational transform to keep everyone agreed on
it. See ot.py. Each client sends the edit it just made against the version it
last saw; the server adjusts it for anything that landed in the meantime, applies
it, and tells everyone. Clients that drift ask for the document again.

FILTERING
---------
After every edit the document is scanned and anything blocked is deleted from it,
as an ordinary operation that everyone receives. So a slur disappears mid-sentence
as you finish typing it, for you and for the room at the same instant.

The scan covers phrases as well as words, because some abuse is innocent word by
word. "behen ke lode" is the reason: only the last word is blockable, and removing
just that leaves the rest of the phrase sitting there.

The person typing is told what was removed. Nobody else is, they only see the
counter move. The host sees everything, which is the only way to know the filter
is doing its job and the only way to spot one person repeatedly trying it on.
"""
from __future__ import annotations

import argparse
import asyncio
import io
import json
import re
import secrets
import socket
from contextlib import suppress
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, PlainTextResponse, Response

from filter import Dictionary
from ot import Op, apply_op, transform_against

HERE = Path(__file__).parent
KEY_FILE = HERE / ".host-key"
MAX_DOC = 60_000
MAX_NAME_LEN = 24
MAX_HISTORY = 4000


class Room:
    """One shared document, and everyone looking at it."""

    def __init__(self) -> None:
        self.doc = ""
        self.version = 0
        self.history: list[Op] = []
        self.clients: dict[WebSocket, str] = {}
        self.hosts: set[WebSocket] = set()
        self.cursors: dict[str, int] = {}
        self.blocked_count = 0
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
            self.hosts.discard(ws)

    def snapshot(self) -> dict:
        return {
            "type": "doc",
            "text": self.doc,
            "version": self.version,
            "users": sorted(set(self.clients.values())),
            "blocked": self.blocked_count,
        }

    async def broadcast_presence(self) -> None:
        await self.broadcast({"type": "presence",
                              "users": sorted(set(self.clients.values()))})

    # -- editing ------------------------------------------------------------

    async def edit(self, ws: WebSocket, name: str, raw_op: dict, base: int) -> None:
        async with self.lock:
            base = max(0, min(base, self.version))
            op = Op.from_json(raw_op)

            if len(self.doc) + op.shift > MAX_DOC:
                await self.send(ws, {"type": "full"})
                return

            # Adjust for everything that landed since this client last heard.
            op = transform_against(op, self.history[base:])
            self.doc = apply_op(self.doc, op)
            self.history.append(op)
            self.version += 1

            await self.broadcast({"type": "op", "op": op.to_json(),
                                  "version": self.version, "by": name,
                                  "len": len(self.doc)})

            removals, removed_words, micros = self._scrub()

        for op in removals:
            await self.broadcast({"type": "op", "op": op.to_json(),
                                  "version": self.version, "by": "filter",
                                  "len": len(self.doc), "filtered": True})

        if removed_words:
            self.blocked_count += len(removed_words)
            await self.send(ws, {"type": "scrubbed", "removed": removed_words,
                                 "micros": micros})
            await self.broadcast({"type": "blocked_count",
                                  "blocked": self.blocked_count})
            for host in list(self.hosts):
                await self.send(host, {"type": "caught", "words": removed_words,
                                       "author": name, "micros": micros})

        if len(self.history) > MAX_HISTORY:
            await self.resync_all()

    def _scrub(self) -> tuple[list[Op], list[str], int]:
        """
        Delete anything blocked from the document.

        Runs inside the lock, straight after an edit lands. Returns the delete
        operations it made so they can be broadcast like any other edit.
        Right to left, so earlier offsets stay valid as later ones are removed.
        """
        self.dictionary.reload_if_changed()
        spans = self.dictionary.scan(self.doc)
        if not spans:
            return [], [], 0

        ops: list[Op] = []
        words: list[str] = []
        micros = 0
        for start, end, why in reversed(spans):
            words.append(self.doc[start:end])
            micros += 1
            op = Op(p=start, d=end - start, i="")
            self.doc = apply_op(self.doc, op)
            self.history.append(op)
            self.version += 1
            ops.append(op)

        # Tidy the double space left where a word was cut out.
        for m in reversed(list(re.finditer(r"[ \t]{2,}", self.doc))):
            op = Op(p=m.start(), d=m.end() - m.start(), i=" ")
            self.doc = apply_op(self.doc, op)
            self.history.append(op)
            self.version += 1
            ops.append(op)

        words.reverse()
        return ops, words, micros

    async def resync_all(self) -> None:
        async with self.lock:
            self.history.clear()
            self.version = 0
        await self.broadcast(self.snapshot())

    # -- the host -----------------------------------------------------------

    async def reset(self) -> None:
        async with self.lock:
            self.doc = ""
            self.history.clear()
            self.version = 0
            self.blocked_count = 0
        await self.broadcast(self.snapshot())

    async def learn(self, term: str) -> bool:
        """Host teaches the dictionary a term, then it is scrubbed everywhere."""
        term = term.strip()
        if not term or len(term.split()) > 1:
            return False
        with suppress(Exception):
            self.dictionary.add(term)
        async with self.lock:
            removals, words, _ = self._scrub()
        for op in removals:
            await self.broadcast({"type": "op", "op": op.to_json(),
                                  "version": self.version, "by": "filter",
                                  "len": len(self.doc), "filtered": True})
        if words:
            self.blocked_count += len(words)
            await self.broadcast({"type": "blocked_count",
                                  "blocked": self.blocked_count})
        return True


def qr_svg(url: str) -> str:
    import qrcode
    import qrcode.image.svg
    img = qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage,
                      box_size=10, border=2)
    buf = io.BytesIO()
    img.save(buf)
    return buf.getvalue().decode("utf-8")


def qr_ascii(url: str) -> str:
    """A QR for the terminal, so a phone can be pointed at the laptop screen."""
    import qrcode
    q = qrcode.QRCode(border=1)
    q.add_data(url)
    q.make(fit=True)
    m = q.get_matrix()
    rows = []
    for y in range(0, len(m), 2):
        row = ""
        for x in range(len(m[0])):
            top = m[y][x]
            bottom = m[y + 1][x] if y + 1 < len(m) else False
            row += "█" if top and bottom else "▀" if top else "▄" if bottom else " "
        rows.append("  " + row)
    return "\n".join(rows)


def make_app(room: Room, host_key: str, join_url: str) -> FastAPI:
    app = FastAPI(title="Chaos Draft")

    @app.get("/")
    async def index():
        return FileResponse(HERE / "static" / "index.html")

    @app.get("/story.txt", response_class=PlainTextResponse)
    async def story():
        return room.doc

    @app.get("/join-url", response_class=PlainTextResponse)
    async def join():
        return join_url

    @app.get("/qr.svg")
    async def qr():
        try:
            return Response(qr_svg(join_url), media_type="image/svg+xml")
        except Exception:
            return Response("", media_type="image/svg+xml")

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

                elif not name:
                    continue

                elif kind == "op":
                    await room.edit(ws, name, msg.get("op", {}),
                                    int(msg.get("base", 0)))
                elif kind == "sync":
                    await room.send(ws, room.snapshot())

                elif is_host and kind == "reset":
                    await room.reset()
                elif is_host and kind == "learn":
                    ok = await room.learn(str(msg.get("term", "")))
                    await room.send(ws, {"type": "learned",
                                         "term": msg.get("term", ""), "ok": ok})

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


def lan_ip() -> str:
    """Best guess at the address other devices can reach, without sending traffic."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def host_key_for_run(explicit: str | None, rotate: bool) -> tuple[str, str]:
    """
    Work out the host key, and say where it came from.

      1. --host-key on the command line
      2. .host-key next to this file, so the URL survives a restart
      3. a fresh random one, saved for next time

    There is deliberately no fixed default. This repository is public, so any key
    written into the code or the README would be a key everybody in the room
    already has, and the host controls include wiping the document.
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
        with suppress(Exception):
            KEY_FILE.chmod(0o600)
        return key, f"new, saved to {KEY_FILE.name}"
    except OSError:
        return key, "new, could not be saved"


def main() -> None:
    p = argparse.ArgumentParser(description="Chaos Draft server")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--host-key",
                   help="Pin the host key yourself. Otherwise one is generated and "
                        "remembered in .host-key so your URL survives a restart.")
    p.add_argument("--new-key", action="store_true",
                   help="Throw away the saved key and generate a new one.")
    p.add_argument("--ip", help="Override the detected address, if it guesses wrong.")
    args = p.parse_args()

    room = Room()
    host_key, key_origin = host_key_for_run(args.host_key, args.new_key)
    ip = args.ip or lan_ip()
    join_url = f"http://{ip}:{args.port}"
    app = make_app(room, host_key, join_url)

    d = room.dictionary
    print()
    print("  Chaos Draft")
    print(f"  dictionary: {len(d.exact)} terms, {len(d.contains)} roots, "
          f"{len(d.phrases)} phrases, {len(d.allow)} protected")
    print()
    with suppress(Exception):
        print(qr_ascii(join_url))
        print()
    print(f"  Everyone scans that, or opens:  {join_url}")
    print(f"  Your host link:                 {join_url}/?key={host_key}")
    print(f"                                  ^ yours only, {key_origin}.")
    print("                                  Do not put it on the projector.")
    print()
    print("  The join QR is on the page too, under the QR button.")
    print("  Edit wordlist.txt during the session and it applies immediately.")
    print()

    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
