# Handover — NSE Programme Sheet Builder

Paste this into a new chat to pick the project up cold. Written 11 Aug 2026,
updated 2 Sep 2026 for **V48**.

**V48** is V45 plus V46–V48, all driven by Rama's 24 Sep 2026 contest sheet:

- **V46** — a contest block's length is computed from its contestant count
  (`contestBlockMinutes`: Table Topics 3.5, Evaluation 4.5 min per contestant
  + 5), not stretched by Balance; "Participants" heading, "not in any particular
  order" note and a per-block `comments` line print under the list; the FLEXIBLE
  chip and range are gone from the printed row; Evaluation half runs Briefing
  (3) → Test Speaker (9) → Holding Room (7) → Contest; certificates go to the
  Contest Toastmaster.
- **V47** — `state.roleOrder` {chapter, contest}: ▲▼ arrows in the roles form
  reorder every printed list of appointment holders. Language Evaluator now
  owns two rows (Word of the Day 2 min, Language Evaluation 8 min) and the
  Ah-Counter tick adds an Ah-Counter's Report (2 min); both sit after
  `evalvote`. Print-uniform set gains `text-transform`, chip borders, thead rule.
- **V48** — custom roles join the order (`orderedRoleEntries`) and are no longer
  printed twice; a typed contest length wins (`durManual`, "↺ use the estimate"
  hands it back); Test Speaker is `noBell` + `fixedSignals` 5/6/7 in a 9-min slot
  with a struck bell on the sheet; `csaa3` "Contest SAA 3" (unticked by default);
  a custom role whose label matches a built-in folds into it on load; Test
  Speaker defaults to "TBA @ Contest"; Rama's contest durations replace the
  estimates; Photography Session row removed ("Closing Address | Photo Taking").

The published copy uses officer **placeholders**; iframe handlers are
`(window.fn||parent.fn)` so the builder still edits inside the mega-app shell.
`python3 publish.py index.html` from this folder. Next version is **V49**.
Never overwrite an existing V-file.

---

# Handover (V44 text, still the source of truth for print geometry)

Written 11 Aug 2026. Current OneDrive file **V48**; this tree is **V48**.
Supersedes the 11 Aug V37 handover.

---

## What it is

A **single-file HTML app** that builds the meeting agenda ("programme sheet") for **Nee Soon East
Toastmasters Club, District 80**. Open it in a browser: no server, no install, no network call.
Form pane on the left, live preview of the printable sheet on the right.

