#!/usr/bin/env python3
"""Open Toastmasters Tools as a Chromium app window on a real origin.

Wraps the existing HTML hub. Does not rewrite the tools. Starts
desktop/serve.py on 127.0.0.1:8765 if that port is free, then launches
Chrome / Chromium / Edge with --app= so there is no tab chrome.

    python3 desktop/launch.py

Stop the window to quit. The server exits with the browser process.
file:// is not used: clipboard, localStorage isolation and the builder's
folder picker all need http://127.0.0.1.
"""
import os
import shutil
import socket
import subprocess
import sys
import time
import webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PORT = 8765
URL = 'http://127.0.0.1:%d/' % PORT

BROWSERS = [
    'google-chrome',
    'google-chrome-stable',
    'chromium',
    'chromium-browser',
    'microsoft-edge',
    'msedge',
    os.path.expandvars(r'%ProgramFiles%\Google\Chrome\Application\chrome.exe'),
    os.path.expandvars(r'%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe'),
    os.path.expandvars(r'%LocalAppData%\Google\Chrome\Application\chrome.exe'),
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
]


def port_open(port: int) -> bool:
    s = socket.socket()
    s.settimeout(0.3)
    try:
        s.connect(('127.0.0.1', port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def find_browser():
    for name in BROWSERS:
        if not name:
            continue
        if os.path.sep in name or (len(name) > 1 and name[1] == ':'):
            if os.path.isfile(name):
                return name
            continue
        found = shutil.which(name)
        if found:
            return found
    return None


def main() -> None:
    server = None
    if not port_open(PORT):
        server = subprocess.Popen(
            [sys.executable, os.path.join(HERE, 'serve.py'), '--port', str(PORT)],
            cwd=ROOT,
        )
        for _ in range(40):
            if port_open(PORT):
                break
            time.sleep(0.05)
        else:
            if server.poll() is not None:
                sys.exit('local server failed to start on 127.0.0.1:%d' % PORT)

    browser = find_browser()
    try:
        if browser:
            print('Opening %s as an app window via %s' % (URL, browser))
            proc = subprocess.Popen([browser, '--app=%s' % URL, '--new-window'])
            proc.wait()
        else:
            print('No Chrome / Edge / Chromium on PATH — opening the default browser')
            print('Install Chrome for a frameless app window, or use: python3 desktop/serve.py')
            webbrowser.open(URL)
            if server:
                print('Server running. Ctrl+C to stop.')
                server.wait()
    finally:
        if server and server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=3)
            except subprocess.TimeoutExpired:
                server.kill()


if __name__ == '__main__':
    main()
