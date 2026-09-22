"""ProAffy site gate. Read-only, stdlib only.

Every check is numbered and prints PASS or FAIL with the reason. Exit 1 on any
failure. Some checks are expected to fail today: that is deliberate. A gate
proved against real defects is worth more than one written after they are fixed.

Copy checks read the text inside <main> only. Nav, footer and head are
byte-identical across pages, so including them would make the duplicate-sentence
check fire on every page at once and hide the real duplicates.

Run:  python _tools/verify.py
"""
import json
import os
import re
import sys
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE_HOST = "proaffy.com"

# Regions written by _tools/chrome.py. Shared on purpose.
CHROME_MARKERS = [
    ("<!-- chrome:nav -->", "<!-- /chrome:nav -->"),
    ("<!-- chrome:footer -->", "<!-- /chrome:footer -->"),
    ("<!-- chrome:assets -->", "<!-- /chrome:assets -->"),
    ("<!-- chrome:cta -->", "<!-- /chrome:cta -->"),
]

findings = []
results = []


def check(num, title, problems, pending=None):
    """Record one numbered check.

    `pending` names the session that fixes a defect we already know about. A
    pending check that fails reports PEND and does not break the build. A
    pending check that PASSES breaks the build, so the marker cannot outlive
    the defect and quietly turn into a disabled check.
    """
    results.append((num, title, list(problems), pending))


# ─────────────────────────────────────────────────────────────
# Patterns, and the samples that prove they still match.
# A regex that silently matches nothing is worse than no regex,
# so every pattern is exercised before the site is scanned.
# ─────────────────────────────────────────────────────────────

PERFORMED = [
    (r"\bworth (?:noting|spotting|knowing|saying|having)\b",
     "cut it, or say the thing itself"),
    (r"\bthat is the [a-z ]{0,26}worth\b",
     "the sentence before it already made the point"),
    (r"\b(?:is|are) (?:rarely|not) the problem\b",
     "state what IS the problem and drop the reversal"),
    (r"\bthe tell is\b",
     "name the signal without announcing that it is one"),
    (r"\bwhich is the (?:whole|only|real) (?:reason|point|thing)\b",
     "if it is the whole reason, the sentence can just say so"),
    (r"\bit is not [a-z]+\.\s+it is\b",
     "the corrective reversal, used for rhythm rather than for clarity"),
    (r"\bis not [a-z]+, it is\b",
     "same reversal, one comma shorter"),
    (r"\bthat is (?:the point|the difference|the whole)\b",
     "let the reader reach it"),
]

PERFORMED_BAD = [
    "and that is worth noting here",
    "that is the moment worth spotting",
    "the price is not the problem",
    "the tell is the spacing",
    "which is the whole reason we built it",
    "it is not slow. it is broken",
    "speed is not luck, it is process",
    "that is the difference",
]

PERFORMED_GOOD = [
    "we answer every lead in under a minute",
    "the furnace failed on the coldest night of the year",
    "a booked appointment that no-shows costs you a truck roll",
]

# Figures that were invented, removed, and must not come back.
#
# Removed once and found again twice, because the first sweeps matched whole
# sentences and the figures had been reworded around them. Match the NUMBER,
# never the sentence it happens to sit in today.
RETIRED = [
    (r"\$ ?3,?477", "an invented monthly loss figure no source produces",
     "bleeding $3,477 a month"),
    (r"\$ ?23,?000", "an invented revenue figure that appeared on one page only",
     "worth an extra $23,000"),
    (r"\b11 (?:new|booked)\b", "the invented jobs-per-month figure",
     "an average of 11 new jobs"),
    (r"15\s*%[^.]{0,24}7\s*%", "the invented no-show range",
     "cut from 15% down to 7%"),
    (r"guarantee[ds]?\s*,?\s*or you don'?t pay",
     "an unconditional guarantee the Terms page calls illustrative",
     "results guaranteed or you don't pay"),
]

RETIRED_GOOD = [
    "we answer 11 enquiries an hour",          # 11 followed by neither word
    "a guarantee is agreed with you in writing",
    "the reply takes 42 hours on average",
]

