"""Regenerate sitemap.xml, with lastmod taken from git rather than by hand.

The hand-maintained version said 2026-07-11 for twelve of fifteen pages. Every
one of those pages had been rewritten at least twice since, most recently the
same day this was written. A lastmod that is three months stale is worse than
no lastmod at all: it is the one field in the file a crawler is entitled to
trust, and it was telling every crawler not to bother re-reading pages that had
changed completely.

The fix is to stop maintaining it. `git log -1 --format=%cs` on each page is
the date its content actually last changed, so the field cannot drift from the
truth without somebody rewriting history.

changefreq and priority stay hand-set: they are editorial judgements about how
often a page is worth re-checking, not facts about the file. Google has said
for years that it ignores both; they cost nothing and other crawlers still read
them.

Run:  python _tools/sitemap.py           rewrite sitemap.xml
      python _tools/sitemap.py --check   exit 1 if it is out of date
"""
import io
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "sitemap.xml")
SITE = "https://proaffy.com"

# path on the site -> (file, changefreq, priority). Order is the file's order.
PAGES = [
    ("/", "index.html", "weekly", "1.0"),
    ("/services", "services.html", "monthly", "0.9"),
    ("/contact", "contact.html", "monthly", "0.8"),
    ("/about", "about.html", "monthly", "0.7"),
    ("/hvac", "hvac.html", "monthly", "0.9"),
    ("/solar", "solar.html", "monthly", "0.9"),
    ("/blog", "blog.html", "weekly", "0.8"),
    ("/blog-thermogrowth-engine", "blog-thermogrowth-engine.html", "monthly", "0.7"),
    ("/blog-hvac-seo", "blog-hvac-seo.html", "monthly", "0.7"),
    ("/blog-hvac-geo", "blog-hvac-geo.html", "monthly", "0.7"),
    ("/blog-hvac-websites", "blog-hvac-websites.html", "monthly", "0.7"),
    ("/blog-hvac-digital-presence", "blog-hvac-digital-presence.html", "monthly", "0.7"),
    ("/blog-solar-quote-requests", "blog-solar-quote-requests.html", "monthly", "0.7"),
    ("/privacy", "privacy.html", "yearly", "0.3"),
    ("/terms", "terms.html", "yearly", "0.3"),
]


def lastmod(filename):
    """The date this page's content last changed, from git.

    Falls back to the filesystem mtime when the file is not committed yet,
    which is the honest answer during a working session.
    """
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%cs", "--", filename],
            cwd=ROOT, capture_output=True, text=True, timeout=20)
        stamp = out.stdout.strip()
        if stamp:
            return stamp
    except (OSError, subprocess.SubprocessError):
        pass
    import datetime
    path = os.path.join(ROOT, filename)
    if os.path.isfile(path):
        return datetime.date.fromtimestamp(os.path.getmtime(path)).isoformat()
    return ""


def build():
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">', ""]
    missing = []
    for path, filename, freq, prio in PAGES:
        if not os.path.isfile(os.path.join(ROOT, filename)):
            missing.append(filename)
            continue
        lines += [
            "  <url>",
            f"    <loc>{SITE}{path}</loc>",
            f"    <lastmod>{lastmod(filename)}</lastmod>",
            f"    <changefreq>{freq}</changefreq>",
            f"    <priority>{prio}</priority>",
            "  </url>",
            "",
        ]
    lines += ["</urlset>", ""]
    return "\n".join(lines), missing


def main():
    check = "--check" in sys.argv
    body, missing = build()

    for m in missing:
        print(f"  listed in PAGES but not on disk: {m}")

    current = io.open(OUT, encoding="utf-8").read() if os.path.isfile(OUT) else None
    if current == body:
        print(f"sitemap.xml is current ({len(PAGES)} urls)")
        return 1 if missing else 0
    if check:
        print("sitemap.xml is OUT OF DATE; run python _tools/sitemap.py")
        return 1

    io.open(OUT, "w", encoding="utf-8", newline="\n").write(body)
    print(f"wrote sitemap.xml, {len(PAGES)} urls")
    for path, filename, _f, _p in PAGES:
        print(f"  {path:30} {lastmod(filename)}")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
