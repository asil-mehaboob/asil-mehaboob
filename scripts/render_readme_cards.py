#!/usr/bin/env python3
"""
Render the profile README's cards as animated SVGs into cards/.

Layout and animation follow Avi Vashishta's "animated SVG cards" profile README
(avivashishta.com/blog/github-profile-readme-animated-svg-cards): paper, ink and
one green accent; Instrument Serif,
Geist and Geist Mono.

Every card is a standalone SVG shown through <img>, so it can only use what GitHub
allows there: inline CSS animations, SMIL and fonts embedded as data URIs (no JS,
no external requests). Fonts are subset WOFFs in fonts/ (SIL OFL).

Live numbers come from data/contributions.json (fetch_contributions.py).
 STATIC=1 renders every animation at its end state for previews.

Run by .github/workflows/update-profile-art.yml after fetch_contributions.py.
"""
import base64
import datetime
import json
import os
import re
from html import escape

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
DATA = os.path.join(ROOT, "data", "contributions.json")
OUT = os.path.join(ROOT, "cards")
FONTS = os.path.join(ROOT, "fonts")

# ---- brand tokens -----------------------------------------------------------
PAPER = "#f3f3f1"
PAPER_DEEP = "#e2e2de"
INK = "#111111"
INK_SOFT = "#3a3a3c"
MUTED = "#6e6e73"
RULE = "#dcdcd7"
ACCENT = "#12a150"  # green
W = 880  # full card width, GitHub's README column at 100%

SERIF = "'Instrument Serif', Georgia, serif"
SANS = "Geist, system-ui, -apple-system, sans-serif"
MONO = "'Geist Mono', ui-monospace, SFMono-Regular, Menlo, monospace"

FONT_FILES = {
    "serif": ("Instrument Serif", "normal", 400, "serif-400.woff"),
    "serif-i": ("Instrument Serif", "italic", 400, "serif-italic.woff"),
    "sans": ("Geist", "normal", 400, "geist-400.woff"),
    "sans-b": ("Geist", "normal", 600, "geist-600.woff"),
    "mono": ("Geist Mono", "normal", 400, "geistmono-400.woff"),
}

BASE_CSS = """
@keyframes rise{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:none}}
@keyframes fade{from{opacity:0}to{opacity:1}}
@keyframes grow{from{transform:scaleY(0)}to{transform:scaleY(1)}}
@keyframes pop{0%{opacity:0;transform:scale(.3)}70%{opacity:1;transform:scale(1.15)}100%{opacity:1;transform:none}}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.25}}
@keyframes nudge{0%,100%{transform:none}50%{transform:translateX(4px)}}
@keyframes nudgeup{0%,100%{transform:none}50%{transform:translate(3px,-3px)}}
.r{opacity:0;animation:rise .8s cubic-bezier(.2,.7,.2,1) both;transform-box:fill-box}
.f{opacity:0;animation:fade .9s ease-out both}
.g{transform-box:fill-box;transform-origin:bottom;transform:scaleY(0);animation:grow .8s cubic-bezier(.2,.7,.2,1) both}
.p{opacity:0;transform-box:fill-box;transform-origin:center;animation:pop .4s ease-out both}
.live{animation:pulse 1.6s ease-in-out infinite}
.n{transform-box:fill-box;animation:nudge 1.8s ease-in-out infinite}
.nu{transform-box:fill-box;animation:nudgeup 1.8s ease-in-out infinite}
@keyframes tilein{0%{opacity:0;transform:translateY(90px) scale(.6) rotate(-9deg)}55%{opacity:1;transform:translateY(-10px) scale(1.05) rotate(2deg)}75%{transform:translateY(3px) scale(.98) rotate(-.8deg)}90%{transform:translateY(-1px) scale(1.01) rotate(.2deg)}100%{opacity:1;transform:none}}
@keyframes slidein{from{opacity:0;transform:translateX(-26px)}to{opacity:1;transform:none}}
@keyframes arrowin{0%{opacity:0;transform:translateX(-30px)}60%{opacity:1;transform:translateX(6px)}100%{opacity:1;transform:none}}
@keyframes roll{from{transform:translateY(60px)}to{transform:none}}
@keyframes sheen{0%{transform:translateX(-260px) skewX(-20deg)}22%,100%{transform:translateX(420px) skewX(-20deg)}}
@keyframes ring{0%{opacity:.7;transform:scale(.2)}100%{opacity:0;transform:scale(2.4)}}
.ti{opacity:0;transform-box:fill-box;transform-origin:50% 60%;animation:tilein 1.1s cubic-bezier(.2,.8,.2,1) both}
.sl{opacity:0;transform-box:fill-box;animation:slidein .6s cubic-bezier(.2,.7,.2,1) both}
.ai{opacity:0;transform-box:fill-box;animation:arrowin .7s cubic-bezier(.2,.7,.2,1) both}
.ro{transform-box:fill-box;animation:roll .8s cubic-bezier(.15,.8,.2,1) both}
.sh{animation:sheen 4s ease-in-out infinite}
.rg{opacity:0;transform-box:fill-box;transform-origin:center;animation:ring 1s ease-out both}
@keyframes ringloop{0%{opacity:.6;transform:scale(.2)}40%,100%{opacity:0;transform:scale(2.4)}}
.rgl{opacity:0;transform-box:fill-box;transform-origin:center;animation:ringloop 3.2s ease-out infinite}
@media (prefers-reduced-motion: reduce){.r,.f,.g,.p,.live,.n,.nu,.ti,.sl,.ai,.ro,.rg{animation:none!important;opacity:1!important;transform:none!important}.sh,.rg,.rgl{display:none}}
"""


