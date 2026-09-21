"""
ProAffy dev server.
Run:  python server.py
Then open http://localhost:8000 in your browser.

Serves extensionless URLs the way the production host does, so /about resolves
to about.html here as well. Without that, local preview 404s on every link the
site actually ships, and routing bugs only surface after a deploy.
"""
import http.server
import socketserver
import webbrowser
import os

PORT = 8000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def translate_path(self, path):
        fs_path = super().translate_path(path)
        if os.path.exists(fs_path):
            return fs_path
        # /about -> about.html, matching the host's clean-URL handling.
        candidate = fs_path + ".html"
        if os.path.isfile(candidate):
            return candidate
        return fs_path

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def log_message(self, fmt, *args):
        print(f"  {self.address_string()} → {fmt % args}")


if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        url = f"http://localhost:{PORT}"
        print(f"\n  ProAffy dev server running at {url}\n  Press Ctrl+C to stop.\n")
        webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n  Server stopped.")
