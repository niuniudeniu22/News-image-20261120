"""Render entry.png: one newspaper front page for Friday 20 November 2026.

Run:  python build_entry.py
Out:  entry.png (1024x1024, PNG, well under 1 MiB)

The page is set like a broadsheet front page: a masthead, a lead ruling on the
left, six short briefs in the grid, and a date block. Everything is drawn with
Pillow, no network and no external assets.
"""

from __future__ import annotations

import os
import sys

from PIL import Image, ImageDraw, ImageFont

W = H = 1024
M = 36

PAPER = (243, 237, 225)
SHADE = (219, 208, 188)
INK = (20, 17, 14)
RED = (176, 42, 31)
RULE = (201, 191, 173)
MUTED = (92, 82, 68)
WHITE = (247, 242, 232)

FONT_DIRS = [r"C:\Windows\Fonts", "/usr/share/fonts/truetype/dejavu",
             "/System/Library/Fonts/Supplemental", "/Library/Fonts"]

# role -> candidate file names, best first
FONT_FILES = {
    "serif_bold": ["georgiab.ttf", "DejaVuSerif-Bold.ttf", "Times New Roman Bold.ttf", "timesbd.ttf"],
    "serif": ["georgia.ttf", "DejaVuSerif.ttf", "times.ttf"],
    "sans": ["segoeui.ttf", "DejaVuSans.ttf", "arial.ttf"],
    "sans_semibold": ["seguisb.ttf", "DejaVuSans-Bold.ttf", "arialbd.ttf"],
    "sans_bold": ["segoeuib.ttf", "DejaVuSans-Bold.ttf", "arialbd.ttf"],
}


def find_font_file(names: list[str]) -> str:
    for name in names:
        for folder in FONT_DIRS:
            path = os.path.join(folder, name)
            if os.path.isfile(path):
                return path
    raise SystemExit(f"no usable font for {names}; install one of them")


FONT_PATHS = {role: find_font_file(names) for role, names in FONT_FILES.items()}
_FONT_CACHE: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}


def font(role: str, size: int) -> ImageFont.FreeTypeFont:
    key = (role, size)
    if key not in _FONT_CACHE:
        _FONT_CACHE[key] = ImageFont.truetype(FONT_PATHS[role], size)
    return _FONT_CACHE[key]


# --- text measuring ---------------------------------------------------------

def tracked_width(draw: ImageDraw.ImageDraw, text: str, f: ImageFont.FreeTypeFont,
                  tracking: float) -> float:
    if not text:
        return 0.0
    return sum(draw.textlength(ch, font=f) for ch in text) + tracking * (len(text) - 1)


def draw_tracked(draw: ImageDraw.ImageDraw, xy: tuple[float, float], text: str,
                 f: ImageFont.FreeTypeFont, fill, tracking: float = 0.0) -> None:
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=f, fill=fill)
        x += draw.textlength(ch, font=f) + tracking


def wrap(draw: ImageDraw.ImageDraw, text: str, f: ImageFont.FreeTypeFont,
         max_width: float, tracking: float = 0.0) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        current = ""
        for word in paragraph.split():
            candidate = f"{current} {word}".strip()
            if tracked_width(draw, candidate, f, tracking) <= max_width or not current:
                current = candidate
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
    return lines


def fit_serif(draw: ImageDraw.ImageDraw, text: str, max_width: float, max_height: float,
              sizes: range, line_gap: float = 1.12, tracking: float = 0.0,
              role: str = "serif_bold") -> tuple[ImageFont.FreeTypeFont, list[str], float]:
    """Largest size whose wrapped block fits the box; smallest size as fallback."""
    chosen = None
    for size in sizes:
        f = font(role, size)
        lines = wrap(draw, text, f, max_width, tracking)
        lh = size * line_gap
        if all(tracked_width(draw, ln, f, tracking) <= max_width for ln in lines) \
                and len(lines) * lh <= max_height:
            chosen = (f, lines, lh)
            break
    if chosen is None:
        size = sizes[-1]
        f = font(role, size)
        lines = wrap(draw, text, f, max_width, tracking)
        chosen = (f, lines, size * line_gap)
    return chosen


