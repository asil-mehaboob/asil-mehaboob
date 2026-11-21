#!/usr/bin/env python3
"""
Scrape daily contribution counts from GitHub's public contributions fragment (the
same HTML the profile page loads) and write data/contributions.json with the raw
days plus derived stats: streaks, busiest day, active days and monthly totals.

No token and no third-party packages. Run daily by
.github/workflows/update-profile-art.yml.
"""
import datetime
import json
import os
import re
import sys
import urllib.request

USERNAME = os.environ.get("GH_PROFILE_USER", "asil-mehaboob")
URL = f"https://github.com/users/{USERNAME}/contributions"
OUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "contributions.json")


def fetch_days():
    req = urllib.request.Request(URL, headers={"User-Agent": "profile-readme-bot/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        html = r.read().decode("utf-8")

    tips = dict(re.findall(r'<tool-tip[^>]*\bfor="([^"]+)"[^>]*>([^<]*)</tool-tip>', html))
    days = []
    for td in re.findall(r"<td[^>]*ContributionCalendar-day[^>]*>", html):
        date = re.search(r'data-date="([^"]+)"', td)
        if not date:
            continue
        td_id = re.search(r'\bid="([^"]+)"', td)
        level = re.search(r'data-level="(\d+)"', td)
        text = tips.get(td_id.group(1), "") if td_id else ""
        m = re.match(r"([\d,]+)", text.strip())
        count = int(m.group(1).replace(",", "")) if m else 0
        days.append({"date": date.group(1), "count": count, "level": int(level.group(1)) if level else 0})

    if not days:
        print("no calendar cells found -- github markup may have changed", file=sys.stderr)
        sys.exit(1)
    days.sort(key=lambda d: d["date"])
    return days


def current_streak(days):
    idx = len(days) - 1
    if days[idx]["count"] == 0:
        idx -= 1  # today isn't over yet, so it doesn't break the streak
    end, streak = idx, 0
    while idx >= 0 and days[idx]["count"] > 0:
        streak += 1
        idx -= 1
    if not streak:
        return 0, None, None
    return streak, days[idx + 1]["date"], days[end]["date"]


def longest_streak(days):
    longest = run = 0
    start = end = run_start = None
    for i, d in enumerate(days):
        if d["count"] > 0:
            if run == 0:
                run_start = i
            run += 1
            if run > longest:
                longest, start, end = run, days[run_start]["date"], d["date"]
        else:
            run = 0
    return longest, start, end


def build(days):
    total = sum(d["count"] for d in days)
    active = sum(1 for d in days if d["count"] > 0)
    best = max(days, key=lambda d: d["count"])
    cl, cs, ce = current_streak(days)
    ll, ls, le = longest_streak(days)
    monthly = {}
    for d in days:
        monthly[d["date"][:7]] = monthly.get(d["date"][:7], 0) + d["count"]
    return {
        "username": USERNAME,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "range": {"start": days[0]["date"], "end": days[-1]["date"]},
        "total_contributions": total,
        "active_days": active,
        "avg_per_active_day": round(total / active, 1) if active else 0,
        "current_streak": {"length": cl, "start": cs, "end": ce},
        "longest_streak": {"length": ll, "start": ls, "end": le},
        "best_day": {"date": best["date"], "count": best["count"]},
        "monthly": [{"month": k, "total": v} for k, v in sorted(monthly.items())],
        "days": days,
    }


if __name__ == "__main__":
    data = build(fetch_days())
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(data, f, indent=2)
    print(f"wrote data/contributions.json: {data['total_contributions']} contributions, "
          f"current streak {data['current_streak']['length']}, longest {data['longest_streak']['length']}")
