"""Probe the deployed site. Read-only, stdlib only.

verify.py checks the repo. This checks what the edge actually serves, which is
a different thing: `_headers` can be correct and still not take effect, and the
host-level settings below live in the Cloudflare dashboard and are in no file
here, so nothing in the repo would ever notice them regressing.

Run after a deploy:  python _tools/check-edge.py
"""
import sys
import urllib.error
import urllib.request

APEX = "https://proaffy.com"
WWW = "https://www.proaffy.com"

SECURITY_HEADERS = [
    "x-content-type-options",
    "referrer-policy",
    "x-frame-options",
    "permissions-policy",
    "strict-transport-security",
]

problems = []
notes = []


def fetch(url, method="HEAD", redirect=True):
    """Return (status, headers, body). Does not follow redirects when asked not to."""
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None

    handlers = [] if redirect else [NoRedirect]
    opener = urllib.request.build_opener(*handlers)
    req = urllib.request.Request(url, method=method,
                                 headers={"User-Agent": "proaffy-edge-check"})
    try:
        with opener.open(req, timeout=20) as res:
            body = res.read() if method == "GET" else b""
            return res.status, {k.lower(): v for k, v in res.headers.items()}, body
    except urllib.error.HTTPError as exc:
        body = exc.read() if method == "GET" else b""
        return exc.code, {k.lower(): v for k, v in exc.headers.items()}, body
    except Exception as exc:  # noqa: BLE001
        return None, {"error": str(exc)}, b""


def main():
    print(f"probing {APEX}\n")

    # 1 - security headers
    status, headers, _ = fetch(APEX + "/")
    if status != 200:
        problems.append(f"homepage returned {status}")
    for h in SECURITY_HEADERS:
        if h not in headers:
            problems.append(f"{h} is not being served")
    print(f"  security headers   {len(SECURITY_HEADERS) - len([h for h in SECURITY_HEADERS if h not in headers])}/{len(SECURITY_HEADERS)}")

    # 2 - asset caching
    for path in ("/assets/css/styles.css", "/assets/js/main.js"):
        _s, h, _b = fetch(APEX + path)
        cc = h.get("cache-control", "")
        if "immutable" not in cc:
            problems.append(f"{path} is not cached immutable (got {cc!r})")
    print("  asset caching      css and js")

    # 3 - html must stay short-lived so a deploy is visible at once
    cc = headers.get("cache-control", "")
    if "immutable" in cc or "max-age=31536000" in cc:
        problems.append(f"html is cached long ({cc!r}); a deploy would not be visible")
    print(f"  html cache         {cc}")

    # 4 - a real 404 with a real status
    status, _h, body = fetch(APEX + "/this-page-does-not-exist", method="GET")
    if status != 404:
        problems.append(f"unknown path returned {status}, want 404")
    if b"That page is not here" not in body:
        problems.append("the 404 page is not being served")
    print(f"  404                {status}")

    # 5 - private paths must not be public
    for path in ("/_headers", "/_tools/verify.py", "/_notes/ROADMAP.md"):
        status, _h, _b = fetch(APEX + path)
        if status == 200:
            problems.append(f"{path} is publicly readable")
    print("  private paths      not served")

    # 6 - one hostname, not two. This cannot be fixed from the repo: Cloudflare
    # matches only the path, never the host, so a _redirects rule starting with
    # https:// can never match. It is a zone Redirect Rule in the dashboard.
    status, h, _b = fetch(WWW + "/", redirect=False)
    if status == 200:
        problems.append(
            "www.proaffy.com serves the site with 200 instead of redirecting. "
            "Two hostnames serve identical pages. Fix: a zone Redirect Rule, "
            "not a file in this repo.")
    elif status in (301, 308):
        print(f"  www -> apex        {status}")
    elif status is None:
        notes.append("www.proaffy.com does not resolve, which is also fine")
    else:
        notes.append(f"www.proaffy.com returned {status}")

    # 7 - plain http must not serve the site
    status, h, _b = fetch("http://proaffy.com/", redirect=False)
    if status == 200:
        problems.append(
            "http://proaffy.com serves the site over plain HTTP with 200. "
            "Fix: turn on Always Use HTTPS in the dashboard.")
    elif status in (301, 308):
        print(f"  http -> https      {status}")

    print()
    for n in notes:
        print(f"note: {n}")
    if problems:
        print(f"\n{len(problems)} problems:")
        for p in problems:
            print(f"  {p}")
        return 1
    print("edge is clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
