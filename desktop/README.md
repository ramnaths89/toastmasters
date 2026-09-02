# Wrapping these tools as a desktop app

The product is already four self-contained web pages behind **one hub** (`index.html`).
A standalone desktop app should **open that hub in a native window**, not rewrite the
tools. That keeps GitHub Pages, the programme sheet's print geometry, and every existing
save file working.

The hub is the mega-app: Home plus Finder, Sheet, Timer and Ah-Counter in the same
window. Tools load on first use and stay mounted, so a live timer keeps ticking while
you log crutches. **Pop out** opens a tool in its own window (and unloads that iframe)
when you need a projector plus a second laptop.

## What “standalone” needs to mean here

Club laptops are the real target. The Timer and Ah-Counter run live in a meeting room.
The programme sheet builder is used at home or at the venue, often on whatever Wi-Fi is
going. A useful desktop build therefore has to:

- Open without a browser tab or address bar
- Work with no network (after the files are on disk)
- Keep each tool’s `localStorage` on a stable origin (not `file://`)
- Let the builder write `.json` / PDF / JPG to disk
- Stay small enough to email or put on a USB stick

Rewriting in Swift / C# / Qt would throw away the programme sheet’s print geometry, which
sits about 4 mm from a third A4 page and is guarded by `pgprobe.py`. Do not do that.

## Options

| Path | What you get | Size | Fit |
|------|----------------|------|-----|
| **`ProgrammeSheet-portable.zip`** | **Programme sheet builder only.** `Install.cmd` → Desktop shortcut *Programme Sheet Builder*. Edge window, offline, own origin `127.0.0.1:8770`. Smart App Control runs it. | ~200 KB | For the TME who only needs the sheet. Nothing else in the window. |
| **`ProgrammeSheet.exe`** | Same, as one double-clickable file (WebView2). | ~7 MB | Unsigned — SmartScreen can *Run anyway*; Smart App Control cannot. |
| **`ToastmastersTools-portable.zip`** | Double-click `START.cmd`. Edge window, all four tools, offline. **This is the Smart App Control path.** | ~500 KB | No unsigned `.exe`. Unblock the zip if Windows copied it from the internet. |
| **`ToastmastersTools.exe`** | Double-clickable Windows app. Embeds all four tools. Native Edge WebView2 window. | ~8 MB | Unsigned — SmartScreen can *Run anyway*; Smart App Control cannot. |
| **PWA (Install app)** | Chrome / Edge / Android “Add to…”, no browser chrome | 0 extra | Hub `manifest.json`. Fastest try in a browser. |
| **`launch.py` (this folder)** | Frameless Chrome `--app` window on `http://127.0.0.1:8765` | 0 extra | Needs Python 3 and Chrome/Edge. |
| **Tauri 2** | Signed `.exe` / `.dmg` / `.deb` when you have certs | ~8–15 MB | Starter in `desktop/tauri/`. Not required for the Go wrap. |

There is no good fifth option of “compile the HTML to native widgets.” The sheet is HTML
and CSS on purpose.

## Recommended sequence

### 1. Use what is already here

- The hub: open in Chrome or Edge → ⋮ → **Install Toastmasters Tools**.
- Local origin (needed for clipboard / FS Access):

      python3 desktop/serve.py

  Then open http://127.0.0.1:8765/ — hash routes `#home` `#finder` `#builder` `#timer` `#ah-counter`.

### 2. Windows, when Smart App Control blocks the `.exe`

