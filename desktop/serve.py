#!/usr/bin/env python3
"""Serve the Toastmasters tools on http://127.0.0.1:8765 from the repo root.

A real origin (not file://) is what clipboard, localStorage isolation and the
programme builder's folder picker need. Tauri should load the same files from
its bundled dist; this script is for trying that origin in an ordinary browser.
"""
from __future__ import annotations

import argparse
import functools
import http.server
import os
import socketserver
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEFAULT_PORT = 8765


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def log_message(self, fmt, *args):
        sys.stderr.write('%s - %s\n' % (self.address_string(), fmt % args))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--port', type=int, default=DEFAULT_PORT)
    args = p.parse_args()

    handler = functools.partial(Handler, directory=ROOT)
    try:
        httpd = socketserver.TCPServer(('127.0.0.1', args.port), handler)
    except OSError as e:
        sys.exit('could not bind 127.0.0.1:%d: %s' % (args.port, e))

    httpd.allow_reuse_address = True
    url = 'http://127.0.0.1:%d/' % args.port
    print('Serving %s' % ROOT)
    print('Open  %s' % url)
    print('Stop with Ctrl+C')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print()


if __name__ == '__main__':
    main()
