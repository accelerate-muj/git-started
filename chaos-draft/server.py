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
import os
import re
import secrets
import socket
from contextlib import suppress
from pathlib import Path

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
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
        self.credits: list[dict] = []      # who added what, newest last
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
            "cursors": self.cursors,
            "credits": self.credits[-60:],
        }

    async def broadcast_presence(self) -> None:
        await self.broadcast({"type": "presence",
                              "users": sorted(set(self.clients.values()))})

    # -- editing ------------------------------------------------------------

    async def edit(self, ws: WebSocket, name: str, raw_op: dict, base: int,
                   cursor: int | None = None) -> None:
        """
        Apply one edit, but only after checking what it adds.

        The check happens BEFORE the edit is applied or broadcast, so a blocked
        word never reaches the shared page and nobody else ever sees it. The
        person who typed it is told, and removes it from their own screen.

        The previous order was the other way round: broadcast, then scan, then
        delete. That put the word on everybody's screen, and on the projector,
        for the length of a round trip before it vanished. Which is precisely
        the thing this is supposed to prevent.
        """
        async with self.lock:
            base = max(0, min(base, self.version))
            op = Op.from_json(raw_op)

            if len(self.doc) + op.shift > MAX_DOC:
                await self.send(ws, {"type": "full"})
                return

            # Adjust for everything that landed since this client last heard.
            op = transform_against(op, self.history[base:])

            # What the page WOULD look like. Nothing is committed yet.
            would_be = apply_op(self.doc, op)
            blocked = self._blocked_in(would_be, op)

            if blocked:
                # Refused. The page is untouched and no one else is told.
                self.blocked_count += len(blocked)
                await self.send(ws, {"type": "refused", "words": blocked,
                                     "version": self.version, "text": self.doc})
                await self.broadcast({"type": "blocked_count",
                                      "blocked": self.blocked_count})
                for host in list(self.hosts):
                    await self.send(host, {"type": "caught", "words": blocked,
                                           "author": name, "micros": 1})
                return

            self.doc = would_be
            self.history.append(op)
            self.version += 1

        # Who wrote what. Shown in the sidebar, which is the point: a name next
        # to every contribution is a far better deterrent than any filter.
        added = op.i.strip()
        if added:
            async with self.lock:
                if self.credits and self.credits[-1]["who"] == name and                         len(self.credits[-1]["text"]) < 120:
                    self.credits[-1]["text"] += " " + added
                else:
                    self.credits.append({"who": name, "text": added})
                self.credits = self.credits[-200:]
                entry = dict(self.credits[-1])

        await self.broadcast({"type": "op", "op": op.to_json(),
                              "version": self.version, "by": name,
                              "len": len(self.doc)})
        if added:
            await self.broadcast({"type": "credit", "credit": entry})

        if len(self.history) > MAX_HISTORY:
            await self.resync_all()

    def _blocked_in(self, candidate: str, op: Op) -> list[str]:
        """
        Anything blocked that this edit would ADD, and nothing else.

        Only the region the edit touches is examined, widened a little so a
        phrase spanning the join is caught. Text elsewhere on the page is
        somebody else's business and is left alone.
        """
        self.dictionary.reload_if_changed()

        start = max(0, op.p - self.PHRASE_WINDOW)
        end = min(len(candidate), op.p + len(op.i) + 1)
        window = candidate[start:end]
        if not window.strip():
            return []

        hits = []
        for s0, e0, _why in self.dictionary.scan(window):
            a, b = s0 + start, e0 + start
            # Only complain about something the edit actually completed: it has
            # to overlap what was inserted, and be finished rather than mid-word.
            touches_edit = a < op.p + len(op.i) and b > op.p - 1
            after = candidate[b] if b < len(candidate) else " "
            finished = not (after.isalnum() or after in "'-")
            if touches_edit and finished:
                hits.append(candidate[a:b])
        return hits

    # How far back to look for a phrase ending at the boundary. Long enough for
    # the longest multi-word entry, short enough to never reach other people.
    PHRASE_WINDOW = 80

    def _check_completed(self, op: Op) -> tuple[list[Op], list[str], int]:
        """
        Check only the word that this edit just finished.

        An edit finishes a word when it inserts something that is not part of one:
        a space, a newline, or punctuation. The word being finished is whatever
        sits immediately before that character, so only a small window ending at
        the insert position is examined.

        A paste can finish several words at once, so the pasted range is examined
        too. Nothing outside that window is ever touched, which is what stops one
        person's typing from disturbing anybody else's.
        """
        if not op.i or all(ch.isalnum() or ch in "'-" for ch in op.i):
            return [], [], 0          # still inside a word, nothing finished

        self.dictionary.reload_if_changed()

        # The window runs from a little before the edit to the end of what was
        # inserted, so a pasted sentence is covered as well as a typed space.
        start = max(0, op.p - self.PHRASE_WINDOW)
        end = min(len(self.doc), op.p + len(op.i))
        window = self.doc[start:end]
        if not window.strip():
            return [], [], 0

        spans = [(s0 + start, e0 + start, why)
                 for s0, e0, why in self.dictionary.scan(window)]

        # Keep only what is genuinely finished: the span must be followed by a
        # non-word character in the document, which is exactly the boundary that
        # was just typed.
        finished = []
        for s0, e0, why in spans:
            after = self.doc[e0] if e0 < len(self.doc) else " "
            if not (after.isalnum() or after in "'-"):
                finished.append((s0, e0, why))
        if not finished:
            return [], [], 0

        ops: list[Op] = []
        words: list[str] = []
        for s0, e0, why in reversed(finished):
            words.append(self.doc[s0:e0])
            cut = Op(p=s0, d=e0 - s0, i="")
            self.doc = apply_op(self.doc, cut)
            self.history.append(cut)
            self.version += 1
            ops.append(cut)

        # Tidy the double space left behind, but only right where we cut.
        for m in reversed(list(re.finditer(r"[ 	]{2,}", self.doc[start:end + 4]))):
            cut = Op(p=start + m.start(), d=m.end() - m.start(), i=" ")
            self.doc = apply_op(self.doc, cut)
            self.history.append(cut)
            self.version += 1
            ops.append(cut)

        words.reverse()
        return ops, words, 1

    def _scrub(self, cursor: int | None = None) -> tuple[list[Op], list[str], int]:
        """
        Delete anything blocked from the document.

        Runs inside the lock, straight after an edit lands. Returns the delete
        operations it made so they can be broadcast like any other edit.
        Right to left, so earlier offsets stay valid as later ones are removed.

        `cursor` is where the person who just typed has their caret. The word it
        sits in is left alone, because it is half-written. Otherwise the filter
        judges every prefix and eats ordinary words partway through: "assignment"
        disappears at "ass", "analysis" at "anal". It is checked as soon as they
        move off it, and a settle pass with no cursor catches anything left when
        they stop typing.
        """
        self.dictionary.reload_if_changed()
        spans = self.dictionary.scan(self.doc, typing_at=cursor)
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

    async def settle(self, ws: WebSocket, name: str) -> None:
        """Re-scan with nothing protected, once somebody stops typing."""
        async with self.lock:
            removals, words, micros = self._scrub(None)
        for op in removals:
            await self.broadcast({"type": "op", "op": op.to_json(),
                                  "version": self.version, "by": "filter",
                                  "len": len(self.doc), "filtered": True})
        if words:
            self.blocked_count += len(words)
            await self.send(ws, {"type": "scrubbed", "removed": words,
                                 "micros": micros})
            await self.broadcast({"type": "blocked_count",
                                  "blocked": self.blocked_count})
            for host in list(self.hosts):
                await self.send(host, {"type": "caught", "words": words,
                                       "author": name, "micros": micros})

    async def move_caret(self, name: str, at) -> None:
        """Tell everyone where this person is working."""
        if at is None:
            self.cursors.pop(name, None)
        else:
            self.cursors[name] = max(0, min(int(at), len(self.doc)))
        await self.broadcast({"type": "carets", "cursors": self.cursors})

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
            self.credits.clear()
            self.cursors.clear()
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