# --- page furniture ---------------------------------------------------------

def paper_background() -> Image.Image:
    img = Image.new("RGB", (W, H), PAPER)
    # A soft, low-contrast vignette: enough to read as paper, cheap to compress.
    small = Image.new("L", (64, 64))
    px = small.load()
    for y in range(64):
        for x in range(64):
            dx = (x - 31.5) / 31.5
            dy = (y - 31.5) / 31.5
            r = min(1.0, (dx * dx + dy * dy) ** 0.5)
            px[x, y] = int(max(0.0, (r - 0.45) / 0.55) * 30)
    vig = small.resize((W, H), Image.BICUBIC)
    return Image.composite(Image.new("RGB", (W, H), SHADE), img, vig)


def kicker(draw: ImageDraw.ImageDraw, x: float, y: float, num: str, label: str) -> None:
    f_num = font("sans_bold", 12)
    f_lab = font("sans_semibold", 10)
    draw_tracked(draw, (x, y), num, f_num, RED, 1.2)
    nw = tracked_width(draw, num, f_num, 1.2)
    draw_tracked(draw, (x + nw + 9, y + 1), "/", f_num, RED, 0.0)
    draw_tracked(draw, (x + nw + 22, y + 2), label.upper(), f_lab, MUTED, 2.0)


# --- cells ------------------------------------------------------------------

def brief(draw, x, y, w, h, num, label, headline, deck) -> None:
    draw.rectangle([x, y, x + w - 1, y], fill=RULE)

    deck_f = font("sans", 14)
    deck_lines = wrap(draw, deck, deck_f, w)[:3]
    deck_lh = 17.5

    top_min = 11
    avail = h - 34 - len(deck_lines) * deck_lh - 12
    hf, lines, lh = fit_serif(draw, headline, w, avail,
                              range(27, 16, -1), line_gap=1.10)

    top = y + top_min

    kicker(draw, x, top, num, label)
    ty = top + 34
    for line in lines:
        draw.text((x, ty), line, font=hf, fill=INK)
        ty += lh
    ty += 8
    draw.rectangle([x, ty, x + 26, ty + 2], fill=RED)
    ty += 10
    for line in deck_lines:
        draw.text((x, ty), line, font=deck_f, fill=MUTED)
        ty += deck_lh


def lead(draw, x, y, w, h, num, label, headline, deck) -> None:
    draw.rectangle([x, y, x + w - 1, y + 3], fill=RED)
    kicker(draw, x, y + 16, num, label)

    deck_f = font("sans", 14)
    deck_lines = wrap(draw, deck, deck_f, w)[:4]
    deck_lh = 19
    deck_h = len(deck_lines) * deck_lh

    top = y + 44
    avail = h - 44 - deck_h - 22
    hf, lines, lh = fit_serif(draw, headline, w, avail,
                              range(58, 26, -2), line_gap=1.08)
    ty = top
    for line in lines:
        draw.text((x, ty), line, font=hf, fill=INK)
        ty += lh
    ty += 8
    draw.rectangle([x, ty, x + w - 1, ty + 1], fill=RULE)
    ty += 12
    for line in deck_lines:
        draw.text((x, ty), line, font=deck_f, fill=MUTED)
        ty += deck_lh


def date_block(draw, x, y, w, h) -> None:
    draw.rectangle([x, y, x + w - 1, y + h - 1], fill=INK)
    pad = 18
    f_top = font("sans_semibold", 10)
    draw_tracked(draw, (x + pad, y + 16), "FRIDAY", f_top, RED, 3.0)

    big = font("serif_bold", 92)
    draw.text((x + pad - 5, y + 30), "20", font=big, fill=WHITE)

    f_month = font("serif_bold", 24)
    draw.text((x + pad, y + 130), "NOV 2026", font=f_month, fill=WHITE)

    draw.rectangle([x + pad, y + h - 46, x + w - pad, y + h - 45], fill=RED)
    f_foot = font("sans_semibold", 9)
    draw_tracked(draw, (x + pad, y + h - 36), "SEVEN STORIES", f_foot, WHITE, 2.0)
    draw_tracked(draw, (x + pad, y + h - 22), "ONE PAGE", f_foot, RED, 2.0)


