"""Grade, resize, encode and place the site's photography.

One tool owns the whole path from a master in _src/photos/ to the <picture>
block in the page, because the output filenames carry a content hash and
hand-written markup would break on every rebuild. Same bargain as
_tools/chrome.py, which owns the nav, footer, head assets and closing CTA for
the same reason, and the regions are delimited the same way: explicit HTML
comments, never tag matching.

The masters are NOT in the repo. They are 18.6 MB of PNG in _src/photos/, which
.gitignore and .assetsignore both exclude. What ships is assets/photos/, which
is about a tenth of that. Anyone rebuilding needs the masters; anyone serving
the site does not.

Run:  python _tools/photos.py           grade, encode, write markup
      python _tools/photos.py --check   exit 1 if anything is out of date
"""
import hashlib
import io
import json
import os
import re
import sys

try:
    from PIL import Image, ImageStat
except ImportError:
    sys.exit("Pillow is required:  pip install Pillow")

from PIL import features
for _mod in ("avif", "webp"):
    if not features.check_module(_mod):
        sys.exit(f"Pillow is built without {_mod}; this tool emits both formats")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "_src", "photos")
OUT = os.path.join(ROOT, "assets", "photos")
MANIFEST = os.path.join(OUT, "manifest.json")

# ── The grade ────────────────────────────────────────────────────────────────
#
# A "light unifying pass": the set should read as one shoot without any frame
# looking treated.
#
# Measured across all eleven masters on 2026-10-14, which is what these
# constants come from:
#
#   black point   0 .. 7      median 4
#   white point   183 .. 250  median 237
#   R/B ratio     0.623 .. 1.335   median 1.102
#   mean luma     64.8 .. 121.4    median 82.9
#
# Two things the measurement ruled out, recorded because the obvious version of
# this function does both and wrecks the two best frames:
#
#   * NO common white point. twilight-van tops out at 183 because it is a night
#     scene. Stretching it to 237 blows out the dusk sky that makes it the
#     homepage hero.
#   * NO white-balance normalisation. solar-rooftop sits at R/B 0.623 because
#     it is a blue sky at noon and founder sits at 1.335 because it is tungsten
#     and neon at night. Pulling both to 1.102 turns the sky grey. These images
#     are SUPPOSED to disagree; they are different times of day.
#
# So only the black point is matched outright. Warmth and midtone are pulled a
# capped fraction of the way to the median, which tightens the set without
# neutralising anything.
BLACK_TARGET = 4.0      # every frame lands its 0.5th percentile here
WARM_MEDIAN = 1.102     # measured set median of mean(R)/mean(B)
WARM_PULL = 0.15        # fraction of the distance to WARM_MEDIAN
LUMA_MEDIAN = 82.9      # measured set median of mean luminance
LUMA_PULL = 0.10
GAIN_CLAMP = 0.08       # no channel gain may exceed +/- 8 percent

# ── The slots ────────────────────────────────────────────────────────────────
#
# kind decides the widths, the sizes attribute and the byte ceiling.
WIDTHS = {"hero": (640, 1024, 1600), "inline": (480, 800, 1200), "portrait": (280, 560)}
SIZES = {
    "hero-bleed": "100vw",
    "hero-split": "(min-width: 961px) 52vw, 100vw",
    "plate": "100vw",
    "inline": "(min-width: 961px) 46vw, 100vw",
    "portrait": "(min-width: 961px) 220px, 160px",
}
# Largest-width AVIF ceiling per kind, in KB. Enforced by the gate, not hoped for.
CEILING = {"hero": 140, "inline": 90, "portrait": 40}


class Slot:
    def __init__(self, region, src, kind, shape, page, alt, caption,
                 crop=None, focus=0.5, lcp=False):
        self.region = region      # the marker name, unique across the site
        self.src = src            # filename in _src/photos/
        self.kind = kind          # hero | inline | portrait  -> widths, ceiling
        self.shape = shape        # key into SIZES -> the sizes attribute
        self.page = page
        self.alt = alt            # what it shows, for a screen reader
        self.caption = caption    # what it argues, visible under the rule
        self.crop = crop          # (l, t, r, b) on the master, before anything
        self.focus = focus        # vertical centre of the crop, 0 top 1 bottom
        self.lcp = lcp            # the page's hero: preloaded, never lazy

    @property
    def slug(self):
        return self.region