def make_app(room: Room, host_key: str, port: int,
             fixed_ip: str | None = None) -> FastAPI:
    app = FastAPI(title="Chaos Draft")

    def current_join_url(request: Request | None = None) -> str:
        """
        The URL to put on the QR, worked out fresh on every request.

        Taken from the Host header of the request that asked for it, which means
        the QR is correct wherever this happens to be running: on a laptop over
        wifi, behind a tunnel, or on a hosting provider. No configuration and
        nothing to keep in sync.

        Falls back to this machine's LAN address when there is no request to read,
        which is the case for the QR printed in the terminal at startup.

        An earlier version built the URL once at startup from the LAN address. It
        kept pointing at the old network after switching to a hotspot, and the
        failure was silent: firewall fine, server fine, nothing connects.
        """
        if fixed_ip:
            return f"http://{fixed_ip}:{port}"
        if request is not None:
            host = request.headers.get("host")
            if host and not host.startswith(("localhost", "127.")):
                # A proxy in front of us knows whether the client used HTTPS.
                proto = request.headers.get("x-forwarded-proto", request.url.scheme)
                return f"{proto}://{host}"
        return f"http://{lan_ip()}:{port}"

    @app.get("/")
    async def index():
        return FileResponse(HERE / "static" / "index.html")

    @app.get("/story.txt", response_class=PlainTextResponse)
    async def story():
        return room.doc

    @app.get("/join-url", response_class=PlainTextResponse)
    async def join(request: Request):
        return current_join_url(request)

    @app.get("/qr.svg")
    async def qr(request: Request):
        try:
            return Response(qr_svg(current_join_url(request)),
                            media_type="image/svg+xml",
                            headers={"Cache-Control": "no-store"})
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
                    raw_cursor = msg.get("cursor")
                    await room.edit(ws, name, msg.get("op", {}),
                                    int(msg.get("base", 0)),
                                    None if raw_cursor is None else int(raw_cursor))
                elif kind == "settle":
                    # Typing stopped. Re-check with no word protected, so a word
                    # left half-typed and then abandoned is still caught.
                    await room.settle(ws, name)
                elif kind == "sync":
                    await room.send(ws, room.snapshot())
                elif kind == "caret":
                    await room.move_caret(name, msg.get("at"))

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
                still_here = name in room.clients.values()
                if not still_here:
                    room.cursors.pop(name, None)
                    await room.broadcast({"type": "carets",
                                          "cursors": room.cursors})
                await room.broadcast_presence()

    return app


