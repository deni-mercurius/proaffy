"""Draw the Open Graph share image from the site's own design system.

The old one baked "HVAC growth partner" into pixels, so a vertical change could
not reach it, and it was set in a face the site does not use. This draws it in
the real palette with the real faces, which means a link preview and the page it
opens look like the same company.

Run:  python _tools/make-og.py
"""
import os
import sys

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit("Pillow is required:  pip install Pillow")

try:
    from fontTools.ttLib import TTFont
except ImportError:
    sys.exit("fontTools is required:  pip install fonttools brotli")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "assets", "fonts")
OUT = os.path.join(ROOT, "assets", "images", "og-image.jpg")

W, H = 1200, 630
BG = (255, 255, 255)
INK = (20, 18, 32)
VIOLET = (80, 16, 208)
TEXT2 = (86, 83, 107)

HEADLINE = "Every lead gets a real reply in 60 seconds"
# On the scrimmed photograph these have to be light, not the page palette.
EYEBROW_INK = (190, 170, 255)
FOOT_INK = (214, 208, 232)
EYEBROW = "PROAFFY  /  HVAC AND SOLAR"
FOOT = "proaffy.com"


def face(woff2, size, cache={}):
    """PIL cannot read WOFF2, so decompress to a TTF beside it once."""
    ttf = os.path.join(FONTS, woff2.replace(".woff2", ".ttf"))
    if ttf not in cache:
        if not os.path.isfile(ttf):
            f = TTFont(os.path.join(FONTS, woff2))
            f.flavor = None
            f.save(ttf)
        cache[ttf] = True
    return ImageFont.truetype(ttf, size)


def wrap(draw, text, font, max_w):
    words, lines, line = text.split(), [], ""
    for w in words:
        trial = (line + " " + w).strip()
        if draw.textlength(trial, font=font) <= max_w:
            line = trial
        else:
            lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines


def backdrop():
    """The homepage hero photograph, cropped to the card and scrimmed.

    The share card and the page it opens used to share a palette and nothing
    else. They now share the actual picture, which is the only version of
    "looks like the same company" that survives being posted somewhere.

    Falls back to flat paper if the master is absent, because this tool must
    still run on a checkout that has no _src/ (it is gitignored).
    """
    master = os.path.join(ROOT, "_src", "photos", "twilight-van.png")
    if not os.path.isfile(master):
        return Image.new("RGB", (W, H), BG), INK

    photo = Image.open(master).convert("RGB")
    scale = max(W / photo.width, H / photo.height)
    photo = photo.resize((round(photo.width * scale), round(photo.height * scale)),
                         Image.LANCZOS)
    left = (photo.width - W) // 2
    photo = photo.crop((left, 0, left + W, H))

    # The same violet-black scrim the hero uses, for the same reason: the
    # headline has to stay legible over a photograph.
    scrim = Image.new("RGB", (W, H), (10, 6, 28))
    photo = Image.blend(photo, scrim, 0.72)
    return photo, (255, 255, 255)


def main():
    img, ink = backdrop()
    d = ImageDraw.Draw(img)

    pad = 84
    mono = face("ibm-plex-sans-600.woff2", 22)
    sans = face("ibm-plex-sans-600.woff2", 68)
    small = face("ibm-plex-sans-400.woff2", 24)

    # Eyebrow, tracked out by hand since PIL has no letter-spacing.
    x = pad
    for ch in EYEBROW:
        d.text((x, pad), ch, font=mono, fill=EYEBROW_INK)
        x += d.textlength(ch, font=mono) + 3

    y = pad + 92
    for line in wrap(d, HEADLINE, sans, W - pad * 2):
        d.text((pad, y), line, font=sans, fill=ink)
        y += 84

    # The measured rule: solid, exactly as wide as what it underlines.
    rule_w = 240
    d.rectangle([pad, y + 26, pad + rule_w, y + 32], fill=VIOLET)

    d.text((pad, y + 56), FOOT, font=small, fill=FOOT_INK)

    # One ink band at the foot, the same device the pages use.
    d.rectangle([0, H - 26, W, H], fill=VIOLET)

    # JPEG, not PNG. The card is a photograph now, and PNG wrote 547 KB of
    # it; a crawler fetching that on every share is the whole cost of this
    # change for no visible gain. Quality 84 lands under 100 KB.
    img.save(OUT, "JPEG", quality=84, optimize=True, progressive=True)
    kb = os.path.getsize(OUT) / 1024
    print(f"  wrote {os.path.relpath(OUT, ROOT)}  {W}x{H}  {kb:.0f} KB")


if __name__ == "__main__":
    main()
