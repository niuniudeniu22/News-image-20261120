"""Render entry.png: a newspaper front page for Friday 20 November 2026.

Run:   python build_entry.py [out.png]
Out:   1024x1024 PNG, well under 1 MiB.

Everything is drawn with Pillow -- no network, no external assets. Each block is
measured as it is laid out and the build stops with an error if a block would
overflow its cell, so the committed image is a clean page and not a guess.
"""

from __future__ import annotations

import os
import sys

from PIL import Image, ImageDraw, ImageFont

W = H = 1024
M = 40  # page margin

INK = (24, 20, 16)
RED = (168, 44, 32)
MUTED = (100, 90, 76)
RULE = (196, 185, 165)
FAINT = (214, 204, 186)
WHITE = (251, 248, 242)

FONT_DIRS = [
    r"C:\Windows\Fonts",
    "/usr/share/fonts/truetype/dejavu",
    "/System/Library/Fonts/Supplemental",
    "/Library/Fonts",
]

# role -> candidate files, best first
FONT_FILES = {
    "serif_bold": ["georgiab.ttf", "DejaVuSerif-Bold.ttf", "timesbd.ttf"],
    "serif_italic": ["georgiai.ttf", "DejaVuSerif-Italic.ttf", "timesi.ttf"],
    "sans": ["segoeui.ttf", "DejaVuSans.ttf", "arial.ttf"],
    "sans_bold": ["segoeuib.ttf", "DejaVuSans-Bold.ttf", "arialbd.ttf"],
    "sans_semibold": ["seguisb.ttf", "DejaVuSans-Bold.ttf", "arialbd.ttf"],
}


def find_font_file(names: list[str]) -> str:
    for name in names:
        for folder in FONT_DIRS:
            path = os.path.join(folder, name)
            if os.path.isfile(path):
                return path
    raise SystemExit(f"no usable font for {names}")


FONT_PATHS = {role: find_font_file(names) for role, names in FONT_FILES.items()}
_CACHE: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}


def font(role: str, size: int) -> ImageFont.FreeTypeFont:
    key = (role, size)
    if key not in _CACHE:
        _CACHE[key] = ImageFont.truetype(FONT_PATHS[role], size)
    return _CACHE[key]


# --- measuring --------------------------------------------------------------

def text_width(draw: ImageDraw.ImageDraw, text: str, f: ImageFont.FreeTypeFont,
               tracking: float = 0.0) -> float:
    if not text:
        return 0.0
    if tracking == 0.0:
        return draw.textlength(text, font=f)
    return sum(draw.textlength(ch, font=f) for ch in text) + tracking * (len(text) - 1)


def draw_tracked(draw: ImageDraw.ImageDraw, xy: tuple[float, float], text: str,
                 f: ImageFont.FreeTypeFont, fill, tracking: float = 0.0) -> None:
    x, y = xy
    if tracking == 0.0:
        draw.text((x, y), text, font=f, fill=fill)
        return
    for ch in text:
        draw.text((x, y), ch, font=f, fill=fill)
        x += draw.textlength(ch, font=f) + tracking


def wrap(draw: ImageDraw.ImageDraw, text: str, f: ImageFont.FreeTypeFont,
         max_width: float) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        current = ""
        for word in paragraph.split():
            candidate = f"{current} {word}".strip()
            if not current or text_width(draw, candidate, f) <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
    return lines


def rule(draw: ImageDraw.ImageDraw, x0: float, y: float, x1: float,
         color=RULE, weight: int = 1) -> None:
    draw.rectangle([x0, y, x1, y + weight - 1], fill=color)


def vrule(draw: ImageDraw.ImageDraw, x: float, y0: float, y1: float,
          color=RULE, weight: int = 1) -> None:
    draw.rectangle([x, y0, x + weight - 1, y1], fill=color)


def kicker(draw: ImageDraw.ImageDraw, x: float, y: float, num: str, label: str,
           size: int, gap: float) -> None:
    f = font("sans_bold", size)
    draw_tracked(draw, (x, y), num, f, RED, 1.4)
    nw = text_width(draw, num, f, 1.4)
    draw_tracked(draw, (x + nw + gap, y), "/", f, RED)
    fl = font("sans_semibold", size)
    draw_tracked(draw, (x + nw + gap + 10, y + 1), label.upper(), fl, MUTED, 2.0)


# --- page -------------------------------------------------------------------

