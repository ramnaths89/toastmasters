# Toastmasters Tools

Small, single-page web tools for Toastmasters clubs and meetings, by Ramanathan S
(District 80, Singapore).

**Live:** https://ramnaths89.github.io/toastmasters/

Every tool is a single-page app with no server and no accounts. Styles, scripts and data live
in the page. The club finder also embeds its fonts; the others use the system font stack so they
open correctly with no network. Nothing is uploaded anywhere. Each tool keeps working offline
once the page itself is on the device.

A path to a double-clickable desktop app — wrap these pages, do not rewrite them — is in
[desktop/](desktop/).

Three of the four are written and edited as that single file. The programme sheet builder outgrew
it, so it is assembled from parts in `programme-sheet-builder/src/` and ships with the test suites
that guard it — see [Programme sheet builder: source and tests](#programme-sheet-builder-source-and-tests).

## Tools

| Tool | Path | For | Notes |
|------|------|-----|-------|
| D80 Club Finder | [`d80-club-finder/`](d80-club-finder/) | Anyone looking for a club to visit | All 217 District 80 clubs across 9 divisions and 45 areas, with meeting schedules expanded into real dates. Filter by division / language / day / time / format. Four tabs — Table, Calendar, Breakdown, Starred. Star clubs to get their whole year on one page with clash days flagged, and copy that list as a link. CSV, clipboard and Google Calendar export. Data compiled 29 Jul 2026 — not live. |
| Programme Sheet Builder | [`programme-sheet-builder/`](programme-sheet-builder/) | Toastmaster of the Day | Fill the panel on the left, the agenda redraws on the right. Official Pathways catalogue built in (project details, durations, timing lights). Club Setup is the first panel, so any club can put its own details on it — see [Customise it for your club](programme-sheet-builder/customise-for-your-club.md). Save a meeting as a `.json` file and reopen it later, or export HTML, a print-ready A4 PDF, or a JPG under 500 KB for WhatsApp. Officer names ship as placeholders, not real people. |
| TMtimer | [`timer/`](timer/) | Timer | Full-screen timing lights — white, green, amber, red, then a bell after a delay you set (30 s by default) — with presets for Prepared Speech, Table Topics and Evaluation, custom times, and a session log you can edit and copy for the Timer's report. Segments and times can be changed mid-speech and the lights follow. The log is saved in this browser (`timer.log.v1`). |
| The Ah-Counter's Log | [`ah-counter/`](ah-counter/) | Ah-Counter | One tap per crutch word, one row per speaker. Undo, remarks, keyboard shortcuts, and an end-of-meeting report you can copy or download as CSV. |

The landing page (`index.html`) groups the tools by when they're used: **before the
meeting** (planning and visiting) and **in the room** (meeting roles, live).

## Using these in another club

The tools are written for Nee Soon East but nothing is locked to it. The club finder is
district-wide. The timer and the Ah-Counter's log ask for nothing club-specific (the Ah-Counter's
log takes a club name in its header, remembered per browser). The programme sheet builder ships
with Nee Soon East as its factory defaults, and
[Customise it for your club](programme-sheet-builder/customise-for-your-club.md) covers both
routes: filling in Club Setup, which takes about five minutes and is remembered in your browser,
or editing `defaultState()` so your club survives a Reset and can be handed on as a finished file.

One field in there is easy to miss and prints on the sheet: **the Slido voting link and its
three room codes**, which ship as `NSE_1`, `NSE_2` and `NSE_3`. Leave them and your members
vote in Nee Soon East's polls. The guide's checklist covers them; searching the file for
"Nee Soon" does not.

## Adding a tool

1. Make a folder, e.g. `general-evaluator/`.
2. Put the tool in it as `index.html`.
3. Add a card to the root `index.html` — copy an existing `<a class="card">` block into
   the right phase section (`Before the meeting` or `In the room`).
4. Add a row to the table above.
5. Commit (or upload via the GitHub web UI) — GitHub Pages redeploys in about a minute.

## Updating a tool

Replace that folder's `index.html` and commit. The URL never changes, so links already
shared with club members keep working. The programme sheet builder is the exception — edit its
source and rebuild, as below.

Note on saved state. All four tools use `localStorage`, per browser on the visitor's own
device, never sent anywhere: the club finder keeps starred clubs (`d80.favourites.v1`), the
programme sheet builder keeps the working sheet (`nse-programme-builder-v6`), the Ah-Counter's
log keeps counts and the club name (`ahcounter.log.v4`, `ahcounter.club`), and TMtimer keeps
the session log plus light times (`timer.log.v1`). There are no accounts and no tracking. The
programme sheet builder can also write meetings to a folder you choose, using the browser's
File System Access API; those files stay on your own disk.

TMtimer does not persist a running clock — reload resets the seconds, not the recorded list.

## Programme sheet builder: source and tests

`programme-sheet-builder/index.html` is a build artifact — do not hand-edit it. It is assembled by
`src/build_generator.py`, which substitutes the parts into `skeleton.html`:

```
skeleton.html + builder.css + sheet.css + app.js + app2.js + pathways_data.json
              + ti-logo.b64 + h2c.js (html2canvas 1.4.1, MIT)
```