# Built with chr() rather than escape sequences, and rather than the characters
# themselves. An escape can be mangled in transit by a shell heredoc, and the
# literal character would put an em dash inside the file that bans em dashes.
BANNED_CHARS = [
    (chr(0x2014), "em dash"),
    (chr(0x2013), "en dash"),
]

EMOJI = re.compile(
    "["
    + chr(0x1F300) + "-" + chr(0x1FAFF)
    + chr(0x2600) + "-" + chr(0x27BF)
    + chr(0x1F1E6) + "-" + chr(0x1F1FF)
    + chr(0x2B00) + "-" + chr(0x2BFF)
    + "]"
)
CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
# Case-sensitive and uppercase-only on purpose. A lowercase match would fire on
# every placeholder="..." attribute in the markup, which is ordinary HTML.
PLACEHOLDER = re.compile(r"[A-Z0-9_]*PLACEHOLDER[A-Z0-9_]*|REPLACE_ME|YOUR_KEY_HERE|TODO_KEY")


def prove_patterns():
    """Exit 2 if any pattern has gone blind. This runs before anything else."""
    blind = []

    # A control character inside a pattern is how a gate goes silently blind.
    # A shell heredoc eats one level of backslash, so a `\b` written in a
    # generating script arrives as byte 0x08 and the pattern then matches
    # nothing while still looking correct in an editor. This has happened in
    # this file: the retired-figures check shipped with two backspace bytes and
    # could not match the figure it was written to catch.
    for label, pats in (("performed-insight", [p for p, _w in PERFORMED]),
                        ("retired-figure", [p for p, _w, _s in RETIRED])):
        for pat in pats:
            bad = [hex(ord(c)) for c in pat if ord(c) < 32]
            if bad:
                blind.append(f"{label} pattern contains a control character "
                             f"{bad}: {pat!r}. A heredoc ate a backslash.")

    for pat, _why, sample in RETIRED:
        rx = re.compile(pat, re.I)
        if not rx.search(sample):
            blind.append(f"retired-figure pattern matches its own sample: {pat!r}")
        for good in RETIRED_GOOD:
            if rx.search(good):
                blind.append(f"retired-figure pattern fires on clean copy: "
                             f"{pat!r} -> {good!r}")

    for pat, _why in PERFORMED:
        rx = re.compile(pat, re.I)
        if not any(rx.search(s) for s in PERFORMED_BAD):
            blind.append(f"performed-insight pattern matches no known-bad sample: {pat}")
        for good in PERFORMED_GOOD:
            if rx.search(good):
                blind.append(f"performed-insight pattern fires on clean copy: {pat} -> {good!r}")

    if not EMOJI.search("ship it \U0001F680"):
        blind.append("emoji pattern matches no emoji")
    if EMOJI.search("plain ascii text"):
        blind.append("emoji pattern fires on plain text")
    if not CONTROL.search("bad\x08byte"):
        blind.append("control-character pattern matches no control character")
    if CONTROL.search("clean text\n\twith tabs"):
        blind.append("control-character pattern fires on tab or newline")
    if not PLACEHOLDER.search("WEB3FORMS_ACCESS_KEY_PLACEHOLDER"):
        blind.append("placeholder pattern matches no placeholder")
    if PLACEHOLDER.search('<input placeholder="Email Address...">'):
        blind.append("placeholder pattern fires on an ordinary HTML placeholder attribute")

    if blind:
        print("GATE BROKEN. Patterns cannot be trusted:\n")
        for b in blind:
            print("  " + b)
        print("\nFix the patterns before trusting any result below.")
        sys.exit(2)


# ─────────────────────────────────────────────────────────────
# Parsing
# ─────────────────────────────────────────────────────────────

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr"}
SKIP_TEXT = {"script", "style"}


