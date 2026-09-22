"""Regenerate the repeated chrome across every page. Stdlib only.

The site has no build step and the pages are hand-written, so three regions were
hand-duplicated across 13 files. This owns exactly those, and nothing else:

  nav     a one-parameter template. Every nav is 31 identical lines except for a
          single ` active` token on one link. None is a valid argument: 404,
          privacy and terms legitimately have no active state.
  footer  a literal constant, byte-identical everywhere, zero parameters.
  cta     the closing block, on the seven pages that carry one. Per-page heading
          and line, because it used to be identical on all seven.
  assets  the 8-line block in <head> that every page shares. The rest of each
          head is per-page SEO copy and is deliberately NOT owned here. Owning
          titles, canonicals and JSON-LD would be a content pipeline, not a
          template.

Cache-busting is derived from a content hash rather than a number somebody
remembers to increment. That stopped being cosmetic when the edge began serving
CSS and JS immutable for a year: a missed bump pins the old file in every
returning visitor's cache, and the failure is silent.

Run:  python _tools/chrome.py          rewrite in place
      python _tools/chrome.py --check  exit 1 if anything is out of date
"""
import hashlib
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY = "5da7b2bb-24b2-42ad-96ac-7228dd4ce8d6"

# Which nav link is marked active on which page. A page absent from this map
# gets no active link, which is correct for 404, privacy and terms.
ACTIVE = {
    "index.html": "home",
    "hvac.html": "hvac",
    "solar.html": "solar",
    "services.html": "services",
    "blog.html": "blog",
    "blog-hvac-digital-presence.html": "blog",
    "blog-hvac-geo.html": "blog",
    "blog-hvac-seo.html": "blog",
    "blog-hvac-websites.html": "blog",
    "blog-thermogrowth-engine.html": "blog",
    "blog-solar-quote-requests.html": "blog",
    "contact.html": "contact",
}

LINKS = [
    ("home", "/", "Home"),
    ("hvac", "/hvac", "HVAC"),
    ("solar", "/solar", "Solar"),
    ("services", "/services", "Services"),
    ("blog", "/blog", "Blog"),
    ("contact", "/contact", "Contact"),
]


def nav_block(active):
    desktop = "\n".join(
        f'        <a href="{href}" class="nav__link'
        + (" active" if key == active else "")
        + f'">{label}</a>'
        for key, href, label in LINKS
    )
    # The mobile menu never carries an active state.
    mobile = "\n".join(
        f'    <a href="{href}" class="nav__mobile-link">{label}</a>'
        for _key, href, label in LINKS
    )
    return f"""  <header class="nav" role="banner">
    <div class="nav__inner">
      <a href="/" class="nav__logo" aria-label="ProAffy home">
        <img src="assets/images/logo-136.png" class="nav__logo-img" alt="ProAffy logo" width="68" height="68" />
      </a>

      <nav class="nav__links" aria-label="Main navigation">
{desktop}
      </nav>

      <a href="/contact" class="btn btn--primary nav__cta">Get Free Pilot</a>

      <button class="nav__hamburger" aria-label="Open menu" aria-expanded="false" id="hamburger">
        <span></span><span></span><span></span>
      </button>
    </div>
  </header>

  <!-- Mobile menu -->
  <nav class="nav__mobile-menu" id="mobileMenu" aria-label="Mobile navigation">
{mobile}
    <a href="/contact" class="btn btn--primary">Get Free Pilot</a>
  </nav>"""


FOOTER_BLOCK = """  <footer class="footer" role="contentinfo">
    <div class="container">
      <div class="footer__inner">
        <a href="/about" class="footer__link">About</a>
        <a href="/privacy" class="footer__link">Privacy Policy</a>
        <div>
          <span class="footer__email-label">Email</span>
          <a href="mailto:info@proaffy.com" class="footer__email-addr">info@proaffy.com</a>
        </div>
        <a href="/terms" class="footer__link">Terms of Service</a>
      </div>
    </div>
  </footer>"""


