"""Standalone server for the Gen UI POC repository."""
import os
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from a2ui_poc import handle

ROOT = Path(__file__).resolve().parent.parent


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if handle(self, 'GET'):
            return
        if self.path == '/':
            self.send_response(302)
            self.send_header('Location', '/research/a2ui-test/')
            self.end_headers()
            return
        super().do_GET()

    def do_POST(self):
        if not handle(self, 'POST'):
            self.send_error(404)

    def send_head(self):
        target = Path(self.translate_path(self.path)).resolve()
        public_roots = (ROOT / 'research' / 'a2ui-test', ROOT / 'research' / 'a2ui-overview')
        mermaid = ROOT / 'assets' / 'vendor' / 'mermaid' / 'mermaid.tiny.js'
        is_public = any(
            target.is_relative_to(folder)
            and not any(part.startswith('.') for part in target.relative_to(folder).parts)
            for folder in public_roots
        )
        if not is_public and target != mermaid:
            self.send_error(404)
            return None
        return super().send_head()

    def list_directory(self, path):
        self.send_error(404)
        return None


if __name__ == '__main__':
    host = os.environ.get('HOST', '127.0.0.1')
    port = int(os.environ.get('PORT', '8080'))
    server = ThreadingHTTPServer((host, port), partial(Handler, directory=str(ROOT)))
    print('Gen UI POC server ready.')
    server.serve_forever()