**Current file: `ProgSheetGenV44.html`** (~616 KB) in
`C:\Users\ramna\OneDrive\10_Toastmasters\61_AItools\`. Next version is V45.
**Never overwrite an existing V-file, always increment.**

**Owner: Rama (Ramanathan S)**, VP Education. He tests by eye on real printouts and exports and
has repeatedly caught defects that every automated check passed. **When he says something looks
wrong and a test says it is fine, distrust the test first.** That has been right every time.

---

## How to work on it

This folder holds `src/`, `build.py`, `publish.py` and every test harness.
Edit `src/`, run `python3 build.py ProgSheetGenV48.html`, then
`python3 publish.py index.html` for the GitHub copy.

If the zip is lost, the monolith splits back into parts at exact byte offsets. Split any V-file by
locating its `<style>` and `<script>` boundaries; the order is always:

| part | contents |
|---|---|
| `00_head_open.html` | doctype, head, fonts link |
| `01_builder.css` | the builder UI |
| `02_body.html` | the form markup, help overlay, save dialog, notice bars |
| `03_sheetcss.js` | `SHEET_CSS` (the printed sheet, all themes + `@media print`), `PATHWAYS_DATA`, `LOGO_B64` |
| `04_h2c.js` | html2canvas 1.4.1, bundled |
| `05_app.js` | state, presets, `defaultState()`, `adoptState()`, Pathways plumbing |
| `06_app2.js` | rendering, interaction, exports, file saving, recovery, pane-fit |
| `07_tail.html` | closing tags |

Script blocks are separated by the literal `</script>` newline `<script>`.
**Verify the round trip is byte-identical before changing anything.**

**Three build traps, each has broken the app before. `build.py` refuses on all three:**
1. `03_sheetcss.js` is injected into a **JS template literal**. A backtick or a `${` anywhere in
   it, *including inside a comment*, silently kills the whole app.
2. A bundled library containing a literal `</script>` would close the tag early.
3. **A raw control character in any source part** (V36). A literal NUL typed into a JS string is
   legal JavaScript and invisible: it turns every `grep` on the file into "binary file matches"
   and stops `diff` and `patch` working. One arrived in `06_app2.js` via a separator meant to be
   an escape sequence and pasted as the character itself.

**Everything in `06_app2.js` is one `<script>` block, so a duplicate `const` is a hard
SyntaxError that kills the entire app.** `PX_PER_MM`, `PRINT_W_MM` and `PRINT_H_MM` already exist
near the export code; re-declaring them for the pane-fit measurement took the app down until
`node --check` caught it. After every build:

```
python3 -c "import re;s=open('ProgSheetGenV44.html',encoding='utf-8').read();open('/tmp/a.js','w',encoding='utf-8').write('\n;\n'.join(re.findall(r'<script>(.*?)</script>',s,re.S)))"
node --check /tmp/a.js
```

---

## Testing

Roughly 100 harnesses across four suites. **V37 is green at 759/759 feature checks.**

- `tests/features/` — eleven live suites (1–10, 12), 748 checks. `run_all.py` runs them and prints
  one table. Point it at the build with `V34=<path>` (the harness's variable name is historical;
  it means TARGET) and `V33=`…`V29=` for the regression baselines.
  **`test_11_v34_markdown` is deliberately not in `run_all`** — it covers the Markdown import that
  V34 added and V35 removed, so it is a guaranteed red that trains people to skim the table.
- `tests/json/` — the save/load attack suite, driven by an in-memory fake directory handle
  (`fakefs.js`) that runs the File System Access paths headless. Set `PSB_BUILD=<path>`; it used
  to be hardcoded to V35, which meant the whole suite silently kept testing the previous build.
  `t17_v36.py` is the end-to-end suite for the V36 save work.
- `tests/pane/` and `tests/diag/` — print geometry, page counts, the reference pane, PDF seams,
  logo aspect, real-print comparison. `warnprobe.py` measures the pane-fit technique against real
  print emulation; `panefit.py` is the ground truth.
- `tests/layoutsweep.py` (V37) — one row per viewport width: the container's display and
  flex-direction, the splitter, the tabs, the panes. **Read `display`, not `flexDirection`:**
  the one-pane view stacks with `display:block`, where `flex-direction` still computes as
  `row` and will tell you a column layout is a row.
- `tests/scrollprobe.py`, `scrollbisect.py`, `scrolltry.py` (V36) — attribute horizontal overflow
  by **hiding elements one at a time** and re-reading `scrollWidth`. Reconstructing pseudo-element
  geometry from computed styles found nothing; bisection named the culprit in one run.

Environment: Playwright + Chromium at `/opt/pw-browsers` (`PLAYWRIGHT_BROWSERS_PATH` set), plus
`pdfinfo`/`pdftotext`/`pdftoppm` from poppler. Block http/https in the Playwright context with the
route pattern `http*://**` — **not** `**://*`, which aborts the `file://` document too.

**Run the page-count probe before shipping any change that touches a row or a line.**
`tests/pane/pgprobe5.py` covers five themes × {blank, blank+LE, filled, filled+LE}; all twenty
must be 2 pages. V36: 20/20.

---

## Hard-won lessons, do not relearn these

- **The exports do not use `@media print`.** They rasterise a copy of the sheet in an iframe.
  Anything that exists only in the print block has to be reproduced by hand in the export path.
- **html2canvas CLONES the document and clones the `<style>` NODES**, so it re-parses the original
  CSS text. Mutating the CSSOM (`r.media.mediaText = 'all'`) measures correctly and renders
  wrong. Re-emit the rules as a real stylesheet instead. **The pane-fit check (V36) mutates the
  CSSOM on purpose** — it only ever measures, and nothing is rendered from that frame.
- **Headless print-to-PDF is not a real print preview.** Every width media query in the sheet CSS
  must be `screen and`. That cost six versions of a mystery grey line.
- **The two-page boundary is close, and raw height lies.** `break-inside: avoid` quantises the
  page-1 break to a whole row, so ~25 mm of apparent spare buys nothing. Count real PDF pages.
- **html2canvas has no `object-fit`.** Size the logo by neither axis, with a ceiling on both.
- **Adjacent margins collapse.** Pushing a block down the page needs a spacer element.
- **`newSegment()` runs inside `defaultState()` while `state` is in its temporal dead zone.**
- **`Object.assign(target, 'abc')` spreads a string into `{0:'a',...}`.** Filter to plain objects.
- **Measure layout with `offsetWidth`, not `getBoundingClientRect()`.**
- **Grain in exports is bits-per-pixel, not bytes.** Cap resolution, spend the budget on quality.
- **`--print-head` is a trap.** The banner box is 125px and its content measures 126–129px.
- **Two breakpoints for one decision is one breakpoint too many.** The CSS stacked the panes at
  980px while the tabs and the hidden splitter arrived at 900px, so 901–980 was a state nobody
  designed: stacked panes, no tabs, and the splitter still in the flow as a full-width 8px bar
  with `cursor:col-resize` — still driving `applyPaneWidth()`, whose `flex-basis` is a HEIGHT in a
  column container, so dragging it set the form pane's height from a horizontal mouse position.
  V37 keeps the split down to 900 and switches to tabs below it, full stop. `tests/layoutsweep.py`
  prints the layout at every width; suite 12 pins the switch at exactly 900/901.
- **A test that asserts a known bug is a trap for the build that fixes it.** V31's suite pinned the
  19px scroll as "the residual is the #dlBtn tooltip" and "the previous build measures the same",
  so V36 failed two checks by fixing them. Pin the *measurement*, not the defect.

---

## Feature history

**V1–V29** — core builder, Pathways catalogue with official timings, timing lights, drag-reorder,
six themes, club standard timings, Slido voting rows, icon toolbar, JPG/PDF export, a hand-rolled
60-line PDF writer, meetings saved as `.json` on disk with autosave, in-page PDF on every device.

**V30** — Save dialog with a custom filename; the 2025 Pathways Education Series at Levels 3/4/5;
one-pane-at-a-time layout under 900px; custom roles; the PDF reference-pane repair; the agenda
compacted so the Language Evaluator fits.

**V31** — speech cards collapse with a `[−] n [+]` speaker count; Handmade retired (five themes);
PNG dropped; every form section shut on load; the printed reference pane compacted.

**V32** — the exports render the **print** layout; real pagination with spacers; a canvas-size
guard; a resolution ladder under the 500 KB cap.

**V33** — configurable voting link and codes; an add-item bar at the top of the running order;
club initials derived from the club name; the save filename re-stamped with the actual time.

**V34** — the whole sheet round-tripped as one Markdown file. **Removed in V35.**

**V35** — Markdown save/import removed; JSON is the only format; the save path rebuilt over five
rounds of adversarial testing (29 defects, 13 standing and 16 introduced while fixing).

**V36** — the horizontal scroll fixed; a Ctrl+P clipping warning for the reference pane; torn- and
stale-write recovery; an advisory two-tab lock; a repeatable publish build.

**V38–V42** — Evaluation and Feedback split across 1st/2nd Speech; the open-roles notice kept out of
every export; the export seam finally traced to `column-count` fragmenting the pane and fixed (V39);
the logo/banner join (V41); Neo Memphis Pop replacing Retro-Futurism (V42).

**V44** — the JPG cut fixed, the Break widened to 10-20 min, and the flex balance made exact.
See "The JPG footer overlap" below.

**V43** — **contest mode.** `state.meeting.mode` is `'chapter'` (default) or `'contest'`. See the
section below.

**V37** — the export canvases forced onto Chrome's CPU backing store, against the vertical seam in
Rama's PDF and JPG (**unconfirmed: see the open items**); and the 901–980px layout band closed.

---

---

## Contest mode (V43)

`state.meeting.mode` — `'chapter'` (default) or `'contest'`. A file written before V43 carries no
mode and loads as a chapter meeting, which is what it is.

**What the mode changes, and nothing else does:**

- **The running order.** `buildModeSegments(mode)` lays down one of two templates. The contest one
  is 21 rows totalling **165 min**, so 18:45 lands on 21:30. Seventeen new PRESETS, all prefixed
  `c` (`csetup`, `cbriefjudges`, `cdraw`, `contest`, `ccollect`, `cresults`, …).
- **The role set.** `CONTEST_ROLE_LABELS` — thirteen appointments — replaces `ROLE_LABELS` through
  `modeRoleLabels()`. **Both sets live in the one `state.roles` object**, so switching to a contest
  and back does not lose the chapter roster. `roleLabelMap()`, `rolePlayerLines()` and
  `openRoleLabels()` all read the live mode's set, so a blank chapter role is not chased during a
  contest.
- **The printed pane.** The Contest Committee replaces the Executive Committee and the Pathways
  legend is dropped (a contest schedules no Pathways project, and dropping eleven lines is what
  makes room). District Officers, Links and Announcements stay.
- **The form.** Speeches & Evaluators is hidden and Contestants is shown, both by body class
  (`mode-contest` / `mode-chapter`) set in `syncModeControls()`.

**The contest block is the only new KIND of segment.** `isContestants: true`, and it carries
`contestants: []` — a numbered list rendered under the row title instead of a single holder. It is
one grid column and **must stay that way**: `column-count` is what fragmented the pane and produced
the export seam that cost V37–V39.

**Two things here have already bitten and are now pinned by tests:**

1. **`runningOrderIsPristine()` must compare the WHOLE segment, not a list of fields.** The first
   version whitelisted eight fields and missed five a user can edit — pathway, level, the timing
   lights, `signalsManual`, the sub-note and the flex range. Editing any of them and switching mode
   replaced the running order **with no confirm**, and `setMeetingMode()` then autosaved the wiped
   order over the file on disk. It now fingerprints every key except `id`, biased toward "not
   pristine": a false negative costs one dialog, a false positive costs an evening's work.
2. **`paneFitSignature()` must include the mode and the roles.** The contest pane's height depends
   on thirteen appointments; leaving them out meant the Ctrl+P clipping warning was computed from
   the chapter pane and stayed hidden while the contest pane overflowed the page by ~6 mm.

**Also settled:**

- `ROLE_OWNED_SEGMENTS` gives contest rows to exactly two appointments — Test Speaker owns the test
  speech (a Table Topics contest has none), Photographer owns the photo session. The rest own
  nothing on purpose: the room is still set up and the ballots still collected when a club fields
  one SAA instead of two.
- The Area Director is in `COMMITTEE_EXCLUDES` — they hold an appointment (the closing address) but
  print under District Officers, not twice in the same column.
- Custom roles print in the Contest Committee. They reach the chapter sheet via `rolePlayerLines()`
  on the TME Welcome Remarks row, which a contest has no equivalent of.
- Switching mode carries the clock **only if it is still the outgoing mode's default**, so a club
  that meets 19:30–22:00 keeps its own times.
- The two Add dropdowns are rendered by `renderAddOptions()` from `ADD_OPTIONS`, not static markup.

**Tests:** `tests/features/test_13_v43_contest.py`, 80 checks, in `run_all`. `tests/pgcontest.py`
counts contest pages at 0/0, 6/6, 10/10 and 10/10-with-long-names across five themes — all 2 pages.

---

---

## The JPG footer overlap (V44)

Rama's exported JPG ended mid-row: the last line of the agenda was sliced in half by the footer band.

**It was not a density problem, and compacting the sheet would have hidden it.** The export's fix
stylesheet pins `footer{position:absolute; bottom:0}`, so the footer contributes NOTHING to
`page.scrollHeight`. `natural()` is therefore the height of the content alone, and painting an opaque
footer at the bottom of a page that tall lands it ON TOP of the last row.

The PDF never showed it because pagination rounds the page up to whole sheets, which leaves slack
below the last row by construction. The JPG does not paginate on purpose - a single image would just
gain a band of white - so the non-paginated branch now adds the footer's height explicitly.

Measured on his 27 Aug sheet: content ended at 1690 px, the canvas was cut at 1674. The missing 16 px
is the overlap; the row it ate was "Club President Adjourns Meeting".

**Three tests asserted the old behaviour** (`4.33e`, `9.40`, and the probe they share) by pinning
`page.style.minHeight === ''`. That was a proxy for the property that actually matters and is
asserted right beside them - the JPG must not be padded to whole A4 pages, unlike the PDF. They now
pin that, plus a direct measurement of footer-to-last-row clearance. **Pin the measurement, not the
mechanism** - this is the second time that rule has been paid for on this file.

## The flex balance is now exact (V44)

Break's range went 10-18 -> 10-20 at Rama's request. Only the RANGE moved; `durMin` stays 15, so the
blank template still totals exactly 150 min.

Widening it broke `balanceToEndTime()`: the default meeting started landing on **9:31 PM**.
`applyFlexBalance()` rounds each flexible segment's share independently, so the parts can miss the
whole by up to a minute per segment - and Break's old 18-minute ceiling had been clamping the very
share whose rounding was wrong, absorbing the error by accident for versions.

It now hands the remainder out a minute at a time to whichever flexible segment still has room in the
needed direction. Exact on every reachable target; when the ranges genuinely cannot reach it, `exact`
is false and the banner says how far short it landed, which is what it always claimed to do.

---

## Settled decisions, do not "fix" these

- **Club standard timings**: 4 min for SAA call-to-order / TME Welcome / President's Opening; 1 min
  for any "returns control to TME"; 4 min per evaluation; 3 min per combined timer's-report-and-vote
  row. **Four speeches and four evaluations.** The blank template totals **exactly 150 min**.
- **Evaluation slots are 4 min with 2:00–3:00 lights** (bell 3:30). **Asked and answered three
  times. Do not raise it again.**
- **Slido codes are chronological**: speeches, then table topics, then evaluations.
- **Voting rows show two names on exactly two lines**, no role labels.
- **Language Evaluator defaults OFF.**
- **Break Time is 10-20 min, nominal 15** (V44). The nominal is what keeps the blank
  template on exactly 150; the range is what Balance has to play with.
- **Five themes**: classic, zine, swiss, brutalist, neomemphis. Retired keys fall back to classic.
- **Contest mode replaces the running order, it does not merge.** There is no useful merge between
  "TME Welcome Remarks" and "Briefing for Judges".
- **No print button**, and **JPG is the only image format**.
- **The Education Series is not path-specific.** `projectsFor()` concatenates `eduFor(lvl)`.
- **JSON is the only save format.** Markdown was built, measured and removed.
- **The printed pane's setting is tuned, not arbitrary.** Tune the leading, never blame the inset.
- **The pane overrun is answered with a warning, not more compaction** (V36). The remaining cases
  need 281 mm of material in a 234 mm column; no typeface fixes that. The PDF and JPG exports
  already flow the pane correctly, so the honest advice is "use Download", not "write less".

---

## The save system, and why it looks the way it does

V35's five rounds found **29 defects**. V36 added write provenance and recovery on top, and two
adversarial rounds against the new code found **25 more** — thirteen in the first pass, twelve in
the fixes for the first pass. **The fix-to-break ratio on this subsystem is close to one in one.
Do not ship a change to it without an adversarial pass over the diff.**

Standing behaviour, every line of it paid for:

- **Reset detaches the file first**, or the next keystroke autosaves the blank template over a
  saved meeting, silently, with a green tick.
- **Warnings are sticky.** `flashSaved()` used to paint a green tick on the next keystroke.
- **All writes go through one chain with a per-file sequence.** The 1.2 s debounce serialised
  timers, not writes; on a synced folder two writes overlapped and the *older* one committed last.
- **The baseline is per file and self-healing.** `resyncBaseline()` re-reads the disk after a
  failure, which repairs our own half-landed write and keeps the two-tab guard armed.
- **`adoptState()` merges into fresh objects** and sanitises everything. Repairs are reported.
- **The file handle is persisted**, and `savedAt` is compared against a stamp captured
  *synchronously at load*.
- An empty running order is never written; existing files prompt before being replaced; a vanished
  file is never silently recreated; the flush on `pagehide` starts synchronously.

**New in V36:**

- **`writeId`, a per-file monotonic counter, and `writer`, a tab id.** Allocated *inside* the write
  chain (stamped at the call site, two queued writes carry the same number) and **burned on
  failure** — `writeIdNext` allocates, `writeIdByFile` only advances after the read-back agrees.
  A failed write that reused its id let two different payloads share a number, and the rollback
  between them was invisible.
- **`classifyDisk()` returns one of six verdicts**, because "that file changed outside this tab" was
  one message for six different events and its advice ("reopen it from the dropdown") is *actively
  wrong* for half of them — reopening loads the damage:
  `same` · `damaged` · `stale` (a lower writeId: a real rollback) · `maybe-stale` (an older
  timestamp in a file with no counter) · `ours-late` · `other` / `changed`.
- **`ours-late` is the headline OneDrive case.** OneDrive pauses mid-commit, `writeHandle` throws,
  `resyncBaseline` captures the torn text, the sync then completes with our own bytes. V35 called
  that a foreign change and refused every autosave for the rest of the session. V36 recognises it
  and carries on. `TAB_ID` and `writeIdNext` live in **sessionStorage**, so reloading the tab —
  the obvious thing to do when a save looks stuck — does not turn our own late write into a
  stranger's.
- **`maybe-stale` deliberately carries no Restore button.** A file with no counter cannot
  distinguish a rollback from a second machine whose clock is behind, and only one of those two
  readings makes restoring safe. `CLOCK_SKEW_MS` is five minutes, and it is generous on purpose:
  a missed warning costs a message, a false one costs somebody's evening.
- **`lastGood`, the last text this tab wrote and verified or read and parsed.** In memory only —
  a copy in localStorage would be a third writer to reconcile. Capped at 8, never evicting the
  attached file (its `at` only moves on a *successful* write, so the one file whose writes are
  failing aged fastest and went first).
- **`adoptDiskProvenance()` will not replace a held copy that is demonstrably newer.** The
  rollback message says "reopen it from the dropdown", and following that advice used to overwrite
  the good in-memory copy with the rolled-back disk text — deleting the safety net by taking the
  advice. **`writeId` decides when both sides carry one; the clock only when one does not.**
  Written as an OR first, and it inverted on skew.
- **The recovery bar** offers the good copy back, and **turns round after a restore** to offer what
  was on screen. The first version's banner said "use Undo in the fields", which does not exist:
  `applyMeetingText` replaces state wholesale and the autosave restamps localStorage 400 ms later.
- **A restore refuses when the tab has since attached to a different file.** Save As does exactly
  that without detaching, and the offer used to survive it — click Restore afterwards and the old
  meeting was adopted and autosaved into the *new* file.
- **Only a write that looked at the disk first may retire an offer.** `flushFileSave` goes straight
  to the chain (it has to; it runs on `pagehide`), and letting it clear the bar meant a genuine
  rollback alarm vanished, unread, the moment the user switched tabs.
- **An advisory localStorage lock**, keyed by **folder and file**. It warns, it never blocks: a
  lock that can refuse to save is a lock that can lock you out twenty minutes before the meeting.
  The alarm fires **once per (file, other tab)** — the 5-second heartbeat fires a `storage` event
  in every other tab, and the first version re-raised the alarm on that timer forever, which both
  parked a permanent banner on screen and re-armed the sticky warning the moment each successful
  autosave cleared it. The claim is taken **at attach**, not after the write, or one transient
  failure left the tab autosaving while advertising nothing.

---

## The Ctrl+P pane warning (V36)

The printed pane is `position:fixed`, one page tall, `overflow:hidden`, so it repeats identically
on every page — and anything past the bottom is cut, with no page 3 and no warning. What sits at
the bottom is Announcements, the only block written the same week it is read.

`measurePaneFit()` renders `buildSheetHTML(false)` into a hidden iframe sized to the A4 page **box**
(190 × 277 mm at 96 dpi) and retargets every `@media print` block in the sheet's own stylesheet to
`all` through the CSSOM, so `position:fixed` resolves against the box the printer gives it.
**Checked against real print emulation across five loads × five themes: worst disagreement
0.01 mm** (`tests/pane/warnprobe.py`).

Three separate facts, and conflating any two has cost a defect each: `paneFit.sig` (the signature
the number describes — the notice renders only when it matches), `paneFit.trusted` (whether the
fonts had settled), `paneFit.mm` (never blanked; staleness is decided by `sig`). Blanking `mm` on
every change let the "already measured this signature" shortcut fire while `mm` was null, so
typing an announcement and deleting it inside the 700 ms debounce killed the check for good.
A run without fonts is shown but re-measured, on a budget of three — on a `file://` page with no
network `document.fonts.ready` never settles, and treating those as failures-to-cache produced a
full offscreen sheet render on every keystroke, forever.

The signature covers **only** the Exco, District officers, Links, Announcements and theme, which is
everything the pane's height depends on and nothing else. That is what keeps an iframe off the
keystroke path.

---

## Publishing

`python3 publish.py out/index.html` builds the copy that may go to GitHub, replacing the officers'
real names with `<President Name>`-style placeholders (matching the transform already visible in
the published V31) and **refusing to write a file that still contains one**. Club identity — name,
number, district line, cadence, venue, the two club links, the voting codes — is deliberately left
alone; that is what the published V31 does and what `customise-for-your-club.md` is written around.

The gate is word-boundaried and case-sensitive. The first version was a loose case-insensitive
alternation and `Lim` matched `limit`, `delimiter` and `sLIM`: 44 hits in a clean file. **A gate
that cries wolf gets switched off, which is worse than no gate.**

V30 onward were never published precisely because "swap the names out before uploading" was a note
in a handover rather than something the build could do. A note does not survive a session.

---

## Open items for the next session

0. **The vertical seam in Rama's exports — V37 is a candidate fix, NOT a confirmed one.**
   Measured from the PDF he sent on 11 Aug: 2px wide, at 49.3% of the content width, on both
   pages, a translucent band of constant colour that reads darker on the cream paper and lighter
   on the maroon banner.
   - **It crosses the banner.** Every element spanning the full height of the export was
     enumerated (`html`, `body`, `.page-wrap`, `.page`, `.body-grid`, `main`, `table`, `tbody`,
     `aside.ref-pane`, `.pane-body`); their edges are at 0%, 24% and 27.16%, and nothing in the
     sheet spans the banner AND the agenda. No CSS border can draw it.
   - **It does not reproduce here.** `tests/seamrepro.py` rebuilds his 13 Aug sheet field for
     field and matches his table geometry to 0.1% (39.8% boundary), with real Google webfonts,
     at device scale factors 1 / 1.25 / 1.5 / 2. No seam in any run.
   - That leaves a GPU tile seam: the sheet is one canvas of ~2154 x 6300 px and a high-quality
     downscale of a texture that size is done per tile. This container rasterises in software,
     which has no tiles, which is why it cannot be reproduced here at all.
   - **Chrome's own print engine renders the same DOM CLEAN on his machine.** He downloaded the
     sheet (⭳ Download → HTML) from a session showing the line and Ctrl+P'd it: no line. That HTML
     is **byte-identical to the one this build produces from his `.nse.json`** — same MD5,
     `41a8332cc097a5d0f7b9b4ad225d34bf`, 87,572 bytes. So the document, the saved file, the theme
     and the app's markup are all cleared. The artefact is introduced by **html2canvas**, which is
     what the JPG and PDF exports use and what Ctrl+P does not.
   - **Two false trails, recorded so nobody walks them again.** (1) Zine's `transform:rotate(-0.6deg)`
     on the meeting title is the only geometric transform in the printed sheet, and it is innocent:
     a blank sheet in Zine is clean and an imported sheet shows the line in *every* theme.
     (2) Every `span.rr-label` has its right edge at 354.7px = 49.4%, matching the line to 0.13%,
     because `grid-template-columns: max-content 1fr` puts that boundary at the same x in all 21 of
     them. Also a coincidence: the line runs through **100% of the banner rows and 100% of the
     notice-bar rows**, where no such label exists.
   - **V37's change, in two parts.** First attempt: the downscale and page-slicing contexts took
     `{willReadFrequently:true}`. That did NOT fix it, and the reason is worth keeping — html2canvas
     creates its OWN canvas (`A.canvas = e.canvas || document.createElement("canvas")` in the
     bundle) and that is the surface every draw call lands on. Second attempt: the app now builds
     that canvas itself, claims its context with `willReadFrequently` first, and passes it via the
     library's `canvas` option. `getContext` attributes are fixed by the first call, so the
     library's later plain `getContext('2d')` returns the CPU-backed context. Sizing is ours,
     because the bundle only sets width/height on a canvas it created.
   - **The discriminating test, two minutes, and it must be run before this is called fixed:**
     Chrome → Settings → System → turn OFF "Use graphics acceleration when available", restart,
     export a PDF from **V36**. Gone => diagnosis confirmed and V37 is the fix. Still there =>
     the diagnosis is wrong; get his `.nse.json` and Chrome version and start again.
   - `tests/seamprobe.py`, `seamvariants.py`, `seamrepro.py` and `printseam.py` drive the real
     export and report every full-height vertical rule as a percentage of the sheet width.
     Suite 12 pins the three legitimate ones (pane rule 24%, table edge 27.2%, TIME column 40%)
     so a LAYOUT-side regression is caught — it cannot catch the GPU seam, and says so.

1. **The meetings folder is still in OneDrive.** Rama has deferred moving it (11 Aug: "we'll think
   about it in a while"). Everything in the V36 save work above exists *because* it is still
   there. OneDrive is a second writer the app cannot see. The recommendation stands: point the
   folder at something local and let OneDrive back up a copy out of band.
2. **The advisory lock cannot see another machine**, only another tab in the same browser, and its
   folder key is the directory **basename** — two folders both called `meetings` (the OneDrive one
   and a local copy, i.e. exactly the migration in item 1) still collide. `FileSystemDirectoryHandle`
   exposes no path. The failure mode is a false "another tab has this open", not data loss.
3. **`ours-late` cannot survive a browser restart**, only a reload — `sessionStorage` dies with the
   tab. Persisting `{tab, writeIdNext}` per file in the existing IndexedDB store would close it.
4. **`Ctrl+P` still clips a long reference pane**; V36 warns instead of fixing it, which was the
   settled decision. The exports flow it correctly.
5. **A row or announcement taller than a whole page** defeats the export's pagination and is cut.
   Real print handles it. Degenerate, never chased.
6. **Not published.** `publish.py` produces the file; nothing has been uploaded. Git push and repo
   creation are both blocked from Cowork — see `reference_github_from_cowork.md` in project memory:
   drive Rama's signed-in browser and upload with sandbox paths.

---

## How Rama wants to be worked with

Challenge the assumption first, no warm openers, tag confidence, one concrete next action at the
end, name avoidance when you see it. He values being told when he is wrong.

**Use subagents to attack the work, not just to test it.** In V36 an adversarial agent reading the
diff found 13 defects the tests passed, and 12 more in the fixes for those. Two of the three most
dangerous — a restore that wrote the wrong file, and a `ours-late` branch that adopted the baseline
and then threw anyway — were invisible to every automated check that existed. Verify at the source;
do not trust a passing test over the artefact.
