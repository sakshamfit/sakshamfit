#!/usr/bin/env python3
"""
render_heatmap_svg.py — draw data/contributions.json as an animated
53-week x 7-day calendar of rounded boxes.

    python scripts/render_heatmap_svg.py           # writes contrib-heatmap.svg
    STATIC=1 python scripts/render_heatmap_svg.py  # frozen frame

The reveal is a diagonal, column-after-column slide-down driven by CSS
keyframes with `forwards` - it plays once on load and freezes. No looping
glow: a README that never stops moving is exhausting to look at.
"""
from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path

SRC = Path("data/contributions.json")
OUT = Path("contrib-heatmap.svg")
STATIC = os.environ.get("STATIC") == "1"

PALETTE = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353", "#69f0a0"]
#          none  ->  brightest (level 5 is a neon top end)

BG = "#0d1117"
BORDER = "#21262d"
DIM = "#7d8590"
TEXT = "#c9d1d9"
ACCENT = "#39d353"

CELL = 12
GAP = 3
STEP = CELL + GAP           # 15
PAD = 20
TOP = 58                    # title bar + month labels
LEFT = PAD + 30             # room for weekday labels
FOOT = 46

FONT = "'SFMono-Regular',Consolas,'Liberation Mono',Menlo,monospace"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

COL_DELAY = 0.016   # per-column stagger
ROW_DELAY = 0.030   # per-row stagger -> together they read as a diagonal
CELL_DUR = 0.34


def load() -> dict:
    if not SRC.exists():
        raise SystemExit(f"missing {SRC} - run: python scripts/fetch_contributions.py")
    return json.loads(SRC.read_text(encoding="utf-8"))


def grid(days: list[dict]) -> list[list[dict | None]]:
    """Bucket days into columns of 7, Sunday-first, like GitHub."""
    cols: list[list[dict | None]] = []
    col: list[dict | None] = [None] * 7
    first_dow = (date.fromisoformat(days[0]["date"]).weekday() + 1) % 7  # Sun=0
    idx = first_dow
    for d in days:
        col[idx] = d
        idx += 1
        if idx == 7:
            cols.append(col)
            col = [None] * 7
            idx = 0
    if any(c is not None for c in col):
        cols.append(col)
    return cols


def build(data: dict) -> str:
    days = data["days"]
    st = data["stats"]
    cols = grid(days)

    w = LEFT + len(cols) * STEP + PAD
    h = TOP + 7 * STEP + FOOT

    p: list[str] = []
    p.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img" '
        f'aria-label="{st["total"]} contributions in the last year">'
    )
    p.append(
        "<style>"
        f"text{{font-family:{FONT}}}"
        ".lbl{font-size:10px;fill:%s}" % DIM
        + ".ttl{font-size:12px}"
        + ".c,.fi{transform-box:fill-box;transform-origin:center}"
        + (
            ""
            if STATIC
            else ".c{opacity:0;animation:pop .34s cubic-bezier(.22,.61,.36,1) forwards}"
            "@keyframes pop{from{opacity:0;transform:translateY(-7px) scale(.72)}"
            "to{opacity:1;transform:translateY(0) scale(1)}}"
            ".fi{opacity:0;animation:fi .5s ease-out forwards}"
            "@keyframes fi{to{opacity:1}}"
        )
        + "</style>"
    )
    p.append(
        f'<rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="10" '
        f'fill="{BG}" stroke="{BORDER}"/>'
    )

    total_cells = len(cols) * 7
    last_delay = (len(cols) - 1) * COL_DELAY + 6 * ROW_DELAY + CELL_DUR

    def fade(delay: float, base: str = "") -> str:
        """Class + delay for a play-once fade-in (classes must be merged, not
        duplicated - an SVG element may only carry one class attribute)."""
        if STATIC:
            return f' class="{base}"' if base else ""
        cls = f"{base} fi".strip()
        return f' class="{cls}" style="animation-delay:{delay:.2f}s"'

    # header
    p.append(
        f'<text x="{PAD}" y="26" fill="{TEXT}"{fade(0.05, "ttl")}>'
        f'<tspan fill="{ACCENT}">{st["total"]:,}</tspan> contributions in the last year'
        f"</text>"
    )
    p.append(
        f'<text x="{w-PAD}" y="26" text-anchor="end"{fade(0.15, "lbl")}>'
        f'{data["range"]["from"]} .. {data["range"]["to"]}</text>'
    )

    # month labels
    seen = set()
    for ci, col in enumerate(cols):
        first = next((d for d in col if d), None)
        if not first:
            continue
        dt = date.fromisoformat(first["date"])
        key = (dt.year, dt.month)
        if dt.day <= 7 and key not in seen:
            seen.add(key)
            p.append(
                f'<text x="{LEFT + ci*STEP}" y="{TOP-8}"'
                f'{fade(0.2 + ci*0.004, "lbl")}>{MONTHS[dt.month-1]}</text>'
            )

    # weekday labels (Mon/Wed/Fri, like GitHub)
    for ri, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        p.append(
            f'<text x="{PAD}" y="{TOP + ri*STEP + CELL - 2}"'
            f'{fade(0.2, "lbl")}>{name}</text>'
        )

    # the grid
    for ci, col in enumerate(cols):
        for ri, d in enumerate(col):
            x = LEFT + ci * STEP
            y = TOP + ri * STEP
            if d is None:
                continue
            lvl = d["level"]
            delay = ci * COL_DELAY + ri * ROW_DELAY
            cls = "" if STATIC else f' class="c" style="animation-delay:{delay:.2f}s"'
            n = d["count"]
            label = "No contributions" if n == 0 else f"{n} contribution{'s'[:n^1]}"
            p.append(
                f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2.5" '
                f'fill="{PALETTE[lvl]}"{cls}>'
                f"<title>{label} on {d['date']}</title></rect>"
            )

    # footer: stats line + Less -> More legend
    fy = TOP + 7 * STEP + 26
    p.append(
        f'<text x="{PAD}" y="{fy}" fill="{DIM}"{fade(last_delay, "lbl")}>'
        f'streak <tspan fill="{ACCENT}">{st["current_streak"]}d</tspan>'
        f'  ·  longest <tspan fill="{TEXT}">{st["longest_streak"]}d</tspan>'
        f'  ·  best day <tspan fill="{TEXT}">{st["best_day"]["count"]}</tspan>'
        f' ({st["best_day"]["date"]})'
        f'  ·  active <tspan fill="{TEXT}">{st["days_active"]}</tspan> days'
        f"</text>"
    )

    lx = w - PAD - (len(PALETTE) * (CELL + 2) + 74)
    p.append(
        f'<text x="{lx}" y="{fy}"{fade(last_delay, "lbl")}>Less</text>'
    )
    for i, c in enumerate(PALETTE):
        p.append(
            f'<rect x="{lx + 30 + i*(CELL+2)}" y="{fy-9}" width="{CELL}" '
            f'height="{CELL}" rx="2.5" fill="{c}"{fade(last_delay + 0.03*i)}/>'
        )
    p.append(
        f'<text x="{lx + 36 + len(PALETTE)*(CELL+2)}" y="{fy}"'
        f'{fade(last_delay + 0.2, "lbl")}>More</text>'
    )

    p.append("</svg>")
    print(f"  {len(cols)} weeks · {total_cells} cells · reveal ~{last_delay:.1f}s")
    return "".join(p)


if __name__ == "__main__":
    OUT.write_text(build(load()), encoding="utf-8")
    print(f"wrote {OUT}  (static={STATIC})")
