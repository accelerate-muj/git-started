"""
Chaos Draft: a shared document that thirty people write at the same time.

Run it on the machine that will act as the server:

    python server.py

It prints a LAN address and a QR code. Everyone on the same wifi or hotspot scans
it, types a name, and starts writing. There is no turn order, which is the point.

    python server.py --port 8080
    python server.py --new-key        rotate the host link if it leaks

HOW THE DOCUMENT WORKS
----------------------
The story is a list of lines. Everyone owns the lines they created and types into
them freely: whole sentences, backspace, edit what you wrote a minute ago. You see
everybody else's lines appearing and changing live.

Lines are owned rather than shared because thirty people typing into one string
means thirty people deleting each other's characters. Per-line ownership gives
normal typing with no clobbering, and the document still fills up chaotically,
which is the part we actually wanted.

FILTERING
---------
Every edit is sanitised server-side before anyone else sees it. Each word is
checked against the dictionary in filter.py, which answers in microseconds, and
anything blocked is removed from the text before it is stored or broadcast.

A word is only complete once you stop typing it, so abuse disappears as you finish
the word. The person typing is told what was removed. Nobody else sees it, they
just see the counter move. The host sees everything, which is the only way to know
the filter is working, and the only way to spot one person repeatedly trying it on.
"""
from __future__ import annotations

import argparse
import asyncio
import io
import json
import re
import secrets
import socket
import time
from contextlib import suppress
from dataclasses import dataclass, field, asdict
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, PlainTextResponse, Response

from filter import Decision, Dictionary

HERE = Path(__file__).parent
KEY_FILE = HERE / ".host-key"
MAX_LINE_LEN = 600
MAX_NAME_LEN = 24
MAX_LINES = 400

# Split on whitespace but keep it, so the text can be rebuilt exactly minus the
# words that were removed.
TOKENS = re.compile(r"(\s+)")


@dataclass
class Line:
    id: int
    author: str
    text: str = ""
    ts: float = field(default_factory=time.time)


class Room:
    """All the state. One room, which is all a single workshop needs."""

    def __init__(self) -> None:
        self.lines: list[Line] = []
        self.next_id = 1
        self.clients: dict[WebSocket, str] = {}
        self.hosts: set[WebSocket] = set()
        self.blocked_count = 0
        self.dictionary = Dictionary()
        self.lock = asyncio.Lock()

    # -- sending ------------------------------------------------------------

    async def send(self, ws: WebSocket, payload: dict) -> None:
        with suppress(Exception):
            await ws.send_text(json.dumps(payload))

    async def broadcast(self, payload: dict, skip: WebSocket | None = None) -> None:
        message = json.dumps(payload)
        dead = []
        for ws in list(self.clients):
            if ws is skip:
                continue
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.clients.pop(ws, None)
            self.hosts.discard(ws)

    def snapshot(self) -> dict:
        return {
            "type": "state",
            "lines": [asdict(l) for l in self.lines],
            "users": sorted(set(self.clients.values())),
            "blocked": self.blocked_count,
        }

    async def broadcast_presence(self) -> None:
        await self.broadcast({"type": "presence",
                              "users": sorted(set(self.clients.values()))})

    # -- filtering ----------------------------------------------------------

    def sanitise(self, text: str) -> tuple[str, list[str], int]:
        """
        Remove any blocked word from a line, keeping everything else exactly.

        Returns the clean text, the words taken out, and how long the checking
        took in microseconds.
        """
        self.dictionary.reload_if_changed()

        kept: list[str] = []
        removed: list[str] = []
        micros = 0

        for token in TOKENS.split(text):
            if not token.strip():
                kept.append(token)
                continue
            verdict = self.dictionary.check(token)
            micros += verdict.micros
            # Anything the dictionary is not happy with comes out. A near match
            # is treated as a match: underlining a slur is not filtering it.
            if verdict.decision is Decision.ALLOW:
                kept.append(token)
            else:
                removed.append(token)

        clean = "".join(kept)
        # Collapse the double spaces left where a word was removed.
        clean = re.sub(r"[ \t]{2,}", " ", clean)
        return clean, removed, micros

    # -- editing ------------------------------------------------------------

    async def edit(self, ws: WebSocket, name: str, line_id: int, raw: str) -> None:
        text = raw[:MAX_LINE_LEN]

        async with self.lock:
            line = next((l for l in self.lines if l.id == line_id), None)
            if line is None or line.author != name:
                return                      # not yours, or gone

        clean, removed, micros = self.sanitise(text)

        async with self.lock:
            line.text = clean

        # Everyone else sees the clean version. The author is only sent an update
        # if something was taken out, otherwise the echo fights their cursor.
        await self.broadcast({"type": "line", "line": asdict(line)}, skip=ws)

        if removed:
            self.blocked_count += len(removed)
            await self.send(ws, {"type": "scrubbed", "id": line.id, "text": clean,
                                 "removed": removed, "micros": micros})
            await self.broadcast({"type": "blocked_count",
                                  "blocked": self.blocked_count})
            for host in list(self.hosts):
                await self.send(host, {"type": "caught", "words": removed,
                                       "author": name, "micros": micros})

    async def new_line(self, ws: WebSocket, name: str) -> None:
        async with self.lock:
            if len(self.lines) >= MAX_LINES:
                return
            line = Line(id=self.next_id, author=name)
            self.next_id += 1
            self.lines.append(line)
        await self.broadcast({"type": "line", "line": asdict(line)})
        await self.send(ws, {"type": "yours", "id": line.id})

    # -- the host -----------------------------------------------------------

    async def remove_line(self, line_id: int, learn: bool) -> None:
        async with self.lock:
            line = next((l for l in self.lines if l.id == line_id), None)
            if line is None:
                return
            text = line.text
            self.lines = [l for l in self.lines if l.id != line_id]

        if learn and text.strip():
            # Only teach it single words. Learning a whole sentence would put a
            # phrase in the dictionary that never matches anything again.
            words = [w for w in text.split() if w.strip()]
            if len(words) == 1:
                with suppress(Exception):
                    self.dictionary.add(words[0])

        await self.broadcast({"type": "removed", "id": line_id})

    async def reset(self) -> None:
        async with self.lock:
            self.lines.clear()
            self.blocked_count = 0
        await self.broadcast(self.snapshot())

    def as_text(self) -> str:
        return "\n".join(l.text for l in self.lines if l.text.strip())