def lan_ip() -> str:
    """
    The address other devices on this network can reach.

    Asks the OS which interface it would use to leave the machine, which is the
    one a phone on the same wifi or hotspot will be able to see. No traffic is
    actually sent; connecting a UDP socket only sets up the route.

    The target has to be a public address. An earlier version aimed at
    10.255.255.255, which on a campus 10.x network resolves to the campus
    interface even when a hotspot is also connected, so it kept reporting the
    wrong one.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"
    finally:
        s.close()


def all_ipv4() -> list[str]:
    """Every address this machine has, so the host can pick if the guess is wrong."""
    found = []
    with suppress(Exception):
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            addr = info[4][0]
            if addr not in found and not addr.startswith(("127.", "169.254.")):
                found.append(addr)
    primary = lan_ip()
    if primary in found:
        found.remove(primary)
    return [primary] + found


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

    # On a hosting provider the filesystem is ephemeral: the container is rebuilt
    # on every deploy, and free instances are torn down when they sleep. A key
    # saved to disk there is regenerated each time, so the host link you wrote
    # down silently stops working. An environment variable survives all of that.
    from_env = os.environ.get("CHAOS_HOST_KEY", "").strip()
    if from_env:
        return from_env, "from CHAOS_HOST_KEY"

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
    p.add_argument("--port", type=int,
                   default=int(os.environ.get("PORT", 8000)),
                   help="Defaults to $PORT when hosted, else 8000.")
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
    app = make_app(room, host_key, args.port, args.ip)

    d = room.dictionary
    print()
    print("  Chaos Draft")
    print(f"  dictionary: {len(d.exact)} terms, {len(d.contains)} roots, "
          f"{len(d.phrases)} phrases, {len(d.allow)} protected")
    print()
    with suppress(Exception):
        print(qr_ascii(join_url))
        print()
    others = [a for a in all_ipv4()[1:]]
    print(f"  Everyone scans that, or opens:  {join_url}")
    if others:
        print(f"  Other addresses on this machine: {', '.join(others)}")
        print(f"  If the QR does not work, try one of those with --ip")
    print(f"  Your host link:                 {join_url}/?key={host_key}")
    print(f"                                  ^ yours only, {key_origin}.")
    print("                                  Do not put it on the projector.")
    print()
    print("  The join QR is on the page too, under the QR button. It is rebuilt")
    print("  on every open, so if you switch to a hotspot just reopen it.")
    print("  Edit wordlist.txt during the session and it applies immediately.")
    print()

    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