def font_face(keys):
    out = []
    for k in keys:
        fam, style, weight, fn = FONT_FILES[k]
        b64 = base64.b64encode(open(os.path.join(FONTS, fn), "rb").read()).decode()
        out.append(
            f"@font-face{{font-family:'{fam}';font-style:{style};font-weight:{weight};"
            f"src:url(data:font/woff;base64,{b64}) format('woff')}}"
        )
    return "".join(out)


GAP = 12          # gap between cards, baked into the SVGs (GitHub's own spacing is uneven)
BOTTOM = 12       # bottom padding per row, matching GAP
COL = W / 3       # each card in a row of three is exactly a third of the column


def svg(w, h, body, fonts, label, extra_css="", left=0, right=0, bottom=BOTTOM):
    """Card of w x h drawn at x=left inside a transparent canvas, padded so rows tile exactly."""
    if left:
        body = f'<g transform="translate({left:.3f} 0)">{body}</g>'
    w, h = w + left + right, h + bottom
    css = font_face(fonts) + BASE_CSS + extra_css
    if os.environ.get("STATIC"):  # preview: show every animation at its end state
        css += ".r,.f,.g,.p,.live,.n,.nu,.ti,.sl,.ai,.ro{animation:none!important;opacity:1!important;transform:none!important}.sh,.rg,.rgl{display:none}"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.3f}" height="{h}" viewBox="0 0 {w:.3f} {h}" '
        f'role="img" aria-label="{escape(label)}"><title>{escape(label)}</title>'
        f"<style>{css}</style>{body}</svg>"
    )


def write(name, content):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print(f"wrote cards/{name} ({len(content) // 1024} KB)")


def d(s):  # animation delay attribute
    return f'style="animation-delay:{s:.2f}s"'


def wrap(text, n):
    lines, line = [], ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > n:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    return lines + [line] if line else lines


def text_lines(x, y, lines, lh, attrs):
    return "".join(
        f'<text x="{x}" y="{y + i * lh}" {attrs}>{escape(l)}</text>' for i, l in enumerate(lines)
    )