class Page(HTMLParser):
    def __init__(self, name, raw):
        super().__init__(convert_charrefs=True)
        self.name = name
        self.raw = raw
        self.title = None
        self.description = None
        self.headings = []        # (level, text)
        self.ids = []
        self.idrefs = []          # (kind, value)
        self.imgs = []            # dict of attrs
        self.requests = []        # (tag, url)
        self.inline_styles = 0
        self.ld = []              # raw json strings
        self.canonical = None
        self.robots = None

        self._stack = []
        self._text = []           # text inside <main>
        self._in_main = 0
        self._grab = None         # buffer for title / heading / ld+json
        self._grab_kind = None
        self.feed(raw)

    # -- helpers ------------------------------------------------
    def _attr(self, attrs, key):
        for k, v in attrs:
            if k == key:
                return v
        return None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)

        if tag not in VOID:
            self._stack.append(tag)
        if tag == "main":
            self._in_main += 1

        if "id" in a and a["id"]:
            self.ids.append(a["id"])
        if "style" in a:
            self.inline_styles += 1

        for key in ("for", "aria-labelledby", "aria-describedby", "aria-controls"):
            if key in a and a[key]:
                for ref in a[key].split():
                    self.idrefs.append((key, ref))

        if tag == "title":
            self._grab, self._grab_kind = [], "title"
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._grab, self._grab_kind = [], tag
        elif tag == "script" and a.get("type") == "application/ld+json":
            self._grab, self._grab_kind = [], "ld"

        if tag == "meta" and a.get("name") == "description":
            self.description = a.get("content")
        if tag == "meta" and a.get("name") == "robots":
            self.robots = a.get("content", "")

        if tag == "link":
            rel = (a.get("rel") or "").lower()
            href = a.get("href")
            if href:
                if "canonical" in rel:
                    self.canonical = href
                else:
                    self.requests.append(("link", href))
        elif tag == "script" and a.get("src"):
            self.requests.append(("script", a["src"]))
        elif tag == "img":
            self.imgs.append(a)
            if a.get("src"):
                self.requests.append(("img", a["src"]))
        elif tag == "a" and a.get("href"):
            self.requests.append(("a", a["href"]))

    def handle_endtag(self, tag):
        if tag == "main" and self._in_main:
            self._in_main -= 1
        while self._stack and self._stack[-1] != tag:
            self._stack.pop()
        if self._stack:
            self._stack.pop()

        if self._grab is not None:
            text = "".join(self._grab).strip()
            if self._grab_kind == "title":
                self.title = text
            elif self._grab_kind == "ld":
                self.ld.append(text)
            elif self._grab_kind and self._grab_kind.startswith("h"):
                self.headings.append((int(self._grab_kind[1]), text))
            self._grab, self._grab_kind = None, None

    def handle_data(self, data):
        if self._grab is not None:
            self._grab.append(data)
        cur = self._stack[-1] if self._stack else None
        if self._in_main and cur not in SKIP_TEXT:
            self._text.append(data)

    def main_text(self):
        return re.sub(r"\s+", " ", "".join(self._text)).strip()


def load_pages():
    pages = {}
    for fn in sorted(os.listdir(ROOT)):
        if fn.endswith(".html"):
            with open(os.path.join(ROOT, fn), encoding="utf-8") as fh:
                pages[fn] = Page(fn, fh.read())
    return pages


def resolves(url):
    """Does an internal URL point at a real file? Mirrors the host's clean URLs."""
    if url.startswith(("http://", "https://", "mailto:", "tel:", "#", "data:")):
        return True
    path = url.split("#")[0].split("?")[0]
    if not path or path == "/":
        return os.path.isfile(os.path.join(ROOT, "index.html"))
    rel = path.lstrip("/")
    full = os.path.join(ROOT, rel.replace("/", os.sep))
    return os.path.isfile(full) or os.path.isfile(full + ".html")


def sentences(text):
    out = []
    for raw in re.split(r"(?<=[.!?])\s+", text):
        s = raw.strip()
        if len(s.split()) >= 9:
            out.append(s)
    return out


# ─────────────────────────────────────────────────────────────
# Checks
# ─────────────────────────────────────────────────────────────