Download [`desktop/dist/ToastmastersTools-portable.zip`](https://github.com/ramnaths89/toastmasters/raw/main/desktop/dist/ToastmastersTools-portable.zip).
Right-click the zip → Properties → **Unblock** → extract. Double-click
`Install.cmd` to put a **Toastmasters Tools** shortcut on the Desktop and in
the Start menu. After that, share the zip (or the extracted folder on a USB
stick) — not the `.exe`. `START.cmd` runs once without installing.

The unsigned `.exe` remains for PCs that only show SmartScreen (*More info* →
*Run anyway*).

**Programme sheet only.** The same pipeline builds a second app that opens the
builder and nothing else:
[`desktop/dist/ProgrammeSheet-portable.zip`](https://github.com/ramnaths89/toastmasters/raw/main/desktop/dist/ProgrammeSheet-portable.zip)
(Unblock → extract → `Install.cmd` → Desktop shortcut **Programme Sheet Builder**)
or [`desktop/dist/ProgrammeSheet.exe`](https://github.com/ramnaths89/toastmasters/raw/main/desktop/dist/ProgrammeSheet.exe).
It serves the builder on its own origin (`127.0.0.1:8770`) with its own
profile folder, so its Club Setup and working sheet are separate from the
builder inside the hub. Both apps can be open at the same time.

Rebuild all of it after any tool changes:

      python3 desktop/app/build.py          # both apps
      python3 desktop/app/build.py sheet    # programme sheet builder only

That also writes the portable zips. Details: [`desktop/app/README.md`](app/README.md).

### 3. Frameless browser window (Python)

      python3 desktop/launch.py

On Windows, double-click `launch.bat`. On macOS/Linux, `./launch.sh`. This starts the
local server if needed and opens Chrome/Edge with `--app=`. Close the window to quit.

### 4. Package with Tauri 2 (optional, signed store builds later)

From a machine with Rust and Node:

```bash
cd desktop/tauri
npx tauri icon ../../icon.svg
npm install
npm run tauri build
```

The starter points Tauri at the repo root (`frontendDist` = `../../..` from `src-tauri/`)
and opens `index.html`. Do **not** set the window URL to a `file://` path.

### 5. Native file dialogs (only if the builder needs them)

Today the builder uses:

- `localStorage` key `nse-programme-builder-v6`
- IndexedDB folder handles (`nse-progsheet-fs`) when Chromium offers `showDirectoryPicker`

In a Tauri window on Windows/Linux that picker is usually present (WebView2 / WebKitGTK).
On macOS WKWebView it is not. If Save-to-folder is required on every OS, add a small
Rust command (`save_meeting`, `open_meeting`) and call it from `06_app2.js` when
`window.__TAURI__` exists. Leave the browser path untouched so GitHub Pages keeps working.

PDF/JPG export already runs in-page via html2canvas. That works inside Tauri. Do not
route those through `window.print()`.

## What a wrapper must provide

| API | Used by | Notes |
|-----|---------|--------|
| `localStorage` | all four | Stable partition per install |
| `navigator.clipboard` | Timer, Ah-Counter, Finder | May need a permission grant in the webview |
| `navigator.wakeLock` | Timer | Often missing in embedded webviews; lights still work |
| `<audio>` + Blob URL | Timer bell | Works in WebView2 / WKWebView |
| File System Access + IndexedDB | Builder | Chromium yes; Safari/WKWebView no — see step 4 |
| `<a download>` | Builder, Ah-Counter, Finder | Works; Tauri can also hook it |

Storage keys a desktop shell should treat as user data:

- `d80.favourites.v1`
- `nse-programme-builder-v6`
- `ahcounter.log.v4`, `ahcounter.club`
- `timer.log.v1`
- `tm.shell.v1` (last hub tab)

## What not to change for a wrap

- `programme-sheet-builder/src/03_sheetcss.js` print rules and default segment durations
- Inlining the club-finder data into a different format unless you also keep a one-file
  GitHub Pages build
- Loading Google Fonts at runtime in the hub or Timer (already off). Ah-Counter V7
  loads Archivo when the network is there and falls back to the system stack offline.

## Local server

`desktop/serve.py` is stdlib only. It binds to localhost, sets no-cache headers so you
see edits, and refuses path escape. Stop it with Ctrl+C. `launch.py` starts it for you.
