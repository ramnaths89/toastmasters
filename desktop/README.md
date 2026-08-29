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
| **PWA (Install app)** | Chrome / Edge / Android “Add to…”, no browser chrome | 0 extra | Hub `manifest.json`. Fastest try. |
| **`launch.py` (this folder)** | Frameless Chrome `--app` window on `http://127.0.0.1:8765` | 0 extra | **The working desktop app today.** Needs Python 3 and Chrome/Edge/Chromium. |
| **Tauri 2** | Real `.exe` / `.dmg` / `.deb` that embeds a system webview | ~8–15 MB | Next step for a signed double-clickable. Icons via `npx tauri icon ../../icon.svg`. |
| **Electron** | Same wrap, Chromium bundled | ~150 MB | Only if you need Chrome File System Access on every OS and cannot wait for a Tauri sidecar. |

There is no good fifth option of “compile the HTML to native widgets.” The sheet is HTML
and CSS on purpose.

## Recommended sequence

### 1. Use what is already here

- The hub: open in Chrome or Edge → ⋮ → **Install Toastmasters Tools**.
- Local origin (needed for clipboard / FS Access):

      python3 desktop/serve.py

  Then open http://127.0.0.1:8765/ — hash routes `#home` `#finder` `#builder` `#timer` `#ah-counter`.

### 2. Frameless desktop window

      python3 desktop/launch.py

On Windows, double-click `launch.bat`. On macOS/Linux, `./launch.sh`. This starts the
local server if needed and opens Chrome/Edge with `--app=`. Close the window to quit.
**This is not a signed installer.** It is the wrap that actually runs without icon
generation or code-signing certificates.

### 3. Package with Tauri 2 (when you want a `.exe`)

From a machine with Rust and Node:

```bash
cd desktop/tauri
npx tauri icon ../../icon.svg
npm install
npm run tauri build
```

The starter points Tauri at the repo root (`frontendDist` = `../../..` from `src-tauri/`)
and opens `index.html`. Do **not** set the window URL to a `file://` path.

### 4. Native file dialogs (only if the builder needs them)

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
- Loading Google Fonts at runtime in the hub, Timer, or Ah-Counter (already off)

## Local server

`desktop/serve.py` is stdlib only. It binds to localhost, sets no-cache headers so you
see edits, and refuses path escape. Stop it with Ctrl+C. `launch.py` starts it for you.