def assets_block(css_v, js_v, fonts_v):
    """The 8-line invariant block. Fonts are local: nothing here leaves the origin.

    Only the two sans weights are preloaded. Mono is below the fold on every page
    and preloading four faces would make them compete with the stylesheet for the
    first round trip. crossorigin is required on a font preload even same-origin,
    because fonts are always fetched in CORS mode.
    """
    return f"""  <link rel="icon" type="image/png" sizes="32x32" href="assets/images/favicon-32.png" />
  <link rel="apple-touch-icon" sizes="180x180" href="assets/images/apple-touch-icon.png" />
  <link rel="manifest" href="site.webmanifest" />
  <link rel="preload" as="font" type="font/woff2" href="assets/fonts/ibm-plex-sans-400.woff2" crossorigin />
  <link rel="preload" as="font" type="font/woff2" href="assets/fonts/ibm-plex-sans-600.woff2" crossorigin />
  <link rel="stylesheet" href="assets/css/fonts.css?v={fonts_v}" />
  <link rel="stylesheet" href="assets/css/styles.css?v={css_v}" />
  <script defer src="assets/js/main.js?v={js_v}"></script>"""


# The closing block used to be byte-identical on seven pages, so seven pages
# ended on the same sentence. It is generated now, and every page closes on a
# line that belongs to it. Gate check 12 fails the build if two pages ever
# share a sentence again.
CTA = {
    "index.html": (
        "See it run on your own leads",
        "We set it up, run it for a month, and you decide afterwards whether it "
        "was worth paying for.",
    ),
    "services.html": (
        "Start with the part that is costing you most",
        "Tell us where jobs are slipping and we will run that piece first.",
    ),
    "blog-thermogrowth-engine.html": (
        "Watch it answer a real enquiry",
        "Send one through and we will show you the reply it gets, with the "
        "timestamps.",
    ),
    "blog-hvac-seo.html": (
        "Ranking gets you the call",
        "Answering it before the next company does is the part we handle.",
    ),
    "blog-hvac-geo.html": (
        "Being recommended is the first half",
        "Once an assistant points a homeowner at you, the reply still has to "
        "arrive in seconds.",
    ),
    "blog-hvac-websites.html": (
        "A faster site still needs a faster reply",
        "We answer what your site collects, at any hour, without you reaching "
        "for the phone.",
    ),
    "blog-hvac-digital-presence.html": (
        "Being easy to find is where it starts",
        "Being quick to answer is where the job actually gets booked.",
    ),
    # These two ended on nothing at all, while seven other pages closed on the
    # same sentence. Both were the same problem: a template applied unevenly.
    "blog-solar-quote-requests.html": (
        "Stop losing the ones that went quiet",
        "We reopen the proposals nobody answered, on the same sequence as the "
        "new enquiries.",
    ),
    "hvac.html": (
        "Try it on one cold snap",
        "Run it through your next busy week and see which calls got answered that "
        "otherwise would not have.",
    ),
    "solar.html": (
        "Be the one who answered first",
        "Put it on your next batch of quote requests and watch where the "
        "conversations are by week three.",
    ),
    "about.html": (
        "Find out what it does on your enquiries",
        "A month on your live leads answers the question better than another "
        "paragraph about us.",
    ),
    "blog.html": (
        "Reading about it is slower than watching it",
        "Put the sequence on your own enquiries and look at what the first "
        "replies actually said.",
    ),
}


def cta_block(name):
    heading, sub = CTA[name]
    slug = "/" if name == "index.html" else "/" + name[:-5]
    return f"""  <section class="cta-email" aria-labelledby="cta-heading">
    <div class="cta-email__content">
      <h2 class="cta-email__heading" id="cta-heading">{heading}</h2>
      <p class="cta-email__sub">{sub}</p>

      <div class="form-sent" id="sent" role="status">
        <p class="form-sent__title">Thank you. Your message reached us.</p>
        <p>We reply within one business day. If it is urgent, email
          <a href="mailto:info@proaffy.com">info@proaffy.com</a>.</p>
      </div>

      <form class="cta-email__form" id="ctaEmailForm"
            action="https://api.web3forms.com/submit" method="POST">
        <input type="hidden" name="access_key" value="{KEY}" />
        <input type="hidden" name="subject" value="Free pilot request from proaffy.com" />
        <input type="hidden" name="redirect" value="https://proaffy.com{slug}?sent=1#sent" />
        <input type="checkbox" name="botcheck" class="hp" tabindex="-1"
               autocomplete="off" aria-hidden="true" />
        <input
          type="email"
          name="email"
          class="cta-email__input"
          placeholder="Email Address..."
          aria-label="Email address"
          required
        />
        <button type="submit" class="btn btn--filled">Book Your Free Pilot</button>
      </form>

      <p class="cta-email__contact">
        <span>Or email us directly:</span>
        <a href="mailto:info@proaffy.com">info@proaffy.com</a>
      </p>
    </div>
  </section>"""


