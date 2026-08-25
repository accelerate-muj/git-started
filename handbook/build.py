#!/usr/bin/env python3
"""
Build every phase of the Rabbit Holes handbook.

    python build.py            build all phases
    python build.py 5 7        build only phases 5 and 7
    python build.py --clean    remove build artefacts

Needs xelatex on PATH, or set XELATEX to point at it:

    XELATEX="C:/Apps/MikTex/miktex/bin/x64/xelatex" python build.py

Each phase is compiled twice, because the table of contents needs a first pass
to learn the page numbers and a second to typeset them.
"""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).parent / "src"
# Built into docs/, so GitHub Pages serves them at a real URL and the
# split-screen handbook can link straight to a phase.
OUT = Path(__file__).parent.parent / "docs" / "handbook"
JUNK = (".aux", ".log", ".out", ".toc", ".synctex.gz", ".fls", ".fdb_latexmk")


def find_xelatex() -> str:
    if os.environ.get("XELATEX"):
        return os.environ["XELATEX"]
    found = shutil.which("xelatex")
    if found:
        return found
    # MiKTeX and TeX Live in their usual places
    for guess in (
        r"C:/Apps/MikTex/miktex/bin/x64/xelatex.exe",
        r"C:/Program Files/MiKTeX/miktex/bin/x64/xelatex.exe",
        r"C:/texlive/2025/bin/windows/xelatex.exe",
        "/usr/bin/xelatex",
        "/Library/TeX/texbin/xelatex",
    ):
        if Path(guess).exists():
            return guess
    sys.exit(
        "Could not find xelatex.\n"
        "Install a TeX distribution (MiKTeX, TeX Live or MacTeX), or set the\n"
        "XELATEX environment variable to its full path."
    )


def clean() -> None:
    removed = 0
    for f in SRC.iterdir():
        if f.suffix in JUNK or f.name.endswith(".synctex.gz"):
            f.unlink()
            removed += 1
    print(f"Removed {removed} build artefacts.")


def phase_files(wanted: list[str]) -> list[Path]:
    files = sorted(SRC.glob("phase-*.tex"))
    if not wanted:
        return files
    keep = []
    for f in files:
        m = re.match(r"phase-0*(\d+)", f.stem)
        if m and m.group(1) in {w.lstrip("0") for w in wanted}:
            keep.append(f)
    return keep


def build(tex: Path, xelatex: str) -> bool:
    """Compile one phase. Returns True on success."""
    for pass_no in (1, 2):
        proc = subprocess.run(
            [xelatex, "-interaction=nonstopmode", "-halt-on-error", tex.name],
            cwd=SRC,
            capture_output=True,
            text=True,
            errors="replace",
        )
        if proc.returncode != 0:
            print(f"  FAILED on pass {pass_no}")
            # Surface the actual TeX errors, which are the lines starting "!"
            for line in proc.stdout.splitlines():
                if line.startswith("!") or "Error" in line:
                    print(f"    {line}")
            return False

    pdf = tex.with_suffix(".pdf")
    if not pdf.exists():
        print("  FAILED: no PDF produced")
        return False

    OUT.mkdir(parents=True, exist_ok=True)
    dest = OUT / pdf.name
    shutil.move(str(pdf), str(dest))

    pages = "?"
    log = tex.with_suffix(".log")
    if log.exists():
        m = re.search(r"Output written on .*?\((\d+) pages?", log.read_text(errors="replace"))
        if m:
            pages = m.group(1)
    size = dest.stat().st_size / 1024
    print(f"  OK  {pages} pages, {size:.0f} KB  ->  docs/handbook/{dest.name}")
    return True


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--clean"]
    if "--clean" in sys.argv:
        clean()
        if not args:
            return

    xelatex = find_xelatex()
    files = phase_files(args)
    if not files:
        sys.exit("No matching phase files in src/.")

    print(f"xelatex: {xelatex}")
    print(f"Building {len(files)} phase(s)\n")

    failed = []
    for tex in files:
        print(f"{tex.name}")
        if not build(tex, xelatex):
            failed.append(tex.name)

    clean()
    print()
    if failed:
        print(f"{len(failed)} failed: {', '.join(failed)}")
        sys.exit(1)
    print(f"All {len(files)} phase(s) built into {OUT}/")


if __name__ == "__main__":
    main()
