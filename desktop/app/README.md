# Toastmasters Tools — Windows .exe and portable packs

One Go source builds **two** apps. Neither rewrites the tools: the HTML is
embedded and served on a fixed `127.0.0.1` port so clipboard, `localStorage`
and the builder's folder picker have a real origin.

| App | What it opens | Origin | Files in `desktop/dist/` |
|-----|---------------|--------|---------------------------|
| **Toastmasters Tools** | The hub — club finder, programme sheet, timer, Ah-Counter | `127.0.0.1:8765` | `ToastmastersTools.exe`, `ToastmastersTools-portable.zip` |
| **Programme Sheet Builder** | Only the programme sheet builder (V48), as the root page | `127.0.0.1:8770` | `ProgrammeSheet.exe`, `ProgrammeSheet-portable.zip` |

Each app keeps its own profile folder under `%LocalAppData%` (`ToastmastersTools\`,
`ProgrammeSheet\`), so Club Setup and the working sheet in the sheet-only app are
separate from the builder inside the hub. Both can be open at once.

## Download

Direct links (branch `main`):

- https://github.com/ramnaths89/toastmasters/raw/main/desktop/dist/ProgrammeSheet-portable.zip
- https://github.com/ramnaths89/toastmasters/raw/main/desktop/dist/ProgrammeSheet.exe
- https://github.com/ramnaths89/toastmasters/raw/main/desktop/dist/ToastmastersTools-portable.zip
- https://github.com/ramnaths89/toastmasters/raw/main/desktop/dist/ToastmastersTools.exe

The `.exe` files are Windows 64-bit and **unsigned**. When Smart App Control
blocks one, use the matching `-portable.zip`: Unblock, extract, double-click
`Install.cmd`. That installs a Desktop + Start Menu shortcut for this Windows
user. `START.cmd` runs once without installing. Share the zip or the folder;
do not share the `.exe` to a PC that uses Smart App Control.

On a club laptop with an `.exe`:

1. Copy the `.exe` onto the machine (USB or email).
2. Double-click it.
3. Windows will warn because the file is **not code-signed**. What you see depends
   on the machine:
   - **SmartScreen** (blue/yellow “Windows protected your PC”): *More info* → *Run anyway*.
   - **Smart App Control** (pink **Okay** / **Get apps from the Store**, no Run anyway):
     that dialog cannot launch the file. Click Okay and use the portable zip
     instead, or install the site as an app from Edge
     (https://ramnaths89.github.io/toastmasters/programme-sheet-builder/ → ⋮ →
     Apps → *Install this site as an app*).
   - Right-click the `.exe` → Properties → tick **Unblock** if it is there, then try
     again. That only clears “downloaded from the internet”; it does not replace a
     signature.
4. The window uses **Microsoft Edge WebView2** (already on current Windows 10/11).
   If that runtime is missing, it falls back to Edge or Chrome `--app`.
5. Close the window to quit.

Needs a 64-bit Windows 10/11 machine with Edge. Does **not** need Python,
Node, or an internet connection after the file is copied.

## Rebuild

After changing any tool (for the sheet-only app: after `publish.py` writes a new
`programme-sheet-builder/index.html`):

```
python3 desktop/app/build.py          # both apps
python3 desktop/app/build.py sheet    # Programme Sheet Builder only
python3 desktop/app/build.py hub      # Toastmasters Tools only
```

`build.py` stages the variant's files into `web/`, zips them with the launchers
from `desktop/windows/` (the sheet variant gets its names, port and URL
substituted), and cross-compiles from Linux or Windows with
`-ldflags "-X main.title=… -X main.appID=… -X main.prefAddr=…"`.
