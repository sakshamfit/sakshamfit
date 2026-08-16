#!/usr/bin/env python3
"""
make_info_card.py — hand-authored neofetch-style info card SVG.

    python scripts/make_info_card.py            # writes info-card.svg
    STATIC=1 python scripts/make_info_card.py   # frozen frame for Quick Look

Keep the *story* here, not the stats - the contribution graph already covers
commits and streaks. This panel is for what numbers can't tell.

>>> EDIT THE `ROWS` LIST BELOW. That's the whole config. <<<
"""
from __future__ import annotations

import html
import os

OUT = "info-card.svg"
STATIC = os.environ.get("STATIC") == "1"

USER = "sakshamfit"   # shown as user@host in the card header
HOST = "github"

# (key, value) — an empty key renders a continuation line, None renders a rule
ROWS: list[tuple[str | None, str]] = [
    ("OS", "Anshuman Pandey · India"),
    ("Uptime", "building since Jun 2025"),
    (None, ""),
    ("Now", "Founder @ NEARconnect"),
    ("", "hyperlocal social + discovery"),
    ("Shipping", "FRINKELs — Flutter app, clean"),
    ("", "architecture, Supabase + Firebase"),
    (None, ""),
    ("Langs", "Dart · TypeScript · JavaScript"),
    ("", "Python · HTML/CSS"),
    ("Stack", "Flutter · React · Next.js · Node"),
    ("Data", "Supabase · Firebase · Postgres"),
    ("Tools", "Git · GitHub Actions · Figma"),
    (None, ""),
    ("Focus", "Clean architecture, dark UI,"),
    ("", "shipping over polishing"),
    ("Learning", "System design · DevOps"),
    (None, ""),
    ("Web", "sakshamfit.netlify.app"),
    ("Contact", "github.com/sakshamfit"),
]

# palette
BG = "#0d1117"
BORDER = "#21262d"
KEY = "#39d353"
VAL = "#c9d1d9"
DIM = "#6e7681"
ACCENT = "#58a6ff"
RED, YEL, GRN = "#ff5f56", "#ffbd2e", "#27c93f"

FONT = "'SFMono-Regular',Consolas,'Liberation Mono',Menlo,monospace"
FS = 13
LH = 21
PAD = 20
W = 520
TITLE_H = 34
KEY_W = 78

STEP = 0.09     # per-line stagger
DUR = 0.45


def esc(s: str) -> str:
    return html.escape(s)


def build() -> str:
    body_lines = 2 + len(ROWS) + 2  # header + rows + swatches
    h = TITLE_H + PAD + body_lines * LH + PAD + 14

    p: list[str] = []
    p.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" '
        f'viewBox="0 0 {W} {h}" role="img" aria-label="{USER} info card">'
    )
    p.append(
        "<style>"
        f"text{{font-family:{FONT};font-size:{FS}px;white-space:pre}}"
        ".t{font-size:12px}"
        + (
            ""
            if STATIC
            else ".ln{opacity:0;animation:in .45s ease-out forwards}"
            "@keyframes in{from{opacity:0;transform:translateX(-8px)}"
            "to{opacity:1;transform:translateX(0)}}"
        )
        + "</style>"
    )

    # frame + title bar
    p.append(
        f'<rect x="0.5" y="0.5" width="{W-1}" height="{h-1}" rx="10" '
        f'fill="{BG}" stroke="{BORDER}"/>'
    )
    p.append(
        f'<path d="M0.5 10.5a10 10 0 0 1 10-10h{W-21}a10 10 0 0 1 10 10v{TITLE_H-10}H0.5z" '
        f'fill="#161b22" stroke="{BORDER}"/>'
    )
    for i, c in enumerate((RED, YEL, GRN)):
        p.append(f'<circle cx="{20+i*17}" cy="{TITLE_H/2}" r="5.5" fill="{c}"/>')
    p.append(
        f'<text class="t" x="{W/2}" y="{TITLE_H/2+4}" text-anchor="middle" '
        f'fill="{DIM}">— {esc(USER)}@{esc(HOST)}: ~ —</text>'
    )

    y = TITLE_H + PAD + LH
    n = 0

    def line(content: str) -> None:
        nonlocal y, n
        style = "" if STATIC else f' class="ln" style="animation-delay:{n*STEP:.2f}s"'
        p.append(f"<g{style}>{content}</g>")
        y += LH
        n += 1

    # neofetch header: user@host + underline
    line(
        f'<text x="{PAD}" y="{y}" fill="{KEY}" font-weight="bold">{esc(USER)}'
        f'<tspan fill="{VAL}">@</tspan>'
        f'<tspan fill="{ACCENT}" font-weight="bold">{esc(HOST)}</tspan></text>'
    )
    line(f'<text x="{PAD}" y="{y}" fill="{DIM}">{"-" * 34}</text>')

    for key, val in ROWS:
        if key is None:
            y += 4
            continue
        if key == "":
            line(
                f'<text x="{PAD+KEY_W}" y="{y}" fill="{VAL}">{esc(val)}</text>'
            )
        else:
            line(
                f'<text x="{PAD}" y="{y}" fill="{KEY}" font-weight="bold">{esc(key)}</text>'
                f'<text x="{PAD+KEY_W}" y="{y}" fill="{VAL}">{esc(val)}</text>'
            )

    # neofetch colour swatches
    y += 6
    sw = []
    for i, c in enumerate(
        ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353", "#69f0a0",
         "#58a6ff", "#bc8cff"]
    ):
        sw.append(
            f'<rect x="{PAD+i*26}" y="{y-11}" width="22" height="12" rx="2" fill="{c}"/>'
        )
    line("".join(sw))

    p.append("</svg>")
    return "".join(p)


if __name__ == "__main__":
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(build())
    print(f"wrote {OUT}  (static={STATIC})")