# Captions carry the argument; they never report a result. The site has no
# client results and says so in its own footer, so a caption claiming one would
# contradict the page it sits on.
SLOTS = [
    Slot("index-hero", "twilight-van.png", "hero", "hero-bleed", "index.html",
         "A technician taking tools from the open back of a work van on a "
         "driveway at dusk, with a lit house behind him.",
         "The call that comes in after six is the one that decides who gets "
         "the job.", lcp=True),

    Slot("index-problem", "homeowner-garage.png", "inline", "inline", "index.html",
         "A homeowner standing beside a water heater in his garage, one hand "
         "on his head, looking at his phone.",
         "He has already filled in three forms. Whoever answers first is the "
         "one he ends up talking to."),

    Slot("index-sequence", "message-kitchen.png", "inline", "inline", "index.html",
         "A pair of hands holding a phone in a dim kitchen, a message bubble "
         "lighting the screen.",
         "A reply inside a minute still reads as a person rather than a "
         "system."),

    Slot("index-operate", "office-calendar.png", "inline", "inline", "index.html",
         "An office manager at a desk looking at a week view on a monitor, "
         "full of colour-coded appointments.",
         "Appointments land in the calendar the office already runs on."),

    Slot("hvac-hero", "rooftop-hvac.png", "hero", "hero-split", "hvac.html",
         "An HVAC technician crouched beside a rooftop condenser at sunset, "
         "reading a set of manifold gauges.",
         "A no-heat call at six in the evening, answered before they work "
         "down the list.", lcp=True),

    Slot("solar-hero", "solar-rooftop.png", "hero", "hero-split", "solar.html",
         "Two harnessed installers setting a solar panel onto roof rails "
         "under a clear sky.",
         "A quote request that went to three other installers in the same "
         "sitting.", lcp=True),

    Slot("solar-compare", "homeowner-tablet.png", "inline", "inline", "solar.html",
         "A homeowner sitting on a sofa in the evening, reading on a tablet.",
         "Most of the decision happens in the weeks after the first reply, "
         "not during it."),

    Slot("contact-hero", "handshake-door.png", "hero", "hero-split", "contact.html",
         "A technician and a homeowner shaking hands in an open front "
         "doorway, a work van at the kerb.",
         "The job that got booked because somebody answered.", lcp=True),

    Slot("about-plate", "van-dashboard.png", "hero", "plate", "about.html",
         "A phone face down on the dashboard of a work truck at golden hour, "
         "beside a clipboard of job sheets.",
         "The phone stays in the van. Nothing was neglected; the work and the "
         "enquiries simply happened at the same time.", lcp=True),

    Slot("services-web", "phone-toolbox.png", "inline", "inline", "services.html",
         "A phone propped against a toolbox in a truck bed showing a "
         "contractor website, a technician working at a condenser behind.",
         "Most homeowners meet the company on a phone before they meet "
         "anybody from it."),

    # Measured, not guessed: the master is a 739x1600 phone screenshot whose
    # letterbox bars occupy rows 0..305 and 1585..1599, leaving 739x1279.
    #
    # The crop is already 4:5 (460x575) so the portrait rule below is a no-op
    # on it. It is placed by hand rather than centred because this frame is an
    # evening event photograph: centring it keeps an orange inflatable and a
    # lit bar in shot, and the whole job here is to leave as little of the
    # venue in the frame as the resolution allows.
    Slot("about-founder", "founder.jpeg", "portrait", "portrait", "about.html",
         "Deni, founder of ProAffy.",
         "Deni, Founder",
         crop=(150, 420, 610, 995)),
]

MARKERS = {s.region: (f"  <!-- photo:{s.region} -->",
                      f"  <!-- /photo:{s.region} -->") for s in SLOTS}


# ── Grading ──────────────────────────────────────────────────────────────────

def percentile(hist, total, p):
    want, acc = total * p, 0
    for value, count in enumerate(hist):
        acc += count
        if acc >= want:
            return float(value)
    return 255.0


def analyse(im):
    grey = im.convert("L")
    hist = grey.histogram()
    total = sum(hist)
    r, g, b = ImageStat.Stat(im).mean
    return {
        "black": percentile(hist, total, 0.005),
        "white": percentile(hist, total, 0.995),
        "r": r, "g": g, "b": b,
        "luma": 0.299 * r + 0.587 * g + 0.114 * b,
    }


def clamp_gain(gain):
    return max(1.0 - GAIN_CLAMP, min(1.0 + GAIN_CLAMP, gain))


