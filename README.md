# Toastmasters Tools

Small, single-page web tools for Toastmasters clubs and meetings, by Ramanathan S
(District 80, Singapore).

**Live:** https://ramnaths89.github.io/toastmasters/

Every tool is served as one self-contained `index.html` — fonts, styles, scripts and data are
all embedded. Nothing is fetched at runtime, there is no server, and each tool runs entirely in
the browser, sends nothing anywhere, and keeps working offline once loaded.

Three of the four are written and edited as that single file. The programme sheet builder outgrew
it, so it is assembled from parts in `programme-sheet-builder/src/` and ships with the test suites
that guard it — see [Programme sheet builder: source and tests](#programme-sheet-builder-source-and-tests).

## Tools

| Tool | Path | For | Notes |
|------|------|-----|-------|
| D80 Club Finder | [`d80-club-finder/`](d80-club-finder/) | Anyone looking for a club to visit | All 217 District 80 clubs across 9 divisions and 45 areas, with meeting schedules expanded into real dates. Filter by division / language / day / time / format; calendar, map with near-me, starred clubs, CSV and Google Calendar export. Data compiled 29 Jul 2026 — not live. |
| Programme Sheet Builder | [`programme-sheet-builder/`](programme-sheet-builder/) | Toastmaster of the Day | Fill the panel on the left, the agenda redraws on the right. Official Pathways catalogue built in (project details, durations, timing lights). Club Setup is the first panel, so any club can put its own details on it — see [Customise it for your club](programme-sheet-builder/customise-for-your-club.md). Save a meeting as a `.json` file and reopen it later, or export HTML, a print-ready A4 PDF, or a JPG under 450 KB for WhatsApp. Officer names ship as placeholders, not real people. |
| TMtimer | [`timer/`](timer/) | Timer | Full-screen timing lights — white, green, amber, red, bell 30 s after red — with presets for Prepared Speech, Table Topics and Evaluation, custom times, and a session log you can copy for the Timer's report. |
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

Note: the tools use `localStorage` for saved state — starred clubs, the working programme
sheet, timer logs and counts. That state lives per browser on the visitor's own device and is
never sent anywhere. There are no accounts and no tracking. The programme sheet builder can also
write meetings to a folder you choose, using the browser's File System Access API; those files
stay on your own disk.

## Programme sheet builder: source and tests

`programme-sheet-builder/index.html` is a build artifact — do not hand-edit it. It is assembled by
`src/build_generator.py`, which substitutes the parts into `skeleton.html`:

```
skeleton.html + builder.css + sheet.css + app.js + app2.js + pathways_data.json
              + ti-logo.b64 + h2c.js (html2canvas 1.4.1, MIT)
```

To change the tool: edit the relevant file in `src/`, run `python3 src/build_generator.py`, copy
the generated HTML over `index.html`, then run the suites in `tests/` before committing.

The build script only ever substitutes — it must never write a part back. An earlier version
carried `builder.css` as an inline string and silently reverted weeks of edits. It also refuses to
build if `sheet.css` contains a backtick or `${`, because that CSS is injected into a JavaScript
template literal and either character would break the whole app at parse time.

The suites need Python Playwright and Chromium, and run against the built `index.html`:

| Suite | Checks |
|---|---|
| `t13.py` | Functional behaviour end to end — 98 checks |
| `fscheck.py` | Saving and reopening meetings, including revoked folder permission — 30 checks |
| `uicheck.py` | Export sizes, timing-light bells, PDF path — 22 checks |
| `checkall.py` | Print geometry and a real PDF per theme, blank and filled — 12 cases |
| `pgprobe.py` | Page count per theme |

162 checks in total. `checkall.py` is the one that matters most: it measures the printed layout at
**both** 794px and 718px, because A4's content width is 190mm ≈ 718px at 96dpi, which is under the
720px mobile breakpoint. A width media query written without `screen and` therefore fires on paper.
Any new width query in `sheet.css` must be scoped `@media screen and (max-width: …)`.

## Housekeeping

- `.nojekyll` stops GitHub Pages from running Jekyll over the files, which would otherwise
  ignore any folder beginning with an underscore.
- `.gitignore` covers the HTML and PDF artifacts the test suites drop into `tests/`.
- Numbered working copies (`V27`, `V28`, `V29` …) stay in OneDrive; git carries the history here.

## Disclaimer

These are personal projects by an individual member, shared while still in development —
expect rough edges. They are not official Toastmasters International or District 80
publications and are not endorsed, reviewed or supported by either. Meeting data may be
out of date — always confirm with the club before attending. Toastmasters International,
District 80 and related marks are the property of Toastmasters International.
