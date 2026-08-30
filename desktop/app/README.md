# Toastmasters Tools — Windows .exe

One double-clickable file that wraps **all four tools** (hub, club finder,
programme sheet, timer, Ah-Counter). It does not rewrite them. The HTML is
embedded and served on `http://127.0.0.1:8765` so clipboard, `localStorage`
and the builder's folder picker have a real origin.

## Download

`desktop/dist/ToastmastersTools.exe` — Windows 64-bit, unsigned.

When Smart App Control blocks that file, use
`desktop/dist/ToastmastersTools-portable.zip` instead: Unblock the zip, extract,
double-click `ToastmastersTools.cmd`. That is a script that opens Edge, not an
unsigned `.exe`.

On a club laptop with the `.exe`:

1. Copy the `.exe` onto the machine (USB or email).
2. Double-click it.
3. Windows will warn because the file is **not code-signed**. What you see depends
   on the machine:
   - **SmartScreen** (blue/yellow “Windows protected your PC”): *More info* → *Run anyway*.
   - **Smart App Control** (pink **Okay** / **Get apps from the Store**, no Run anyway):
     that dialog cannot launch the file. Click Okay. Either install the site as an
     app from Edge (https://ramnaths89.github.io/toastmasters/ → ⋮ → Apps →
     *Install this site as an app*), or turn Smart App Control off under
     Settings → Privacy & security → Windows Security → App & browser control.
     Microsoft treats turning it off as one-way on that PC.
   - Right-click the `.exe` → Properties → tick **Unblock** if it is there, then try
     again. That only clears “downloaded from the internet”; it does not replace a
     signature.
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
