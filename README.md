# Toastmasters Tools

Unofficial single-page tools for Toastmasters clubs and meetings, by Ramanathan S
(Nee Soon East, District 80, Singapore). **V48.**

**Live:** https://ramnaths89.github.io/toastmasters/

Every tool is a single-page app with no server and no accounts. Styles, scripts and data live
in the page. The club finder also embeds its fonts; the others use the system font stack so they
open correctly with no network. Nothing is uploaded anywhere. Each tool keeps working offline
once the page itself is on the device.

The root page is **one app** with all four tools. Switching tabs keeps a running timer
alive. Each tool still has its own URL for a second screen or a bookmark.

A double-clickable Windows app — same HTML, a real `http://127.0.0.1` origin —
is `desktop/dist/ToastmastersTools.exe`. Rebuild with `python3 desktop/app/build.py`.
Tauri 2 remains in `desktop/tauri/` if you later want a signed store bundle.

Three of the four are written and edited as that single file. The programme sheet builder
is assembled from numbered parts in `programme-sheet-builder/src/` — see
[programme-sheet-builder/README.md](programme-sheet-builder/README.md).

## Tools

| Tool | Path | For | Notes |
|------|------|-----|-------|
| D80 Club Finder | [`d80-club-finder/`](d80-club-finder/) | Anyone looking for a club to visit | All 217 District 80 clubs across 9 divisions and 45 areas, with meeting schedules expanded into real dates. Filter by division / language / day / time / format. Four tabs — Table, Calendar, Breakdown, Starred. Star clubs to get their whole year on one page with clash days flagged, and copy that list as a link. CSV, clipboard and Google Calendar export. Data compiled 29 Jul 2026 — not live. |
| Programme Sheet Builder **V48** | [`programme-sheet-builder/`](programme-sheet-builder/) | Toastmaster of the Day | Fill the panel on the left, the agenda redraws on the right. **Chapter meeting or speech contest.** Official Pathways catalogue built in. Club Setup is the first panel — see [Customise it for your club](programme-sheet-builder/customise-for-your-club.md). Contest blocks size themselves from the contestant count (or take a typed length); appointment holders print in the order you set with ▲▼; Language Evaluation and Ah-Counter's Report rows follow the ticks. Break flexes 10–20 min. Save as `.json`; export HTML, A4 PDF, or a JPG under 500 KB. Officer names ship as placeholders, not real people. |
| TMtimer | [`timer/`](timer/) | Timer | Full-screen timing lights — white, green, amber, red, then a bell after a delay you set (30 s by default) — with presets for Prepared Speech, Table Topics and Evaluation, custom times, and a session log you can edit and copy for the Timer's report. The log is saved in this browser (`timer.log.v1`). |
| The Ah-Counter's Log **V7** | [`ah-counter/`](ah-counter/) | Ah-Counter | One tap per crutch word, one row per speaker. Two-column word list. Undo, remarks, keyboard shortcuts, and an end-of-meeting report you can copy or download as CSV. |

The hub (`index.html`) is a Loyal Blue home in official Toastmasters colours
(Loyal Blue, Fair Red, Happy Yellow, True Maroon, Cool Gray), with marquees,
count-up stats and hover motion. It groups the tools
by **before the meeting** and **in the room**,
plus a tab bar that opens each tool inside the same page (`#finder`, `#builder`,
`#timer`, `#ah-counter`). Individual folder URLs still work on their own — use those
when the Timer needs a projector and the Ah-Counter needs a second laptop. Chrome / Edge
can **Install** the hub as a standalone window (`manifest.json`).

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
vote in Nee Soon East's polls. Clear the link and all three codes and the voting lines stop
printing. The guide's checklist covers them; searching the file for "Nee Soon" does not.

## Adding a tool

1. Make a folder, e.g. `general-evaluator/`.
2. Put the tool in it as `index.html`.
3. Add a card on the Home screen in the root `index.html` — copy an existing
   `<a class="card" href="#…" data-nav="…">` block into the right phase section.
4. Register it in the hub script: a `TOOLS` entry, a tab `<button data-nav="…">`,
   and an `<iframe class="pane" id="frame-…">`.
5. Add a row to the table above.
6. Commit — GitHub Pages redeploys in about a minute.

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

`programme-sheet-builder/index.html` is a build artifact — do not hand-edit it. V48 uses the
numbered-part pipeline from V44:

```
00_head_open.html + 01_builder.css + 02_body.html + 03_sheetcss.js
                  + 04_h2c.js + 05_app.js + 06_app2.js + 07_tail.html
```

```
cd programme-sheet-builder
python3 build.py ProgSheetGenV48.html
python3 publish.py index.html
```

`publish.py` strips officer names to `<President Name>`-style placeholders (already the
state of git `src/`) and **refuses** to write a file that still contains one. Club identity
stays. `build.py` refuses a backtick or `${` in the sheet CSS, a literal `</script>` in a
script part, and raw control characters.

The suites in `tests/` need Python Playwright, Chromium, and `pdfinfo` (poppler). They default
to this folder's `index.html`. **Run a page-count probe before shipping any change that
touches a row or a line** — `tests/pgprobe.py` or `tests/pane/pgprobe5.py`. The sheet sits
about 4 mm from the two-page boundary.

`test_11_v34_markdown` is deliberately not in `run_all`: Markdown save was removed in V35.

Do not re-add `column-count` on the reference pane. Do not change print CSS without a
page-count probe. Full working notes: [programme-sheet-builder/HANDOVER.md](programme-sheet-builder/HANDOVER.md).

## A standalone desktop app

These tools are already the app. A desktop build wraps the existing HTML. Short version:

1. **`desktop/dist/ToastmastersTools-portable.zip`** — Windows standalone.
   Unblock the zip, extract, double-click `Install.cmd` for a Desktop shortcut.
   Share that zip (or the folder on a USB). Smart App Control does not block it.
2. **`desktop/dist/ToastmastersTools.exe`** — Windows 64-bit, all four tools embedded.
   Double-click. Unsigned: SmartScreen can *Run anyway*; Smart App Control (pink **Okay**)
   cannot. Rebuild both: `python3 desktop/app/build.py`.
3. **Install from Chrome / Edge** — hub `manifest.json`, `display: standalone`.
4. **`python3 desktop/launch.py`** — local origin + frameless Chrome/Edge `--app`.
5. **Tauri 2** — starter in `desktop/tauri/` for a later signed bundle.

Do not load the pages as `file://`. Details: [desktop/](desktop/).

## Housekeeping

- `.nojekyll` stops GitHub Pages from running Jekyll over the files.
- `.gitignore` covers generated monoliths, test artifacts, and desktop build folders.
- Numbered working copies (`V45`, `V48`, …) stay in OneDrive; git carries the published history here.
- Never overwrite an existing V-file — always increment.

## Disclaimer

These are personal projects by an individual member, shared while still in development —
expect rough edges. They are not official Toastmasters International or District 80
publications and are not endorsed, reviewed or supported by either. Meeting data may be
out of date — always confirm with the club before attending. Toastmasters International,
District 80 and related marks are the property of Toastmasters International.
