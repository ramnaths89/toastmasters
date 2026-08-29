# Toastmasters Tools — Windows .exe

One double-clickable file that wraps **all four tools** (hub, club finder,
programme sheet, timer, Ah-Counter). It does not rewrite them. The HTML is
embedded and served on `http://127.0.0.1:8765` so clipboard, `localStorage`
and the builder's folder picker have a real origin.

## Download

`desktop/dist/ToastmastersTools.exe` — Windows 64-bit, unsigned.

On a club laptop:

1. Copy the `.exe` onto the machine (USB or email).
2. Double-click it.
3. Windows SmartScreen will warn because the file is **not code-signed**.
   *More info* → *Run anyway*.
4. The window uses **Microsoft Edge WebView2** (already on current Windows 10/11).
   If that runtime is missing, it falls back to Edge or Chrome `--app`.
5. Close the window to quit.

Needs a 64-bit Windows 10/11 machine with Edge. Does **not** need Python,
Node, or an internet connection after the file is copied.

Rebuild after changing any tool:

```
python3 desktop/app/build.py
```

That restages `index.html` and the four tool folders, then cross-compiles
from Linux or Windows.