def paper() -> Image.Image:
    """A vertical paper gradient plus a soft vignette: cheap and compressible."""
    strip = Image.new("RGB", (1, H))
    px = strip.load()
    top, bottom = (250, 246, 238), (237, 229, 214)
    for y in range(H):
        t = y / (H - 1)
        px[0, y] = tuple(round(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
    base = strip.resize((W, H), Image.BILINEAR)

    mask = Image.new("L", (96, 96))
    mp = mask.load()
    for y in range(96):
        for x in range(96):
            dx = (x - 47.5) / 47.5
            dy = (y - 47.5) / 47.5
            r = min(1.0, (dx * dx + dy * dy) ** 0.5)
            mp[x, y] = int(max(0.0, (r - 0.5) / 0.5) * 24)
    shade = Image.new("RGB", (W, H), (226, 216, 198))
    return Image.composite(shade, base, mask.resize((W, H), Image.BICUBIC))


# --- blocks -----------------------------------------------------------------

def lead(draw: ImageDraw.ImageDraw, x: float, y: float, w: float, h: float,
         num: str, label: str, headline: str, deck: str) -> None:
    rule(draw, x, y, x + w - 1, RED, 3)
    kicker(draw, x, y + 20, num, label, 11, 10)

    deck_f = font("serif_italic", 19)
    deck_lines = wrap(draw, deck, deck_f, w)
    if len(deck_lines) > 3:
        raise SystemExit(f"lead deck wraps to {len(deck_lines)} lines")
    deck_lh = 25

    top = y + 54
    avail = h - (top - y) - len(deck_lines) * deck_lh - 18
    size = None
    for candidate in range(56, 29, -2):
        f = font("serif_bold", candidate)
        lines = wrap(draw, headline, f, w)
        if len(lines) * candidate * 1.06 <= avail:
            size = candidate
            break
    if size is None:
        raise SystemExit("lead headline does not fit")
    f = font("serif_bold", size)
    lines = wrap(draw, headline, f, w)
    lh = size * 1.06

    ty = top
    for line in lines:
        draw.text((x - 2, ty), line, font=f, fill=INK)
        ty += lh
    ty += 6
    rule(draw, x, ty, x + 116, RED, 2)
    ty += 15
    for line in deck_lines:
        draw.text((x, ty), line, font=deck_f, fill=MUTED)
        ty += deck_lh
    if ty > y + h + 1:
        raise SystemExit(f"lead overflows by {ty - (y + h):.1f}px")


def brief(draw: ImageDraw.ImageDraw, x: float, y: float, w: float, h: float,
          size: int, num: str, label: str, headline: str, deck: str) -> None:
    rule(draw, x, y, x + w - 1, RULE, 1)
    kicker(draw, x, y + 15, num, label, 9, 7)

    f = font("serif_bold", size)
    lines = wrap(draw, headline, f, w)
    lh = size * 1.10

    deck_f = font("sans", 14)
    deck_lines = wrap(draw, deck, deck_f, w)
    deck_lh = 19

    ty = y + 46
    for line in lines:
        draw.text((x, ty), line, font=f, fill=INK)
        ty += lh
    ty += 9
    for line in deck_lines:
        draw.text((x, ty), line, font=deck_f, fill=MUTED)
        ty += deck_lh
    if ty > y + h + 1:
        raise SystemExit(f"brief {num} overflows by {ty - (y + h):.1f}px")


def date_panel(draw: ImageDraw.ImageDraw, x: float, y: float, w: float, h: float) -> None:
    draw.rectangle([x, y, x + w - 1, y + h - 1], fill=INK)
    pad = 20
    draw_tracked(draw, (x + pad, y + 18), "FRIDAY", font("sans_semibold", 9), RED, 3.6)
    draw.text((x + pad - 4, y + 34), "20", font=font("serif_bold", 80), fill=WHITE)
    draw.text((x + pad, y + 142), "NOVEMBER 2026", font=font("serif_bold", 24), fill=WHITE)
    rule(draw, x + pad, y + 176, x + w - pad, RED, 2)
    ff = font("sans_semibold", 8)
    draw_tracked(draw, (x + pad, y + 188), "SEVEN STORIES", ff, WHITE, 2.2)
    draw_tracked(draw, (x + pad, y + 204), "ONE FRONT PAGE", ff, (200, 122, 110), 2.2)


# --- content ----------------------------------------------------------------

STORIES = [
    ("01", "World",
     "ICJ: Myanmar committed genocide against Rohingya",
     "The court finds the 2017 campaign amounted to genocide."),
    ("02", "Asia-Pacific",
     "Trump, Xi and Putin in first three-way summit as APEC closes in Shenzhen",
     "Three leaders share one stage as the summit closes."),
    ("03", "Markets",
     "Anthropic IPO debut",
     "Shares begin trading in the AI company's public debut."),
    ("04", "Climate",
     "COP31 ends, fossil-fuel transition text cut",
     "Talks close with the transition text weakened."),
    ("05", "Europe",
     "Putin rules out sea and energy truce after Crimea Bridge hit again",
     "Moscow refuses a truce at sea or on energy targets."),
    ("06", "Middle East",
     "Iran steps up Hormuz tanker attacks",
     "Attacks on shipping in the strait intensify."),
    ("07", "Middle East",
     "Gaza: 65,000 tents wait at border",
     "Shelters pile up at the crossing with nowhere to go."),
]

TITLE = "WORLD NEWS - 20 NOV 2026"

# grid: three 300px columns, 22px gutters, 944px of content
COL_W, GUT = 300, 22
COLS = [M, M + COL_W + GUT, M + 2 * (COL_W + GUT)]
ROWS = [200, 458, 716]
ROW_H, LEAD_H = 232, 490


def brief_size(draw: ImageDraw.ImageDraw, w: float, h: float) -> int:
    """One headline size for every brief, so the grid reads as a single design."""
    for size in range(27, 17, -1):
        ok = True
        for _, _, head, deck in STORIES[1:]:
            f = font("serif_bold", size)
            if len(wrap(draw, head, f, w)) * size * 1.10 > h - 46 - 9 - 19 * 2:
                ok = False
                break
        if ok:
            return size
    raise SystemExit("no uniform brief size fits")


def main() -> None:
    out = sys.argv[1] if len(sys.argv) > 1 else "entry.png"
    img = paper()
    draw = ImageDraw.Draw(img)

    # top strap
    fs = font("sans_semibold", 9)
    draw_tracked(draw, (M, 28), "THE WORLD IN ONE PAGE", fs, RED, 3.2)
    right = "LATE EDITION  /  NO. 20"
    draw_tracked(draw, (W - M - text_width(draw, right, fs, 3.2), 28), right, fs, MUTED, 3.2)
    rule(draw, M, 48, W - M - 1, FAINT, 1)

    # masthead
    size = None
    for candidate in range(84, 39, -2):
        f = font("serif_bold", candidate)
        if text_width(draw, TITLE, f, -1.6) <= W - 2 * M:
            size = candidate
            break
    if size is None:
        raise SystemExit("title does not fit")
    tf = font("serif_bold", size)
    tw = text_width(draw, TITLE, tf, -1.6)
    draw_tracked(draw, ((W - tw) / 2, 62), TITLE, tf, INK, -1.6)

    rule(draw, M, 158, W - M - 1, INK, 4)
    rule(draw, M, 166, W - M - 1, RULE, 1)
    f_strip = font("sans_semibold", 9)
    draw_tracked(draw, (M, 176), "THE DAY IN SEVEN STORIES", f_strip, MUTED, 2.6)
    right = "FRIDAY 20 NOVEMBER 2026"
    draw_tracked(draw, (W - M - text_width(draw, right, f_strip, 2.6), 176),
                 right, f_strip, MUTED, 2.6)

    # column rules
    for boundary in (COLS[1] - GUT // 2, COLS[2] - GUT // 2):
        vrule(draw, boundary, ROWS[0], ROWS[2] + ROW_H, FAINT, 1)

    bsize = brief_size(draw, COL_W, ROW_H)
    lead(draw, COLS[0], ROWS[0], COL_W, LEAD_H, *STORIES[0])
    brief(draw, COLS[1], ROWS[0], COL_W, ROW_H, bsize, *STORIES[1])
    brief(draw, COLS[2], ROWS[0], COL_W, ROW_H, bsize, *STORIES[2])
    brief(draw, COLS[1], ROWS[1], COL_W, ROW_H, bsize, *STORIES[3])
    brief(draw, COLS[2], ROWS[1], COL_W, ROW_H, bsize, *STORIES[4])
    brief(draw, COLS[0], ROWS[2], COL_W, ROW_H, bsize, *STORIES[5])
    brief(draw, COLS[1], ROWS[2], COL_W, ROW_H, bsize, *STORIES[6])
    date_panel(draw, COLS[2], ROWS[2], COL_W, ROW_H)

    # footer
    rule(draw, M, 966, W - M - 1, FAINT, 1)
    ff = font("sans", 9)
    draw_tracked(draw, (M, 974), "20 NOVEMBER 2026  /  WORLD NEWS IN ONE PAGE", ff, MUTED, 1.6)
    right = "EDITED FOR ONE PAGE"
    draw_tracked(draw, (W - M - text_width(draw, right, ff, 1.6), 974), right, ff, MUTED, 1.6)

    img.save(out, "PNG", optimize=True)
    print(f"wrote {out} {img.size[0]}x{img.size[1]} "
          f"{os.path.getsize(out)} bytes, brief size {bsize}px")


if __name__ == "__main__":
    main()