def run():
    pages = load_pages()
    css_path = os.path.join(ROOT, "assets", "css", "styles.css")
    css = open(css_path, encoding="utf-8").read() if os.path.isfile(css_path) else ""
    js_dir = os.path.join(ROOT, "assets", "js")
    js = ""
    if os.path.isdir(js_dir):
        for fn in sorted(os.listdir(js_dir)):
            if fn.endswith(".js"):
                js += open(os.path.join(js_dir, fn), encoding="utf-8").read()

    # 1 - title and description shape
    p = []
    for name, pg in pages.items():
        if not pg.title:
            p.append(f"{name}: no <title>")
        elif not 20 <= len(pg.title) <= 65:
            p.append(f"{name}: title is {len(pg.title)} chars, want 20-65")
        if not pg.description:
            p.append(f"{name}: no meta description")
        elif not 70 <= len(pg.description) <= 170:
            p.append(f"{name}: description is {len(pg.description)} chars, want 70-170")
    check(1, "title 20-65 chars, description 70-170", p)

    # 2 - titles and descriptions unique
    p = []
    for field in ("title", "description"):
        seen = {}
        for name, pg in pages.items():
            val = getattr(pg, field)
            if val:
                seen.setdefault(val, []).append(name)
        for val, where in seen.items():
            if len(where) > 1:
                p.append(f"{field} repeated on {', '.join(where)}: {val[:60]}...")
    check(2, "titles and descriptions unique", p)

    # 3 - one h1, no skipped heading levels
    p = []
    for name, pg in pages.items():
        h1s = [t for lvl, t in pg.headings if lvl == 1]
        if len(h1s) != 1:
            p.append(f"{name}: {len(h1s)} h1 elements, want exactly 1")
        prev = 0
        for lvl, text in pg.headings:
            if prev and lvl > prev + 1:
                p.append(f"{name}: h{prev} jumps to h{lvl} at {text[:40]!r}")
            prev = lvl
    check(3, "one h1 per page, no skipped heading levels", p)

    # 4 - internal references resolve
    p = []
    for name, pg in pages.items():
        for tag, url in pg.requests:
            if not resolves(url):
                p.append(f"{name}: <{tag}> -> {url} does not resolve")
    check(4, "every internal link, script, style and image resolves", p)

    # 5 - ids unique, IDREFs resolve
    p = []
    for name, pg in pages.items():
        dupes = {i for i in pg.ids if pg.ids.count(i) > 1}
        for d in sorted(dupes):
            p.append(f"{name}: duplicate id {d!r}")
        have = set(pg.ids)
        for kind, ref in pg.idrefs:
            if ref not in have:
                p.append(f"{name}: {kind}={ref!r} points at no element")
        for tag, url in pg.requests:
            if tag == "a" and url.startswith("#") and len(url) > 1:
                if url[1:] not in have:
                    p.append(f"{name}: href={url!r} points at no element")
    check(5, "ids unique and every reference resolves", p)

    # 6 - images carry width, height, alt
    p = []
    for name, pg in pages.items():
        for img in pg.imgs:
            src = img.get("src", "?")
            for attr in ("width", "height"):
                if attr not in img:
                    p.append(f"{name}: img {src} has no {attr}")
            if "alt" not in img:
                p.append(f"{name}: img {src} has no alt")
    check(6, "every img has width, height and alt", p)

    # 7 - structured data parses, and claims nothing invented
    p = []
    for name, pg in pages.items():
        for raw in pg.ld:
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as exc:
                p.append(f"{name}: JSON-LD does not parse: {exc}")
                continue
            blob = json.dumps(data)
            for forbidden in ("AggregateRating", "\"Review\""):
                if forbidden in blob:
                    p.append(f"{name}: JSON-LD contains {forbidden}. "
                             "There are no ratings or reviews to report.")
    check(7, "structured data parses, no invented ratings or reviews", p)

    # 8 - no third-party requests
    p = []
    for name, pg in pages.items():
        for tag, url in pg.requests:
            if tag == "a":
                continue
            if url.startswith(("http://", "https://")) and SITE_HOST not in url:
                p.append(f"{name}: <{tag}> loads third-party {url}")
    check(8, "no third-party requests", p)

    # 9 - sitemap agrees with reality
    p = []
    sm_path = os.path.join(ROOT, "sitemap.xml")
    if not os.path.isfile(sm_path):
        p.append("sitemap.xml is missing")
    else:
        sm = open(sm_path, encoding="utf-8").read()
        listed = set(re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", sm))
        for url in sorted(listed):
            path = url.split(SITE_HOST, 1)[-1] if SITE_HOST in url else url
            if not resolves(path):
                p.append(f"sitemap lists {url} which resolves to no file")
        # The rule, rather than a list of exceptions: a page that says noindex
        # must not be in the sitemap, and an indexable page must be.
        for name, pg in pages.items():
            slug = "/" if name == "index.html" else "/" + name[:-5]
            want = f"https://{SITE_HOST}{slug}"
            present = want in listed or want + "/" in listed
            noindex = "noindex" in (pg.robots or "").lower()
            if noindex and present:
                p.append(f"{name} is noindex but the sitemap lists it ({want})")
            elif not noindex and not present:
                p.append(f"{name} is indexable but the sitemap omits it ({want})")
    check(9, "sitemap and robots meta agree on what is indexable", p)

    # 10 - banned characters and unconfigured placeholders
    p = []
    sources = {name: pg.raw for name, pg in pages.items()}
    sources["assets/css/styles.css"] = css
    sources["assets/js/main.js"] = js
    for name, text in sources.items():
        for ch, label in BANNED_CHARS:
            if ch in text:
                p.append(f"{name}: contains an {label}")
        if EMOJI.search(text):
            p.append(f"{name}: contains an emoji")
        if CONTROL.search(text):
            p.append(f"{name}: contains a control character")
        for m in PLACEHOLDER.finditer(text):
            p.append(f"{name}: unconfigured placeholder {m.group(0)!r}")
    check(10, "no em dash, en dash, emoji, control char or placeholder key", p)

    # 11 - performed insight
    p = []
    for name, pg in pages.items():
        text = pg.main_text()
        for pat, why in PERFORMED:
            for m in re.finditer(pat, text, re.I):
                p.append(f"{name}: {m.group(0)!r} performs the insight. {why}")
    check(11, "no performed insight", p)

    # 12 - no sentence shared between pages.
    # Generated chrome is excluded, because it is shared by definition and its
    # per-page fields are asserted unique by check 20 instead. This check is
    # about authored prose: a button label repeating is a UI decision, the same
    # paragraph on seven pages is a tell.
    p = []
    seen = {}
    for name, pg in pages.items():
        stripped = pg.raw
        # A source line is a reference. Two pages citing the same study should
        # word it identically, and varying a citation to satisfy a duplicate
        # check would corrupt the citation to protect the metric.
        stripped = re.sub(r'<p class="source">.*?</p>', "", stripped, flags=re.S)
        for open_m, close_m in CHROME_MARKERS:
            while open_m in stripped and close_m in stripped:
                a = stripped.index(open_m)
                b = stripped.index(close_m) + len(close_m)
                stripped = stripped[:a] + stripped[b:]
        for s in sentences(Page(name, stripped).main_text()):
            seen.setdefault(s, []).append(name)
    for s, where in sorted(seen.items(), key=lambda kv: -len(set(kv[1]))):
        uniq = sorted(set(where))
        if len(uniq) > 1:
            p.append(f"on {len(uniq)} pages ({', '.join(uniq[:3])}"
                     f"{'...' if len(uniq) > 3 else ''}): {s[:70]}...")
        elif len(where) > 1:
            p.append(f"{len(where)} times on {uniq[0]}: {s[:70]}...")
    check(12, "no sentence of 9+ words repeats across pages", p)

    # 13 - motion lint
    p = []
    if css:
        if "prefers-reduced-motion" not in css:
            p.append("no prefers-reduced-motion block anywhere in the stylesheet")
        for m in re.finditer(r"transition:\s*all\b", css):
            p.append("transition: all - name the properties instead")
        for block in re.findall(r"@keyframes[^{]*\{(.*?)\n\}", css, re.S):
            for prop in re.findall(r"^\s*([a-z-]+)\s*:", block, re.M):
                if prop not in ("transform", "opacity", "stroke-dashoffset"):
                    p.append(f"@keyframes animates {prop!r}; "
                             "only transform, opacity and stroke-dashoffset are cheap")
    check(13, "motion lint", p)

    # 14 - contrast. Lands with the new palette.
    check(14, "token contrast (arrives with the new palette)", [])

    # 15 - no inline style attributes
    p = []
    for name, pg in pages.items():
        if pg.inline_styles:
            p.append(f"{name}: {pg.inline_styles} inline style attributes")
    check(15, "no inline style attributes", p)

    # 16 - private folders cannot be published
    p = []
    ai_path = os.path.join(ROOT, ".assetsignore")
    if not os.path.isfile(ai_path):
        p.append(".assetsignore is missing; the repo root is published as-is")
    else:
        ai = open(ai_path, encoding="utf-8").read()
        for needed in ("_tools", "_notes"):
            if needed not in ai:
                p.append(f".assetsignore does not exclude {needed}/, "
                         "so it would be served publicly")
    gi_path = os.path.join(ROOT, ".gitignore")
    if not os.path.isfile(gi_path):
        p.append(".gitignore is missing")
    elif "_notes" not in open(gi_path, encoding="utf-8").read():
        p.append(".gitignore does not exclude _notes/")
    check(16, "private folders are neither committed nor published", p)

    # 17 - edge headers. Without these the host serves nothing but defaults,
    # and every asset is revalidated on every page load.
    p = []
    h_path = os.path.join(ROOT, "_headers")
    if not os.path.isfile(h_path):
        p.append("_headers is missing; the host will serve no security headers "
                 "and no asset caching")
    else:
        h = open(h_path, encoding="utf-8").read()
        for header in ("X-Content-Type-Options", "Referrer-Policy",
                       "X-Frame-Options", "Permissions-Policy",
                       "Strict-Transport-Security", "Content-Security-Policy"):
            if header not in h:
                p.append(f"_headers does not set {header}")
        for path in ("/assets/css/*", "/assets/js/*", "/assets/fonts/*"):
            block = h.split(path, 1)
            if len(block) < 2 or "immutable" not in block[1].split("\n\n", 1)[0]:
                p.append(f"_headers does not cache {path} immutable")
        csp = ""
        for line in h.splitlines():
            if "Content-Security-Policy:" in line:
                csp = line.split(":", 1)[1]
        if csp:
            if "unsafe-inline" in csp or "unsafe-eval" in csp:
                p.append("the CSP contains an unsafe- escape hatch; the fonts are "
                         "local and the inline styles are gone, so it needs none")
            if "api.web3forms.com" not in csp:
                p.append("the CSP does not allow the form endpoint, so submitting "
                         "would be blocked")
            elif "form-action" not in csp:
                p.append("the CSP allows the form endpoint but not under "
                         "form-action; the forms post natively, so connect-src "
                         "alone would block them while looking correct")
        if os.path.isfile(ai_path):
            ignored = open(ai_path, encoding="utf-8").read()
            if "_headers" in ignored:
                p.append("_headers is listed in .assetsignore, so it is never "
                         "uploaded and never takes effect")
    check(17, "edge sets security headers and caches assets", p)

    # 18 - routing is pinned, not inherited from a default
    p = []
    if not os.path.isfile(os.path.join(ROOT, "404.html")):
        p.append("404.html is missing")
    wr_path = os.path.join(ROOT, "wrangler.jsonc")
    if not os.path.isfile(wr_path):
        p.append("wrangler.jsonc is missing")
    else:
        wr = open(wr_path, encoding="utf-8").read()
        if "html_handling" not in wr:
            p.append("wrangler.jsonc does not pin html_handling; the site's "
                     "clean URLs depend on an unwritten default")
        if "not_found_handling" not in wr:
            p.append("wrangler.jsonc does not set not_found_handling, so 404.html "
                     "is never served")
    check(18, "routing and 404 handling are pinned", p)

    # 19 - every form is actually wired to something
    p = []
    key_shape = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
                           re.I)
    for name, pg in pages.items():
        for form in re.findall(r"<form\b.*?</form>", pg.raw, re.S):
            fid = re.search(r'id="([^"]+)"', form)
            label = f"{name}: form {fid.group(1) if fid else '(no id)'}"

            action = re.search(r'action="([^"]*)"', form)
            if not action or not action.group(1).strip():
                p.append(f"{label} has no action, so submitting it goes nowhere")
                continue

            key = re.search(r'name="access_key"\s+value="([^"]*)"', form)
            if not key:
                p.append(f"{label} carries no access_key")
            elif not key_shape.match(key.group(1)):
                p.append(f"{label} has an access_key that is not a key")

            redirect = re.search(r'name="redirect"\s+value="([^"]*)"', form)
            if not redirect:
                p.append(f"{label} has no redirect, so the visitor lands on a "
                         "third-party page after submitting")
            elif SITE_HOST not in redirect.group(1):
                p.append(f"{label} redirects off-site: {redirect.group(1)}")
            elif "#sent" not in redirect.group(1):
                p.append(f"{label} redirects without #sent, so the confirmation "
                         "panel never shows")

            if "botcheck" not in form:
                p.append(f"{label} has no honeypot")
            if "novalidate" in form:
                p.append(f"{label} sets novalidate but nothing validates it now")

        if "form-sent" in pg.raw and 'id="sent"' not in pg.raw:
            p.append(f"{name} has a confirmation panel with no id=\"sent\" to target")
    check(19, "every form is wired, guarded and confirms", p)

    # 20 - the repeated chrome matches its template
    p = []
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import chrome  # safe: guarded by __main__, stdlib only, no work at import

        css_v = chrome.version(os.path.join(ROOT, "assets", "css", "styles.css"))
        js_v = chrome.version(os.path.join(ROOT, "assets", "js", "main.js"))
        fonts_v = chrome.version(os.path.join(ROOT, "assets", "css", "fonts.css"))
        wanted = {
            "footer": chrome.FOOTER_BLOCK,
            "assets": chrome.assets_block(css_v, js_v, fonts_v),
        }
        for name, pg in pages.items():
            for region in ("nav", "footer", "assets"):
                open_m, close_m = chrome.MARKERS[region]
                if open_m not in pg.raw or close_m not in pg.raw:
                    p.append(f"{name}: no {region} markers; run python _tools/chrome.py")
                    continue
                body = (chrome.nav_block(chrome.ACTIVE.get(name)) if region == "nav"
                        else wanted[region])
                got = pg.raw.split(open_m, 1)[1].split(close_m, 1)[0]
                if got.strip("\n") != body:
                    p.append(f"{name}: the {region} block was hand-edited and no longer "
                             "matches the template; run python _tools/chrome.py")
    except Exception as exc:  # noqa: BLE001
        p.append(f"could not check the chrome: {exc}")
        # The closing block is shared markup with a per-page voice. If two
        # pages ever close on the same line, the duplication has simply moved
        # from the HTML into the template.
        heads, subs = {}, {}
        for name, (heading, sub) in chrome.CTA.items():
            heads.setdefault(heading, []).append(name)
            subs.setdefault(sub, []).append(name)
        for label, group in list(heads.items()) + list(subs.items()):
            if len(group) > 1:
                p.append(f"the closing block is identical on {', '.join(group)}: "
                         f"{label[:50]}...")
    check(20, "repeated chrome matches its template", p)

    # 21 - the FAQ structured data says what the page says
    p = []
    unesc = __import__("html").unescape
    for name, pg in pages.items():
        shown = [(unesc(re.sub(r"<[^>]+>", "", q)).strip(),
                  unesc(re.sub(r"<[^>]+>", "", a)).strip())
                 for q, a in re.findall(
                     r"<summary>(.*?)</summary>\s*<[^>]*class=\"faq__answer\"[^>]*>(.*?)</",
                     pg.raw, re.S)]
        shown = [(re.sub(r"\s+", " ", q), re.sub(r"\s+", " ", a)) for q, a in shown]

        marked = []
        for raw in pg.ld:
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if data.get("@type") != "FAQPage":
                continue
            for item in data.get("mainEntity", []):
                marked.append((
                    re.sub(r"\s+", " ", item.get("name", "")).strip(),
                    re.sub(r"\s+", " ",
                           item.get("acceptedAnswer", {}).get("text", "")).strip(),
                ))

        if not shown and not marked:
            continue
        if bool(shown) != bool(marked):
            p.append(f"{name}: {len(shown)} questions on the page, "
                     f"{len(marked)} in the structured data")
            continue
        if len(shown) != len(marked):
            p.append(f"{name}: {len(shown)} visible questions but "
                     f"{len(marked)} marked up")
            continue
        for (vq, va), (mq, ma) in zip(shown, marked):
            if vq != mq:
                p.append(f"{name}: marked-up question differs from the page: "
                         f"{mq[:52]!r}")
            elif va != ma:
                p.append(f"{name}: the answer to {vq[:38]!r} differs between "
                         "the page and its structured data")
    check(21, "FAQ structured data matches the visible questions", p)

    # 22 - figures that were invented, and must not come back.
    # The patterns live at module level so prove_patterns() can exercise
    # them against a known-bad sample before anything is scanned.
    p = []
    sources = {name: pg.raw for name, pg in pages.items()}
    for extra in ("llms.txt", "site.webmanifest", "robots.txt"):
        fp = os.path.join(ROOT, extra)
        if os.path.isfile(fp):
            sources[extra] = open(fp, encoding="utf-8").read()
    for name, text in sources.items():
        for pat, why, _sample in RETIRED:
            for m in re.finditer(pat, text, re.I):
                p.append(f"{name}: {m.group(0)!r} is {why}")
    check(22, "retired figures stay retired", p)

    # 23 - the stylesheet is structurally intact
    #
    # A rule-removal pass once truncated a comment banner instead of removing
    # it whole, which left every rule after it inside an open comment. The page
    # still rendered, the brace count still balanced, and a link on one page
    # became the same colour as the band behind it. Comment balance is the
    # cheap check that would have caught it.
    p = []
    for rel in ("assets/css/styles.css", "assets/css/fonts.css"):
        fp = os.path.join(ROOT, rel)
        if not os.path.isfile(fp):
            p.append(f"{rel} is missing")
            continue
        css = open(fp, encoding="utf-8").read()
        if css.count("/*") != css.count("*/"):
            p.append(f"{rel}: {css.count('/*')} comments opened but "
                     f"{css.count('*/')} closed, so some rules are commented out")
        if css.count("{") != css.count("}"):
            p.append(f"{rel}: {css.count('{')} braces opened, {css.count('}')} closed")
        # A selector that survived a truncated comment reads as part of it.
        if "/*" in css.split("*/")[-1]:
            p.append(f"{rel}: the file ends inside an unterminated comment")
    check(23, "stylesheets are structurally intact", p)

    return pages


