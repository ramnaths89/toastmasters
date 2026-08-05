# Toastmasters Tools

Small, single-page web tools for Toastmasters clubs and meetings, by Ramanathan S
(District 80, Singapore).

**Live:** https://ramnaths89.github.io/toastmasters/

Every tool is one self-contained `index.html` — fonts, styles, scripts and data are all
embedded. No build step, no dependencies, no server. They run entirely in the browser,
send nothing anywhere, and keep working offline once loaded.

## Tools

| Tool | Path | For | Notes |
|------|------|-----|-------|
| D80 Club Finder | [`d80-club-finder/`](d80-club-finder/) | Anyone looking for a club to visit | All 217 District 80 clubs across 9 divisions and 45 areas, with meeting schedules expanded into real dates. Filter by division / language / day / time / format; calendar, map with near-me, starred clubs, CSV and Google Calendar export. Data compiled 29 Jul 2026 — not live. |
| Programme Sheet Builder | [`programme-sheet-builder/`](programme-sheet-builder/) | Toastmaster of the Day | Fill the panel on the left, the agenda redraws on the right. Official Pathways catalogue built in (project details, durations, timing lights). Club Setup panel lets any club put its own name and number on it. Exports HTML, print-ready A4 PDF, or a JPG under 450 KB for WhatsApp. |
| TMtimer | [`timer/`](timer/) | Timer | Full-screen timing lights — white, green, amber, red, bell 30 s after red — with presets for Prepared Speech, Table Topics and Evaluation, custom times, and a session log you can copy for the Timer's report. |
| The Ah-Counter's Log | [`ah-counter/`](ah-counter/) | Ah-Counter | One tap per crutch word, one row per speaker. Undo, remarks, keyboard shortcuts, and an end-of-meeting report you can copy or download as CSV. |

The landing page (`index.html`) groups the tools by when they're used: **before the
meeting** (planning and visiting) and **in the room** (meeting roles, live).

## Adding a tool

1. Make a folder, e.g. `general-evaluator/`.
2. Put the tool in it as `index.html`.
3. Add a card to the root `index.html` — copy an existing `<a class="card">` block into
   the right phase section (`Before the meeting` or `In the room`).
4. Add a row to the table above.
5. Commit (or upload via the GitHub web UI) — GitHub Pages redeploys in about a minute.

## Updating a tool

Replace that folder's `index.html` and commit. The URL never changes, so links already
shared with club members keep working.

Note: the tools use `localStorage` for saved state — starred clubs, saved programme
sheets, timer logs and counts. That state lives per browser on the visitor's own device
and is never sent anywhere. There are no accounts and no tracking.

## Housekeeping

- `.nojekyll` stops GitHub Pages from running Jekyll over the files, which would otherwise
  ignore any folder beginning with an underscore.
- Version history lives in git — the numbered working copies (`V24`, `V25`, `V26` …) stay
  in OneDrive and are not published here.

## Disclaimer

These are personal projects by an individual member, shared while still in development —
expect rough edges. They are not official Toastmasters International or District 80
publications and are not endorsed, reviewed or supported by either. Meeting data may be
out of date — always confirm with the club before attending. Toastmasters International,
District 80 and related marks are the property of Toastmasters International.