def grade(im):
    """Match the black point outright; pull warmth and midtone a capped way."""
    before = analyse(im)

    # Black point: subtract what is there, add back the shared target. The white
    # point is deliberately untouched, see the note at the top of this file.
    lift = BLACK_TARGET - before["black"]

    # Warmth: a capped pull of R and B toward the set median R/B, in opposite
    # directions so overall exposure does not move. G is never touched, which
    # is what keeps skin where it is.
    ratio = before["r"] / before["b"] if before["b"] else 1.0
    target = ratio + (WARM_MEDIAN - ratio) * WARM_PULL
    adjust = (target / ratio) ** 0.5 if ratio else 1.0
    gain_r, gain_b = clamp_gain(adjust), clamp_gain(1.0 / adjust)

    # Midtone: a capped pull toward the set median luminance, as a gamma so the
    # ends stay put and only the middle moves.
    want_luma = before["luma"] + (LUMA_MEDIAN - before["luma"]) * LUMA_PULL
    gamma = 1.0
    if before["luma"] > 1 and want_luma > 1:
        import math
        gamma = math.log(want_luma / 255.0) / math.log(before["luma"] / 255.0)
        gamma = max(0.92, min(1.08, gamma))

    def lut(gain):
        table = []
        for v in range(256):
            x = (v + lift) * gain
            x = 255.0 * ((max(x, 0.0) / 255.0) ** gamma)
            table.append(int(max(0, min(255, round(x)))))
        return table

    out = im.point(lut(gain_r) + lut(1.0) + lut(gain_b))
    return out, before, analyse(out), {
        "lift": lift, "gain_r": gain_r, "gain_b": gain_b, "gamma": gamma}


# ── Deriving ─────────────────────────────────────────────────────────────────

def encode(im, fmt):
    buf = io.BytesIO()
    if fmt == "avif":
        im.save(buf, format="AVIF", quality=55, speed=4)
    else:
        im.save(buf, format="WEBP", quality=78, method=6)
    return buf.getvalue()


def derive(slot):
    """Return [(filename, bytes)], plus the intrinsic size of the fallback."""
    master = Image.open(os.path.join(SRC, slot.src)).convert("RGB")
    if slot.crop:
        master = master.crop(slot.crop)

    if slot.kind == "portrait":
        # 4:5 around the head, placed by focus rather than centred, because a
        # centred crop of a standing figure cuts the face off.
        want_h = int(master.width * 5 / 4)
        if want_h <= master.height:
            top = int((master.height - want_h) * slot.focus)
            master = master.crop((0, top, master.width, top + want_h))

    toned, before, after, moves = grade(master)
    files, fallback = [], None

    for width in WIDTHS[slot.kind]:
        if width > toned.width:
            width = toned.width
        height = round(toned.height * width / toned.width)
        resized = toned.resize((width, height), Image.LANCZOS)
        for fmt in ("avif", "webp"):
            blob = encode(resized, fmt)
            digest = hashlib.sha256(blob).hexdigest()[:8]
            files.append({
                "name": f"{slot.slug}.{digest}-{width}.{fmt}",
                "blob": blob, "width": width, "height": height, "fmt": fmt,
            })
        if fallback is None or abs(width - 800) < abs(fallback - 800):
            fallback = width

    return files, fallback, before, after, moves


# ── Markup ───────────────────────────────────────────────────────────────────

def srcset(entries, fmt):
    return ", ".join(
        f"/assets/photos/{e['name']} {e['width']}w"
        for e in entries if e["fmt"] == fmt)


def picture_block(slot, entries, fallback):
    base = next(e for e in entries if e["fmt"] == "webp" and e["width"] == fallback)
    sizes = SIZES[slot.shape]
    loading = ("" if slot.lcp else '\n        loading="lazy"')
    priority = ('\n        fetchpriority="high"' if slot.lcp else "")
    return f"""  <!-- photo:{slot.region} -->
  <figure class="photo photo--{slot.shape}">
    <picture>
      <source type="image/avif" sizes="{sizes}"
              srcset="{srcset(entries, 'avif')}" />
      <source type="image/webp" sizes="{sizes}"
              srcset="{srcset(entries, 'webp')}" />
      <img src="/assets/photos/{base['name']}"
        alt="{slot.alt}"
        width="{base['width']}" height="{base['height']}"
        decoding="async"{loading}{priority} />
    </picture>
    <figcaption class="photo__caption">{slot.caption}</figcaption>
  </figure>
  <!-- /photo:{slot.region} -->"""


def preload_link(slot, entries):
    """The hero is the LCP element, so the browser is told before it parses."""
    sizes = SIZES[slot.shape]
    return ('  <link rel="preload" as="image" type="image/avif" '
            f'imagesrcset="{srcset(entries, "avif")}" '
            f'imagesizes="{sizes}" />')


