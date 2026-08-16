#!/usr/bin/env python3
"""
make_ascii_svg.py — convert source-prepped.png into a self-typing,
monochrome ASCII-portrait SVG.

    python scripts/make_ascii_svg.py        # writes saksham-ascii.svg
    STATIC=1 python scripts/make_ascii_svg.py   # frozen frame, no animation

Design rules that keep it looking clean instead of noisy:
  * ONE fill color. Per-character rainbow coloring is what makes most ASCII
    portraits read as static.
  * The ramp starts with a space, so bright pixels clear to nothing and only
    the subject prints.
  * Each row is wrapped in a horizontal clip that wipes left-to-right, with a
    block cursor riding the wipe edge, staggered top to bottom. It prints
    ONCE and freezes - no looping.
"""
from __future__ import annotations

import html
import os
from pathlib import Path

import numpy as np
from PIL import Image

SRC = Path("source-prepped.png")
MASK = Path("source-mask.png")
OUT = Path("saksham-ascii.svg")

COLS = 100
ROWS = 0   # 0 = derive from the photo's aspect ratio (chars are ~2x tall)

RAMP = " .`:-=+*cs#%@"  # bright (sparse) -> dark (dense)

# tone controls - tweak these if your photo comes out too dark or too washed
GAMMA = float(os.environ.get("GAMMA", "1.25"))  # <1 lightens, >1 darkens

CH_W = 6.2            # character advance for the mono font at FONT_PX
CH_H = 11.0
FONT_PX = 10.5
PAD = 14

INK = "#c9d1d9"       # single light-gray fill
CURSOR = "#39d353"
BG = "#0d1117"

ROW_DUR = 0.42        # how long one row takes to wipe in
ROW_STEP = 0.055      # stagger between consecutive rows
STATIC = os.environ.get("STATIC") == "1"


def load_grid() -> list[str]:
    global ROWS
    if not SRC.exists():
        raise SystemExit(f"missing {SRC} - run: python scripts/prep_photo.py <photo>")

    img = Image.open(SRC).convert("L")

    # a character cell is ~2x taller than it is wide, so the row count has to
    # be scaled by CH_W/CH_H or the portrait comes out stretched
    if not ROWS:
        ROWS = max(12, round(COLS * (img.height / img.width) * (CH_W / CH_H)))

    img = img.resize((COLS, ROWS), Image.LANCZOS)
    arr = np.asarray(img, dtype=np.float32) / 255.0

    # Auto-levels on the SUBJECT only. The background is pure white and would
    # otherwise dominate the histogram, leaving the face crushed into two or
    # three glyphs. Stretch the subject's real tonal range across the ramp.
    if MASK.exists():
        m = np.asarray(Image.open(MASK).convert("L").resize((COLS, ROWS),
                       Image.LANCZOS), dtype=np.float32) / 255.0
        inside = m > 0.5
        subject = arr[inside] if inside.sum() > 64 else arr[arr < 0.97]
    else:
        inside = None
        subject = arr[arr < 0.97]
    if subject.size > 64:
        lo = float(np.percentile(subject, 1.5))
        hi = float(np.percentile(subject, 97.0))
        if hi - lo > 0.03:
            arr = np.clip((arr - lo) / (hi - lo), 0.0, 1.0)

    # gamma < 1 lightens midtones so dark clothing does not become a solid block
    arr = np.clip(arr, 0, 1) ** GAMMA

    # force everything outside the subject to paper white -> ASCII whitespace
    if inside is not None:
        arr = np.where(inside, arr, 1.0)

    idx = ((1.0 - arr) * (len(RAMP) - 1)).round().astype(int)
    idx = np.clip(idx, 0, len(RAMP) - 1)

    rows = ["".join(RAMP[i] for i in row) for row in idx]
    return [r.rstrip() for r in rows]


def build(rows: list[str]) -> str:
    w = int(COLS * CH_W) + PAD * 2
    h = int(ROWS * CH_H) + PAD * 2 + 6
    total = ROW_STEP * len(rows) + ROW_DUR

    parts: list[str] = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img" aria-label="ASCII portrait">'
    )
    parts.append(
        "<style>"
        "text{font-family:'SFMono-Regular',Consolas,'Liberation Mono',Menlo,monospace;"
        f"font-size:{FONT_PX}px;white-space:pre;letter-spacing:0}}"
        "</style>"
    )
    parts.append(f'<rect width="100%" height="100%" fill="{BG}" rx="10"/>')

    for i, line in enumerate(rows):
        if not line.strip():
            continue
        y = PAD + (i + 1) * CH_H
        wipe = int(len(line) * CH_W) + 2
        begin = round(i * ROW_STEP, 3)
        cid = f"c{i}"

        tl = f' textLength="{len(line) * CH_W:.1f}" lengthAdjust="spacingAndGlyphs"'

        if STATIC:
            parts.append(
                f'<text x="{PAD}" y="{y:.1f}" fill="{INK}"{tl}>{html.escape(line)}</text>'
            )
            continue

        # clip rectangle grows from 0 -> full row width, then freezes
        parts.append(
            f'<clipPath id="{cid}"><rect x="{PAD}" y="{y - CH_H:.1f}" '
            f'height="{CH_H + 2:.1f}" width="0">'
            f'<animate attributeName="width" from="0" to="{wipe}" '
            f'dur="{ROW_DUR}s" begin="{begin}s" fill="freeze" '
            f'calcMode="spline" keySplines="0.22 0.61 0.36 1" keyTimes="0;1"/>'
            f"</rect></clipPath>"
        )
        parts.append(
            f'<g clip-path="url(#{cid})">'
            f'<text x="{PAD}" y="{y:.1f}" fill="{INK}"{tl}>{html.escape(line)}</text>'
            f"</g>"
        )
        # block cursor rides the wipe edge, then disappears
        parts.append(
            f'<rect y="{y - CH_H + 2.2:.1f}" width="{CH_W:.1f}" height="{CH_H - 2.4:.1f}" '
            f'fill="{CURSOR}" opacity="0">'
            f'<animate attributeName="x" from="{PAD}" to="{PAD + wipe}" '
            f'dur="{ROW_DUR}s" begin="{begin}s" fill="freeze" '
            f'calcMode="spline" keySplines="0.22 0.61 0.36 1" keyTimes="0;1"/>'
            f'<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.05;0.9;1" '
            f'dur="{ROW_DUR}s" begin="{begin}s" fill="freeze"/>'
            f"</rect>"
        )

    # trailing prompt cursor
    py = PAD + (len(rows) + 1) * CH_H
    blink = (
        ""
        if STATIC
        else f'<animate attributeName="opacity" values="1;0;1" dur="1.05s" '
        f'begin="{total:.2f}s" repeatCount="indefinite"/>'
    )
    op = "1" if STATIC else "0"
    show = (
        ""
        if STATIC
        else f'<set attributeName="opacity" to="1" begin="{total:.2f}s"/>'
    )
    parts.append(
        f'<rect x="{PAD}" y="{py - CH_H + 2.2:.1f}" width="{CH_W:.1f}" '
        f'height="{CH_H - 2.4:.1f}" fill="{CURSOR}" opacity="{op}">{show}{blink}</rect>'
    )
    parts.append("</svg>")
    return "".join(parts)


if __name__ == "__main__":
    grid = load_grid()
    OUT.write_text(build(grid), encoding="utf-8")
    print(f"wrote {OUT}  ({COLS}x{ROWS} chars, static={STATIC})")
