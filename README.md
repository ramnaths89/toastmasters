# Toastmasters Tools

Small, single-page web tools for Toastmasters clubs and meetings, by Ramanathan S
(District 80, Singapore).

**Live:** https://ramnaths89.github.io/toastmasters/

Every tool is one self-contained `index.html` — fonts, styles, scripts and data are all
embedded. No build step, no dependencies, no server. They run entirely in the browser,
send nothing anywhere, and keep working offline once loaded.

## Tools

| Tool | Path | Notes |
|------|------|-------|
| D80 Club Meeting Finder | [`d80-club-finder/`](d80-club-finder/) | 217 District 80 clubs, filter by division / area / language / day / time / format. Data compiled 27 Jul 2026. |

## Adding a tool

1. Make a folder, e.g. `ah-counter/`.
2. Put the tool in it as `index.html`.
3. Add a card to the root `index.html` (copy the existing `<a class="tool">` block).
4. Add a row to the table above.
5. Commit and push — GitHub Pages redeploys in about a minute.

## Updating a tool

Replace that folder's `index.html` and push. The URL never changes, so links already
shared with club members keep working.

Note: the tools use `localStorage` for preferences such as starred clubs. Those are stored
per browser on the visitor's own device and are never sent anywhere.

## Housekeeping

- `.nojekyll` stops GitHub Pages from running Jekyll over the files, which would otherwise
  ignore any folder beginning with an underscore.
- Version history lives in git — the working copies numbered `V24`, `V25`, `V26` etc. stay
  in OneDrive and are not published here.

## Disclaimer

These are personal projects by an individual member. They are not official Toastmasters
International or District 80 publications and are not endorsed by either. Meeting data may
be out of date — always confirm with the club before attending. Toastmasters International,
District 80 and related marks are the property of Toastmasters International.