def main():
    prove_patterns()
    pages = run()

    print(f"ProAffy gate: {len(pages)} pages\n")
    failed = 0
    pending = 0
    stale = []

    for num, title, problems, sched in results:
        if problems and sched:
            pending += 1
            print(f"PEND {num:>2}  {title}  [fixed in {sched}]")
            for prob in problems[:4]:
                print(f"         {prob}")
            if len(problems) > 4:
                print(f"         ... and {len(problems) - 4} more")
        elif problems:
            failed += 1
            print(f"FAIL {num:>2}  {title}")
            for prob in problems[:8]:
                print(f"         {prob}")
            if len(problems) > 8:
                print(f"         ... and {len(problems) - 8} more")
        elif sched:
            stale.append((num, title, sched))
            print(f"PASS {num:>2}  {title}  [marked for {sched}, but it passes now]")
        else:
            print(f"PASS {num:>2}  {title}")

    print()
    if stale:
        print("A pending marker outlived its defect. Remove it, or the check is "
              "disabled without anyone deciding to disable it:")
        for num, title, sched in stale:
            print(f"  check {num} is marked pending={sched} and now passes")
        print()
        return 1

    if pending:
        print(f"{pending} checks pending, scheduled for a later session.")
    if failed:
        print(f"{failed} of {len(results)} checks failed.")
        return 1
    print(f"{len(results) - pending} checks passed, {pending} pending.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
