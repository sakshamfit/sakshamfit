#!/usr/bin/env python3
"""
fetch_contributions.py — scrape the public contribution calendar. No GraphQL,
no personal access token.

GitHub serves the calendar as public HTML at:
    https://github.com/users/<username>/contributions
(the same fragment the profile page itself loads)

Writes data/contributions.json — raw days plus derived stats
(total, current streak, longest streak, best day, monthly totals).
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import OrderedDict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

USER = os.environ.get("GH_USER", "sakshamfit")
URL = f"https://github.com/users/{USER}/contributions"
OUT = Path("data/contributions.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (profile-art bot; +https://github.com/%s)" % USER,
    "Accept": "text/html",
    "X-Requested-With": "XMLHttpRequest",
}


def level_for(count: int, peak: int) -> int:
    """0-5. Levels 1-4 mirror GitHub; 5 is a neon top end for standouts."""
    if count <= 0:
        return 0
    if peak <= 4:
        return min(4, count)
    q = count / peak
    if count >= max(12, peak * 0.85):
        return 5
    if q > 0.5:
        return 4
    if q > 0.25:
        return 3
    if q > 0.1:
        return 2
    return 1


def parse(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    cells = soup.select("td.ContributionCalendar-day[data-date]")
    if not cells:
        cells = soup.select("[data-date][data-level]")

    # counts live either in data-count or in the adjacent tooltip/span text
    tips: dict[str, str] = {}
    for tl in soup.select("tool-tip[for]"):
        tips[tl.get("for", "")] = tl.get_text(" ", strip=True)

    days: list[dict] = []
    for c in cells:
        d = c.get("data-date")
        if not d:
            continue
        count = c.get("data-count")
        if count is None:
            txt = tips.get(c.get("id", ""), "") or c.get_text(" ", strip=True)
            m = re.search(r"(\d[\d,]*)\s+contribution", txt)
            count = m.group(1).replace(",", "") if m else "0"
            if re.search(r"\bNo contributions\b", txt, re.I):
                count = "0"
        days.append({"date": d, "count": int(count)})

    days.sort(key=lambda x: x["date"])
    return days


def streaks(days: list[dict]) -> tuple[int, int]:
    longest = run = 0
    for d in days:
        run = run + 1 if d["count"] > 0 else 0
        longest = max(longest, run)

    today = date.today()
    by = {d["date"]: d["count"] for d in days}
    cur = 0
    cursor = today
    # today not being logged yet shouldn't break a live streak
    if by.get(cursor.isoformat(), 0) == 0:
        cursor -= timedelta(days=1)
    while by.get(cursor.isoformat(), 0) > 0:
        cur += 1
        cursor -= timedelta(days=1)
    return cur, longest


def main() -> None:
    print(f"fetching {URL}")
    r = requests.get(URL, headers=HEADERS, timeout=30)
    r.raise_for_status()

    days = parse(r.text)
    if not days:
        sys.exit("parsed 0 days - GitHub markup may have changed")

    peak = max(d["count"] for d in days)
    for d in days:
        d["level"] = level_for(d["count"], peak)

    total = sum(d["count"] for d in days)
    cur, longest = streaks(days)
    best = max(days, key=lambda d: d["count"])

    months: "OrderedDict[str, int]" = OrderedDict()
    for d in days:
        months[d["date"][:7]] = months.get(d["date"][:7], 0) + d["count"]

    payload = {
        "user": USER,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "range": {"from": days[0]["date"], "to": days[-1]["date"]},
        "stats": {
            "total": total,
            "days_active": sum(1 for d in days if d["count"] > 0),
            "current_streak": cur,
            "longest_streak": longest,
            "best_day": {"date": best["date"], "count": best["count"]},
            "busiest_month": max(months, key=months.get),
            "peak": peak,
        },
        "months": months,
        "days": days,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(
        f"wrote {OUT}  {len(days)} days · {total} contributions · "
        f"streak {cur} (best {longest})"
    )


if __name__ == "__main__":
    main()
