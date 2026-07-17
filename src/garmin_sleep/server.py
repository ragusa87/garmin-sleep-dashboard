"""Serveur HTTP local minimal pour le tableau de bord."""

from __future__ import annotations

import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def _make_handler(html: str) -> type[BaseHTTPRequestHandler]:
    body = html.encode("utf-8")

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path not in ("/", "/index.html"):
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):  # silence les logs de requêtes
            pass

    return Handler


def serve(html: str, port: int = 8765, open_browser: bool = True) -> None:
    with ThreadingHTTPServer(("127.0.0.1", port), _make_handler(html)) as httpd:
        url = f"http://127.0.0.1:{httpd.server_address[1]}/"
        print(f"Tableau de bord : {url}  (Ctrl+C pour quitter)")
        if open_browser:
            webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nArrêt.")