# ---- 1 · hero -----------------------------------------------------------------
def hero():
    h = 300
    body = f"""
<defs>
  <linearGradient id="shine" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="600" y2="0">
    <stop offset="0" stop-color="{INK}"/><stop offset=".42" stop-color="{INK}"/>
    <stop offset=".5" stop-color="{ACCENT}"/><stop offset=".58" stop-color="{INK}"/>
    <stop offset="1" stop-color="{INK}"/>
    <animateTransform attributeName="gradientTransform" type="translate" values="-600 0;600 0;600 0"
      keyTimes="0;.45;1" dur="7s" begin="1.6s" repeatCount="indefinite"/>
  </linearGradient>
</defs>
<rect width="{W}" height="{h}" rx="14" fill="{PAPER}"/>
<text class="r" {d(0.15)} x="44" y="150" font-family="{SERIF}" font-size="116" letter-spacing="-2.5" fill="{INK}">Asil</text>
<text class="r" {d(0.3)} x="44" y="250" font-family="{SERIF}" font-style="italic" font-size="116" letter-spacing="-2.5" fill="url(#shine)">Mehaboob</text>
<rect class="f" {d(0.5)} x="540" y="90" width="1" height="160" fill="{RULE}"/>
<text class="r" {d(0.7)} x="570" y="176" font-family="{SERIF}" font-size="68" letter-spacing="-1" fill="{INK}">forgesaas<tspan class="live" fill="{ACCENT}">.</tspan></text>
<text class="r" {d(0.85)} x="572" y="216" font-family="{SANS}" font-size="18" fill="{INK_SOFT}">Shipping products end to end.</text>
"""
    write("hero.svg", svg(W, h, body, ["serif", "serif-i", "sans", "mono"],
                          "Asil Mehaboob. forgesaas. Shipping products end to end."))


# ---- 2 · green contribution graph -----------------------------------------------
RAMP = [PAPER_DEEP, "#c6ead3", "#8fd5aa", "#4fba7d", ACCENT, "#0a7a3a"]


def level_for(c):
    return 0 if c == 0 else 1 if c <= 5 else 2 if c <= 15 else 3 if c <= 30 else 4 if c <= 50 else 5


def heatmap(data):
    days = data["days"]
    first = datetime.date.fromisoformat(days[0]["date"])
    lead = (first.weekday() + 1) % 7  # sunday = 0
    cell, step, gx, gy = 12, 15, 44, 96
    cells, months, seen = [], [], set()
    for i, day in enumerate(days):
        k = i + lead
        col, row = divmod(k, 7)
        date = datetime.date.fromisoformat(day["date"])
        if date.day <= 7 and (date.year, date.month) not in seen and row == 0:
            seen.add((date.year, date.month))
            months.append((col, date.strftime("%b")))
        c = day["count"]
        delay = 1.0 + col * 0.03 + row * 0.02
        cells.append(
            f'<rect class="p" style="animation-delay:{delay:.2f}s" x="{gx + col * step}" y="{gy + row * step}" '
            f'width="{cell}" height="{cell}" rx="3" fill="{RAMP[level_for(c)]}">'
            f'<title>{day["date"]}: {c} contribution{"s" if c != 1 else ""}</title></rect>'
        )
    ncols = (len(days) + lead + 6) // 7
    right = gx + ncols * step - 3
    labels = "".join(
        f'<text x="{gx + col * step}" y="{gy + 7 * step + 16}" font-family="{MONO}" font-size="11" fill="{MUTED}">{m}</text>'
        for col, m in months if col < ncols - 12
    )
    legend_x = right - len(RAMP) * 14
    legend = "".join(
        f'<rect x="{legend_x + i * 14}" y="{gy + 7 * step + 6}" width="11" height="11" rx="2.5" fill="{c}"/>'
        for i, c in enumerate(RAMP)
    )
    h = gy + 7 * step + 44
    body = f"""
<rect width="{W}" height="{h}" rx="14" fill="{PAPER}"/>
<text class="r" {d(0.8)} x="42" y="62" font-family="{SERIF}" font-size="34" fill="{INK}">Every day, <tspan font-style="italic" fill="{ACCENT}">in green</tspan></text>
{''.join(cells)}
<g class="f" {d(2.4)}>{labels}
<text x="{legend_x - 8}" y="{gy + 7 * step + 16}" text-anchor="end" font-family="{MONO}" font-size="11" fill="{MUTED}">less</text>
{legend}
<text x="{legend_x + len(RAMP) * 14 + 2}" y="{gy + 7 * step + 16}" font-family="{MONO}" font-size="11" fill="{MUTED}">more</text></g>
"""
    write("heatmap.svg", svg(W, h, body, ["serif", "serif-i", "mono"],
                             f'Contribution graph: {data["total_contributions"]:,} contributions in the last year'))


if __name__ == "__main__":
    data = json.load(open(DATA, encoding="utf-8"))
    hero()
    heatmap(data)