To change the tool: edit the relevant file in `src/`, run `python3 src/build_generator.py`, then
run the suites in `tests/` before committing. The script writes the gitignored
`src/NSE_Programme_Generator.html` and copies it over `index.html` in the same step — that used
to be manual, and forgetting it was the easiest way to test the old build and believe the new
one passed. `cmp src/NSE_Programme_Generator.html index.html` should now be a no-op after a
successful build.

The build script only ever substitutes — it must never write a part back. An earlier version
carried `builder.css` as an inline string and silently reverted weeks of edits. It also refuses to
build if `sheet.css` contains a backtick or `${`, because that CSS is injected into a JavaScript
template literal and either character would break the whole app at parse time.

The suites need Python Playwright and Chromium, plus `pdfinfo` (poppler-utils), and run against
the built `index.html`. **Run `pgprobe.py` first — it is the quickest and catches the worst
failure.** Status re-measured against the current build on 11 Aug 2026:

| Suite | Checks | Against this build |
|---|---|---|
| `pgprobe.py` | Page count per theme | passes — `ALL 2 PAGES` |
| `checkall.py` | Print geometry and a real PDF per theme, blank and filled | 10/10, about 72 s |
| `uicheck.py` | Toolbar, export sizes, PDF path | 19/22 — see below |
| `t13.py` | Functional behaviour end to end | **does not run** — raises a Playwright timeout on `.speech-card input` |
| `fscheck.py` | Saving and reopening meetings, incl. revoked folder permission | **does not run** — hangs past two minutes with no output |

Read that last pair literally. `t13.py` and `fscheck.py` do not report failures, they abort:
`t13.py` ends in a traceback and `fscheck.py` looks like a frozen machine. Both were written
before the interface gained the save dialog, custom roles and the speech-count spinner. Until
they are rewritten they are not a safety net, and running them will waste your time before it
tells you anything.

`uicheck.py`'s three remaining failures:

- **`renders at high res before downscaling`** measures 2154 px against an expectation set
  before the export was rewritten to render the print layout in V32. Nobody has looked at it
  since.
- **two toolbar failures**, both the same thing: *Balance Segments* is a text label where every
  other toolbar control is an icon with a tooltip, so the hover-tooltip check fails with it.

The fourth failure is gone: the JPG export measures 498 KB at 1500 px / q0.8, which is inside
the "under 500 KB" the Download menu promises. The assertion had been left behind at an older
450 KB and has been moved to 500 to match. **If you change the export width or quality, change
the menu text and the customise guide in the same commit** — those numbers drifted apart once
already, and the docs lost.

### The suites this build was actually verified with are not in this repo

V36 was built and checked against three suite trees that live only in
`progsheetV36-src-and-tests.zip` beside the working copy: `tests/features/` (12 files, 748
feature checks), `tests/json/` (17 save-and-recovery attack suites) and `tests/pane/` (the
print-pane fit measurements). The five suites published here are the V29-era set and cover a
fraction of what the tool now does — nothing here exercises saving, recovery, custom roles, the
Education Series or the two-tab lock. Treat a clean run of the published five as a smoke test,
not as clearance to ship.

`checkall.py` is the check that matters most: it measures the printed layout at **both** 794px and
718px, because A4's content width is 190mm ≈ 718px at 96dpi, which is under the 720px mobile
breakpoint. A width media query written without `screen and` therefore fires on paper but not in a
headless test. Any new width query in `sheet.css` must be scoped `@media screen and (max-width: …)`.

**The sheet sits about 4 mm from the two-page boundary.** Adding a single line to any row has tipped
themes onto a third page before now. Never ship a row or line change without running `pgprobe.py`.

## A standalone desktop app

These tools are already the app. A desktop build should wrap the existing HTML, not start
again in Swift, C# or Electron-from-scratch. The options, trade-offs and a local preview
server live in [desktop/](desktop/). Short version:

1. **Install from Chrome / Edge** — the timer and Ah-Counter already ship a web app manifest
   (`display: standalone`). On a club laptop that is often enough: menu → *Install…* and the
   browser chrome goes away.
2. **Tauri 2** — the real double-clickable `.exe` / `.app` / `.deb`. A ~10 MB window that
   loads these files from disk. Native file dialogs can later replace the builder's
   Chrome-only File System Access API.
3. **Electron** — same wrap, much larger binaries. Only if Tauri is a poor fit.

Do not load the pages as `file://`. Several APIs (clipboard, storage origin, File System
Access) need a real origin. `python3 desktop/serve.py` gives you `http://127.0.0.1:8765`
for local testing, which is also how a Tauri window should load them.

## Housekeeping

- `.nojekyll` stops GitHub Pages from running Jekyll over the files, which would otherwise
  ignore any folder beginning with an underscore.
- `.gitignore` covers the HTML and PDF artifacts the test suites drop into `tests/`, the
  builder's own output in `src/`, and desktop build folders.
- Numbered working copies (`V27`, `V28`, `V29` …) stay in OneDrive; git carries the history here.

## Disclaimer

These are personal projects by an individual member, shared while still in development —
expect rough edges. They are not official Toastmasters International or District 80
publications and are not endorsed, reviewed or supported by either. Meeting data may be
out of date — always confirm with the club before attending. Toastmasters International,
District 80 and related marks are the property of Toastmasters International.
