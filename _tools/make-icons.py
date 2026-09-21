"""Generate icon renditions from the master logo.

The master is 3508x3508 and was being served straight into a 68px nav slot on
every page, which is 179 KB decoded at full resolution for a mark the size of a
thumbnail. This writes the sizes the site actually uses.

Run:  python _tools/make-icons.py
"""
import os
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow is required:  pip install Pillow")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGES = os.path.join(ROOT, "assets", "images")
MASTER = os.path.join(IMAGES, "logo.png")

# name -> pixel size. The nav renders the mark at 68 CSS px, so 136 covers 2x.
RENDITIONS = {
    "favicon-32.png": 32,
    "logo-136.png": 136,
    "apple-touch-icon.png": 180,
    "icon-192.png": 192,
    "icon-512.png": 512,
}


def main():
    if not os.path.isfile(MASTER):
        sys.exit(f"master not found: {MASTER}")

    master = Image.open(MASTER)
    if master.mode != "RGBA":
        master = master.convert("RGBA")

    print(f"master  {master.size[0]}x{master.size[1]}  "
          f"{os.path.getsize(MASTER) / 1024:.0f} KB")

    total = 0
    for name, size in sorted(RENDITIONS.items(), key=lambda kv: kv[1]):
        out = os.path.join(IMAGES, name)
        img = master.resize((size, size), Image.LANCZOS)
        img.save(out, "PNG", optimize=True)
        kb = os.path.getsize(out) / 1024
        total += kb
        print(f"  {name:24} {size:>4}px  {kb:6.1f} KB")

    print(f"\n{len(RENDITIONS)} renditions, {total:.0f} KB total")


if __name__ == "__main__":
    main()