def fill_regions(text, region, block):
    open_m, close_m = MARKERS[region]
    start = text.find(open_m)
    if start == -1:
        return None
    end = text.find(close_m, start)
    if end == -1:
        return None
    return text[:start] + block + text[end + len(close_m):]


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    check = "--check" in sys.argv
    if not os.path.isdir(SRC):
        sys.exit(f"no masters at {os.path.relpath(SRC, ROOT)}")
    os.makedirs(OUT, exist_ok=True)

    manifest, wanted, total = {}, set(), 0
    problems, written = [], []

    print(f"grading {len(SLOTS)} slots from {os.path.relpath(SRC, ROOT)}")
    for slot in SLOTS:
        path = os.path.join(SRC, slot.src)
        if not os.path.isfile(path):
            problems.append(f"missing master: {slot.src}")
            continue

        entries, fallback, before, after, moves = derive(slot)
        biggest = max((e for e in entries if e["fmt"] == "avif"),
                      key=lambda e: e["width"])
        kb = len(biggest["blob"]) / 1024
        total += sum(len(e["blob"]) for e in entries)

        flag = ""
        if kb > CEILING[slot.kind]:
            flag = f"  OVER the {CEILING[slot.kind]} KB ceiling"
            problems.append(
                f"{slot.region}: largest AVIF is {kb:.0f} KB, ceiling is "
                f"{CEILING[slot.kind]} KB")
        print(f"  {slot.region:16} black {before['black']:5.1f} -> "
              f"{after['black']:4.1f}   R/B {before['r'] / before['b']:5.3f} -> "
              f"{after['r'] / after['b']:5.3f}   gamma {moves['gamma']:.3f}   "
              f"{biggest['width']}px avif {kb:5.1f} KB{flag}")

        for e in entries:
            dest = os.path.join(OUT, e["name"])
            wanted.add(e["name"])
            if not os.path.isfile(dest) or os.path.getsize(dest) != len(e["blob"]):
                if check:
                    problems.append(f"{e['name']} is missing or stale")
                else:
                    with open(dest, "wb") as fh:
                        fh.write(e["blob"])
                    written.append(e["name"])

        manifest[slot.region] = {
            "page": slot.page, "kind": slot.kind, "shape": slot.shape,
            # The sizes string is carried here, not looked up, so _tools/
            # chrome.py can write the hero preload without importing this
            # module and inheriting its dependency on Pillow.
            "sizes": SIZES[slot.shape],
            "lcp": slot.lcp, "alt": slot.alt, "caption": slot.caption,
            "fallback": fallback,
            "files": [{k: e[k] for k in ("name", "width", "height", "fmt")}
                      for e in entries],
        }

        block = picture_block(slot, entries, fallback)
        page_path = os.path.join(ROOT, slot.page)
        if os.path.isfile(page_path):
            text = io.open(page_path, encoding="utf-8").read()
            new = fill_regions(text, slot.region, block)
            if new is None:
                problems.append(
                    f"{slot.page}: no markers for photo:{slot.region}; add "
                    f"<!-- photo:{slot.region} --> and its closing marker")
            elif new != text:
                if check:
                    problems.append(f"{slot.page}: photo:{slot.region} is out of date")
                else:
                    io.open(page_path, "w", encoding="utf-8",
                            newline="\n").write(new)
                    written.append(f"{slot.page}:{slot.region}")

    # Orphans. A regrade changes every hash, and without this the old files sit
    # in the repo forever, served to nobody and counted by every size audit.
    orphans = [f for f in os.listdir(OUT)
               if f not in wanted and f != "manifest.json"]
    for f in orphans:
        if check:
            problems.append(f"orphan: {f}")
        else:
            os.remove(os.path.join(OUT, f))
            written.append(f"removed {f}")

    body = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    current = io.open(MANIFEST, encoding="utf-8").read() if os.path.isfile(MANIFEST) else None
    if current != body:
        if check:
            problems.append("manifest.json is out of date")
        else:
            io.open(MANIFEST, "w", encoding="utf-8", newline="\n").write(body)
            written.append("manifest.json")

    print(f"\n{len(wanted)} derivatives, {total / 1024 / 1024:.2f} MB on disk")
    if orphans and not check:
        print(f"pruned {len(orphans)} orphaned file(s)")
    if problems:
        print(f"\n{len(problems)} problem(s):")
        for p in problems[:20]:
            print(f"  {p}")
        return 1
    if check:
        print("photos are current")
    else:
        print(f"wrote {len(written)} file(s)" if written else "no change")
    return 0


if __name__ == "__main__":
    sys.exit(main())