# --- content ----------------------------------------------------------------

STORIES = [
    ("01", "World",
     "ICJ: Myanmar committed genocide against Rohingya",
     "The court's ruling closes a case\nyears in the making."),
    ("02", "Asia-Pacific",
     "Trump, Xi and Putin in first three-way summit as APEC closes in Shenzhen",
     "Three leaders at one table as the summit ends."),
    ("03", "Markets",
     "Anthropic IPO debut",
     "The company's shares begin trading in public."),
    ("04", "Climate",
     "COP31 ends, fossil-fuel transition text cut",
     "Talks close with the transition text weakened."),
    ("05", "Europe",
     "Putin rules out sea and energy truce after Crimea Bridge hit again",
     "Moscow rules out a truce at sea and on energy."),
    ("06", "Middle East",
     "Iran steps up Hormuz tanker attacks",
     "Tanker attacks in the strait are stepping up."),
    ("07", "Middle East",
     "Gaza: 65,000 tents wait at border",
     "Shelters wait at the border, nowhere to go."),
]


def main() -> None:
    out = sys.argv[1] if len(sys.argv) > 1 else "entry.png"
    img = paper_background()
    draw = ImageDraw.Draw(img)

    # masthead
    draw.rectangle([M, 30, W - M - 1, 30], fill=RULE)
    title = "WORLD NEWS - 20 NOV 2026"
    tf, tlines, _ = fit_serif(draw, title, W - 2 * M - 18, 80, range(76, 40, -2),
                              line_gap=1.0, tracking=-1.0)
    tw = tracked_width(draw, title, tf, -1.0)
    draw_tracked(draw, ((W - tw) / 2, 44), title, tf, INK, -1.0)

    draw.rectangle([M, 128, W - M - 1, 131], fill=INK)
    draw.rectangle([M, 137, W - M - 1, 137], fill=RULE)

    f_strip = font("sans_semibold", 9)
    draw_tracked(draw, (M, 149), "THE DAY IN SEVEN STORIES", f_strip, MUTED, 2.4)
    right = "LATE EDITION / PAGE 01"
    rw = tracked_width(draw, right, f_strip, 2.4)
    draw_tracked(draw, (W - M - rw, 149), right, f_strip, MUTED, 2.4)

    # grid
    col_w, gut = 300, 26
    cols = [M, M + col_w + gut, M + 2 * (col_w + gut)]
    rows = [180, 458, 736]
    row_h, row_gap = 232, 46

    # column rules: the page is set in three columns
    for boundary in (cols[1] - gut // 2, cols[2] - gut // 2):
        draw.rectangle([boundary, rows[0], boundary, rows[2] + row_h], fill=RULE)

    lead(draw, cols[0], rows[0], col_w, row_h * 2 + row_gap, *STORIES[0])
    brief(draw, cols[1], rows[0], col_w, row_h, *STORIES[1])
    brief(draw, cols[2], rows[0], col_w, row_h, *STORIES[2])
    brief(draw, cols[1], rows[1], col_w, row_h, *STORIES[3])
    brief(draw, cols[2], rows[1], col_w, row_h, *STORIES[4])
    brief(draw, cols[0], rows[2], col_w, row_h, *STORIES[5])
    brief(draw, cols[1], rows[2], col_w, row_h, *STORIES[6])
    date_block(draw, cols[2], rows[2], col_w, row_h)

    # footer
    draw.rectangle([M, 982, W - M - 1, 982], fill=RULE)
    f_foot = font("sans", 9)
    draw_tracked(draw, (M, 991), "20 NOVEMBER 2026 / WORLD NEWS IN ONE PAGE", f_foot, MUTED, 1.6)
    right = "EDITED FOR ONE PAGE"
    rw = tracked_width(draw, right, f_foot, 1.6)
    draw_tracked(draw, (W - M - rw, 991), right, f_foot, MUTED, 1.6)

    img.save(out, "PNG", optimize=True)
    print(f"wrote {out} {img.size[0]}x{img.size[1]} {os.path.getsize(out)} bytes")


if __name__ == "__main__":
    main()
