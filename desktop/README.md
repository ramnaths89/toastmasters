# Wrapping these tools as a desktop app

The product is already four self-contained web pages. A standalone desktop app should
**open those pages in a native window**, not rewrite them. That keeps GitHub Pages, the
print layout, and every existing save file working.

## What “standalone” needs to mean here

Club laptops are the real target. The Timer and Ah-Counter run live in a meeting room.
The programme sheet builder is used at home or at the venue, often on whatever Wi-Fi is
going. A useful desktop build therefore has to:

- Open without a browser tab or address bar
- Work with no network
- Keep each tool’s `localStorage` on a stable origin (not `file://`)
- Let the builder write `.json` / PDF / JPG to disk
- Stay small enough to email or put on a USB stick

Rewriting in Swift / C# / Qt would throw away the programme sheet’s print geometry, which
sits about 4 mm from a third A4 page and is guarded by `pgprobe.py`. Do not do that.

## Options

| Path | What you get | Size | Fit |
|------|----------------|------|-----|
| **PWA (Install app)** | Chrome / Edge / Android “Add to…”, no browser chrome | 0 extra | Already works for Timer and Ah-Counter (`manifest.json`). Fastest way to try a standalone window. Safari on iPhone is “Add to Home Screen”. |
| **Tauri 2** | Real `.exe` / `.dmg` / `.deb` that embeds a system webview | ~8–15 MB | **Recommended.** Wraps the existing HTML. Rust compile once; after that, `tauri build` ships all four tools. |
| **Electron** | Same wrap, Chromium bundled | ~150 MB | Only if you need the exact Chrome File System Access API and cannot wait for a Tauri sidecar. |
| **Neutralino / pywebview** | Thin webview + local server | small | Fine for a personal launcher; weaker packaging and auto-update story. |

There is no good fifth option of “compile the HTML to native widgets.” The sheet is HTML
and CSS on purpose.

## Recommended sequence

### 1. Use what is already here

- Timer and Ah-Counter: open in Chrome or Edge → ⋮ → **Install TMtimer** / **Install Ah-Counter**.
- Club finder: already embeds fonts and data; it is the strongest offline page.
- Local preview of the whole hub:

      python3 desktop/serve.py

  Then open http://127.0.0.1:8765/ — this is the origin a packaged app should use too.

### 2. Package with Tauri 2 (the real desktop app)

From a machine with Rust and Node:

```bash
cd desktop/tauri
npm install
npm run tauri build
```

The starter in `desktop/tauri/` points Tauri at the repo root (`frontendDist` =
`../../..` from `src-tauri/`) and opens `index.html` as the first window. Generate
icons with `npx tauri icon path/to/icon.png` before the first `tauri build`. Each tool card still navigates to its folder.
Later, a native menu can open Timer / Ah-Counter / Builder / Finder in their own windows
(`WebviewWindow` per tool) so the Timer can sit fullscreen on the projector while the
Ah-Counter stays on the secretary’s laptop.

Do **not** set the window URL to a `file://` path. Serve from the bundled dist (Tauri
does this) or from the local server. `file://` shares one `localStorage` origin across
every copy of the builder and breaks the File System Access API.

### 3. Native file dialogs (only if the builder needs them)

Today the builder uses:

- `localStorage` key `nse-programme-builder-v6`
- IndexedDB folder handles (`nse-progsheet-fs`) when Chromium offers `showDirectoryPicker`

In a Tauri window on Windows/Linux that picker is usually present (WebView2 / WebKitGTK).
On macOS WKWebView it is not. If Save-to-folder is required on every OS, add a small
Rust command (`save_meeting`, `open_meeting`) and call it from `app2.js` when
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
| File System Access + IndexedDB | Builder | Chromium yes; Safari/WKWebView no — see step 3 |
| `<a download>` | Builder, Ah-Counter, Finder | Works; Tauri can also hook it |

Storage keys a desktop shell should treat as user data:

- `d80.favourites.v1`
- `nse-programme-builder-v6`
- `ahcounter.log.v4`, `ahcounter.club`
- `timer.log.v1`

## What not to change for a wrap

- `programme-sheet-builder/src/sheet.css` print rules and default segment durations
- Inlining the club-finder data into a different format unless you also keep a one-file
  GitHub Pages build
- Loading Google Fonts at runtime (already removed from the hub, Timer, and Ah-Counter)

## Local server

`desktop/serve.py` is stdlib only. It binds to localhost, sets no-cache headers so you
see edits, and refuses path escape. Stop it with Ctrl+C.
