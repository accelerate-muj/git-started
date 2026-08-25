"""
Just enough operational transform for one shared plain-text document.

An edit is one operation: at position `p`, delete `d` characters, then insert the
string `i`. Every ordinary editing action reduces to that. Typing a letter is
(p, 0, "x"). Backspace is (p, 1, ""). Replacing a selection is (p, n, "text").
Pasting is (p, 0, "lots of text").

The problem this solves: two people edit at the same time, both against version 7.
The server applies one of them, so the other one's positions are now wrong. It has
to be adjusted to account for the edit that landed first. That adjustment is the
transform, and it is the whole of collaborative editing.

    Alice at position 10, Bob at position 3, Bob lands first inserting 5 chars.
    Alice's edit must move to position 15 or it lands in the wrong place.

The server is authoritative: it transforms every incoming operation against
everything that has happened since the client last heard from it, applies the
result, and tells everyone. Clients that fall out of step ask for the whole
document again, which is the safety net under all of this.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Op:
    p: int          # position
    d: int = 0      # characters to delete at p
    i: str = ""     # text to insert at p

    @property
    def shift(self) -> int:
        """How much this operation moves everything after it."""
        return len(self.i) - self.d

    @property
    def end(self) -> int:
        return self.p + self.d

    def to_json(self) -> dict:
        return {"p": self.p, "d": self.d, "i": self.i}

    @staticmethod
    def from_json(raw: dict) -> "Op":
        return Op(p=max(0, int(raw.get("p", 0))),
                  d=max(0, int(raw.get("d", 0))),
                  i=str(raw.get("i", "")))


def apply_op(text: str, op: Op) -> str:
    p = max(0, min(op.p, len(text)))
    d = max(0, min(op.d, len(text) - p))
    return text[:p] + op.i + text[p + d:]


def transform(a: Op, b: Op) -> Op:
    """
    Adjust `a` so it can be applied after `b`, when both were written against the
    same version of the document.

    The three easy cases are exact. The overlapping case, where two people edit
    the same characters at the same instant, cannot be resolved correctly by any
    rule: the intent is genuinely ambiguous. It is clamped to something safe and
    the client resyncs if the result diverges.
    """
    # b is entirely before a, so a slides by however much b changed the length.
    if b.end <= a.p:
        return Op(max(0, a.p + b.shift), a.d, a.i)

    # b is entirely after a, so a is unaffected.
    if b.p >= a.end and not (b.p == a.p and a.d == 0):
        return a

    # a is a pure insert inside or at the edge of b's deleted range: put it where
    # b's deletion started, since the surrounding text is gone.
    if a.d == 0:
        if b.p <= a.p <= b.end:
            return Op(min(a.p, b.p) + (len(b.i) if b.p < a.p else 0), 0, a.i)
        return Op(max(0, a.p + b.shift), 0, a.i)

    # Overlapping deletes. Keep whatever part of a's range b did not already
    # remove, and never let the range run past what is left.
    start = min(a.p, b.p) if b.p < a.p else a.p
    overlap = max(0, min(a.end, b.end) - max(a.p, b.p))
    return Op(max(0, start if b.p >= a.p else b.p + len(b.i)),
              max(0, a.d - overlap), a.i)


def transform_against(op: Op, history: list[Op]) -> Op:
    for prior in history:
        op = transform(op, prior)
    return op


def diff(old: str, new: str) -> Op | None:
    """
    Turn "the text was this, now it is that" into one operation.

    Finds the common prefix and suffix and treats everything between them as the
    change. That is exactly right for typing, backspace, selection replacement
    and paste, which is everything a person does in a textarea.
    """
    if old == new:
        return None

    start = 0
    limit = min(len(old), len(new))
    while start < limit and old[start] == new[start]:
        start += 1

    end_old, end_new = len(old), len(new)
    while end_old > start and end_new > start and old[end_old - 1] == new[end_new - 1]:
        end_old -= 1
        end_new -= 1

    return Op(p=start, d=end_old - start, i=new[start:end_new])