def qr_svg(url: str) -> str:
    """A QR for the join URL, as inline SVG so the page needs no image files."""
    import qrcode
    import qrcode.image.svg

    img = qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage,
                      box_size=10, border=2)
    buf = io.BytesIO()
    img.save(buf)
    return buf.getvalue().decode("utf-8")


def qr_ascii(url: str) -> str:
    """A QR for the terminal, so you can point a phone at the laptop screen."""
    import qrcode

    q = qrcode.QRCode(border=1)
    q.add_data(url)
    q.make(fit=True)
    m = q.get_matrix()
    out = []
    # Two rows per line using half-block characters, so it fits in a terminal.
    for y in range(0, len(m), 2):
        row = ""
        for x in range(len(m[0])):
            top = m[y][x]
            bottom = m[y + 1][x] if y + 1 < len(m) else False
            row += "█" if top and bottom else "▀" if top else "▄" if bottom else " "
        out.append(row)
    return "\n".join(out)


def make_app(room: Room, host_key: str, join_url: str) -> FastAPI:
    app = FastAPI(title="Chaos Draft")

    @app.get("/")
    async def index():
        return FileResponse(HERE / "static" / "index.html")

    @app.get("/story.txt", response_class=PlainTextResponse)
    async def story():
        return room.as_text()

    @app.get("/qr.svg")
    async def qr():
        try:
            return Response(qr_svg(join_url), media_type="image/svg+xml")
        except Exception:
            return Response("", media_type="image/svg+xml")

    @app.get("/join-url", response_class=PlainTextResponse)
    async def join():
        return join_url

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

                elif kind == "edit":
                    await room.edit(ws, name, int(msg.get("id", -1)),
                                    str(msg.get("text", "")))
                elif kind == "newline":
                    await room.new_line(ws, name)

                elif is_host and kind == "remove":
                    await room.remove_line(int(msg.get("id", -1)),
                                           learn=bool(msg.get("learn", True)))
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
    already has, and the host controls include wiping the story.
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
          f"{len(d.allow)} protected")
    print()
    try:
        print(qr_ascii(join_url))
        print()
    except Exception:
        pass
    print(f"  Everyone scans that, or opens:  {join_url}")
    print(f"  Your host link:                 {join_url}/?key={host_key}")
    print(f"                                  ^ yours only, {key_origin}.")
    print("                                  Do not put it on the projector.")
    print()
    print("  The join QR is also on the page itself, under the QR button.")
    print("  Edit wordlist.txt during the session and it applies immediately.")
    print()

    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