MARKERS = {
    "nav": ("  <!-- chrome:nav -->", "  <!-- /chrome:nav -->"),
    "footer": ("  <!-- chrome:footer -->", "  <!-- /chrome:footer -->"),
    "assets": ("  <!-- chrome:assets -->", "  <!-- /chrome:assets -->"),
    "cta": ("  <!-- chrome:cta -->", "  <!-- /chrome:cta -->"),
}


def version(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()[:8]


def find_region(text, region):
    """Locate a region the first time, before markers exist.

    Anchored on structure, never on a bare tag: 8 pages carry a second
    <nav class="breadcrumb">, so matching <nav> to </nav> would swallow it.
    Returns (start, end) character offsets, or None.
    """
    if region == "nav":
        start = text.find('  <header class="nav" role="banner">')
        if start == -1:
            return None
        anchor = text.find('<nav class="nav__mobile-menu"', start)
        if anchor == -1:
            return None
        end = text.find("</nav>", anchor)
        if end == -1:
            return None
        return start, end + len("</nav>")

    if region == "footer":
        start = text.find('  <footer class="footer" role="contentinfo">')
        if start == -1:
            return None
        end = text.find("</footer>", start)
        return (start, end + len("</footer>")) if end != -1 else None

    if region == "cta":
        start = text.find('  <section class="cta-email"')
        if start != -1:
            end = text.find("</section>", start)
            return (start, end + len("</section>")) if end != -1 else None
        # A page that never had one. About and Blog ended on nothing at all,
        # while seven other pages closed on the same sentence: the same
        # template applied unevenly, in two different directions. Insert it at
        # the foot of main, as a zero-width replacement.
        close = text.find("  </main>")
        return (close, close) if close != -1 else None

    if region == "assets":
        start = text.find('  <link rel="icon"')
        if start == -1:
            return None
        end = text.find("></script>", start)
        return (start, end + len("></script>")) if end != -1 else None

    return None


def apply_region(text, region, body):
    """Replace a marked region, inserting the markers on first run."""
    open_m, close_m = MARKERS[region]
    block = f"{open_m}\n{body}\n{close_m}"

    if open_m in text:
        start = text.index(open_m)
        end = text.index(close_m) + len(close_m)
        return text[:start] + block + text[end:]

    found = find_region(text, region)
    if not found:
        return None
    start, end = found
    return text[:start] + block + text[end:]


def main():
    check = "--check" in sys.argv

    css_v = version(os.path.join(ROOT, "assets", "css", "styles.css"))
    js_v = version(os.path.join(ROOT, "assets", "js", "main.js"))
    fonts_v = version(os.path.join(ROOT, "assets", "css", "fonts.css"))

    bodies = {"footer": FOOTER_BLOCK,
              "assets": assets_block(css_v, js_v, fonts_v)}

    stale, written, problems = [], [], []

    for name in sorted(os.listdir(ROOT)):
        if not name.endswith(".html"):
            continue
        path = os.path.join(ROOT, name)
        src = io.open(path, encoding="utf-8").read()
        out = src

        for region in ("nav", "footer", "assets", "cta"):
            if region == "cta" and name not in CTA:
                continue
            if region == "nav":
                body = nav_block(ACTIVE.get(name))
            elif region == "cta":
                body = cta_block(name)
            else:
                body = bodies[region]
            result = apply_region(out, region, body)
            if result is None:
                problems.append(f"{name}: could not locate the {region} region")
                continue
            out = result

        if out == src:
            continue
        if check:
            stale.append(name)
        else:
            # write-if-changed: required inside OneDrive, which syncs on mtime.
            io.open(path, "w", encoding="utf-8", newline="\n").write(out)
            written.append(name)

    print(f"chrome: css v{css_v}, js v{js_v}, fonts v{fonts_v}")
    for p in problems:
        print(f"  PROBLEM {p}")
    if check:
        for s in stale:
            print(f"  STALE   {s}")
        if stale or problems:
            print(f"\n{len(stale)} pages out of date, {len(problems)} problems.")
            return 1
        print("  every page is current")
        return 0

    for w in written:
        print(f"  wrote   {w}")
    if not written:
        print("  no change")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
