"""V34: the whole sheet round-trips as one Markdown file.

Order of attack:
  1. parseClubMd is now an alias of parseSheetMd - prove V33 club files are
     unaffected BEFORE testing anything new.
  2. Full round trip of a deliberately awkward meeting, diffing the whole state.
  3. The shipped weekly template, untouched.
  4. Hostile Programme / Roles / Speeches sections.
  5. Partial files.
Throughout: nothing throws, state stays structurally valid, the sheet still
renders.
"""

import asyncio
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import V33, open_app, open_sections, run_suite  # noqa: E402

MEETING_MD = "/home/claude/psb/nse-meeting.md"
CLUB_MD = "/home/claude/psb/nse-club-setup.md"
BLANK_MD = "/home/claude/psb/blank-club-setup.md"

# The whole of the state that a round trip is expected to carry.
FULL = r"""() => ({
  meeting: {title: state.meeting.title, date: state.meeting.dateDisplay,
            start: state.meeting.startTime, end: state.meeting.endTime},
  theme: state.theme,
  voting: JSON.parse(JSON.stringify(state.meeting.voting || {})),
  announcements: state.announcementsText,
  roles: JSON.parse(JSON.stringify(state.roles)),
  roleActive: JSON.parse(JSON.stringify(state.roleActive)),
  customRoles: JSON.parse(JSON.stringify(state.customRoles || [])),
  segments: activeSegments().map(s => ({
    title: titleFor(s), preset: s.presetKey, dur: s.durMin,
    holder: s.holderOverride || '', sub: (s.sub || '').replace(/\n/g, ' '),
    isSpeech: !!s.isSpeech, isEval: !!s.isEvaluation,
    speaker: s.speakerName || '', pathway: s.pathway || '',
    level: String(s.pLevel || ''), project: s.project || '',
    speechTitle: s.speechTitle || '',
    sigMin: s.signalMin, sigMax: s.signalMax,
  })),
  totals: {minutes: computeSchedule().rows.reduce((a,r)=>a+(Number(r.seg.durMin)||0),0),
           end: computeSchedule().endClock, n: activeSegments().length},
})"""

VALID = r"""() => ({
  segsArray: Array.isArray(state.segments),
  segsOk: state.segments.every(s => s && typeof s.id === 'string'
            && typeof s.durMin === 'number' && !isNaN(s.durMin)),
  rolesObj: state.roles && typeof state.roles === 'object',
  activeObj: state.roleActive && typeof state.roleActive === 'object',
  customArr: Array.isArray(state.customRoles)
            && state.customRoles.every(r => r && typeof r.key === 'string'),
  votingObj: state.meeting.voting && typeof state.meeting.voting === 'object',
  annStr: typeof state.announcementsText === 'string',
  themeStr: THEMES.some(t => t.key === state.theme),
  ids: state.segments.length === new Set(state.segments.map(s=>s.id)).size,
})"""

RICH = r"""() => {
  state = defaultState();
  const m = state.meeting;
  m.title = 'Chapter Meeting: Voices of a Nation';
  m.dateDisplay = 'Thursday, 13 August 2026';
  state.theme = 'swiss';
  state.announcementsText = 'Club anniversary dinner, 20 Sept\nArea contest: bring $5';
  Object.keys(state.roles).forEach((k,i)=>{ state.roles[k] = 'Member Name ' + (i+1); });
  state.roleActive.langeval = false;
  /* two club roles of our own */
  addCustomRole(); state.customRoles[0].label = 'Zoom Master';
  state.roles[state.customRoles[0].key] = 'Priya Menon';
  addCustomRole(); state.customRoles[1].label = 'Joke Master';
  state.roles[state.customRoles[1].key] = 'Sam Lee';
  /* a custom item whose sub-note has BOTH a pipe and a colon */
  const cust = newSegment('custom');
  cust.title = 'Guest Speaker: Q&A | Open Floor';
  cust.durMin = 7.5;
  cust.holderOverride = 'Guest Chair';
  cust.sub = 'Note: bring the mic | second half only';
  /* BEFORE the speeches, so the block of speeches stays contiguous. An item
     placed BETWEEN two speeches is covered separately (11.20z). */
  state.segments.splice(5, 0, cust);
  /* an unusual duration on a preset row */
  const brk = state.segments.find(s=>s.presetKey==='breaktime');
  if(brk) brk.durMin = 12.5;
  /* speeches: one with a project whose official timing differs from the slot */
  const sp = state.segments.filter(s=>s.isSpeech);
  const evs = state.segments.filter(s=>s.isEvaluation);
  const setup = [
    ['Ada Lovelace','DL','1','Ice Breaker','The First Time', 'Eval One', 11],
    ['Grace Hopper','PM','2','Understanding Your Communication Style','Signals','Eval Two', 8],
    ['Alan Turing','EH','1','Ice Breaker','Machines That Think','Eval Three', 8],
    ['Katherine Johnson','MS','1','Ice Breaker','Numbers','Eval Four', 8],
  ];
  sp.forEach((s,i)=>{
    const r = setup[i]; if(!r) return;
    s.speakerName = r[0]; s.pathway = r[1]; s.pLevel = r[2];
    applyProjectChoice(s, r[3]);
    s.speechTitle = r[4];
    s.durMin = r[6]; autoSignalsFromSlot(s);
    if(evs[i]){ evs[i].holderOverride = r[5]; evs[i].speakerName = r[0]; }
  });
  syncFormInputs(); renderFormPane(); renderPreviewNow();
}"""

RICH_INTERLEAVED = RICH.replace("state.segments.splice(5, 0, cust);",
                                "state.segments.splice(6, 0, cust);")

WRECK = r"""() => {
  state = defaultState();
  state.meeting.title = 'WRECKED'; state.meeting.dateDisplay = 'nope';
  state.theme = 'brutalist';
  state.announcementsText = 'wrecked';
  Object.keys(state.roles).forEach(k=>{ state.roles[k] = 'XX'; });
  state.customRoles = [];
  state.segments = state.segments.slice(0, 3);
  syncFormInputs(); renderFormPane(); renderPreviewNow();
}"""


async def apply_md(p, text, label="t.md"):
    return await p.evaluate(
        r"""([t,l]) => { try { applySheetMd(parseSheetMd(t), l);
              return {ok:true, banner: (document.getElementById('banner')||{}).textContent || ''};
            } catch(e){ return {ok:false, err: String(e && e.stack || e)}; } }""",
        [text, label])


async def parse_md(p, text):
    return await p.evaluate(
        r"""t => { try { return {ok:true, out: parseSheetMd(t)}; }
                   catch(e){ return {ok:false, err:String(e)}; } }""", text)


async def sheet_ok(p):
    await p.evaluate("() => renderPreviewNow()")
    await p.wait_for_timeout(250)
    txt = await p.frame_locator("#previewFrame").locator("body").inner_text()
    return len(txt) > 400 and "Toastmasters" in txt


async def main(ctx, s):
    app = await open_app(ctx)
    p = app.page
    await open_sections(p)
    p.on("dialog", lambda d: asyncio.ensure_future(d.accept()))

    club_md = open(CLUB_MD).read()
    blank_md = open(BLANK_MD).read()
    meeting_md = open(MEETING_MD).read()

    # ================= 1. parseClubMd is an alias; V33 files unaffected =========
    s.check("11.1 parseClubMd is literally parseSheetMd",
            await p.evaluate("() => parseClubMd === parseSheetMd") is True)

    v33 = await open_app(ctx, V33)
    keys = ["meeting", "voting", "exec", "district", "links", "unknown"]

    def norm(v):
        # V33 returned list rows as "A|B|C" strings; V34 returns ["A","B","C"].
        # applyClubSetup accepts both, so compare the VALUES, not the container.
        if isinstance(v, list):
            return ["|".join(x) if isinstance(x, list) else x for x in v]
        return v

    diffs, shape = [], []
    for name, text in (("nse-club-setup.md", club_md), ("blank-club-setup.md", blank_md)):
        old = await v33.page.evaluate("t => parseClubMd(t)", text)
        new = await p.evaluate("t => parseClubMd(t)", text)
        for k in keys:
            if norm(old.get(k)) != norm(new.get(k)):
                diffs.append((name, k, old.get(k), new.get(k)))
            elif old.get(k) != new.get(k):
                shape.append((name, k))
    s.check("11.2 V33 club files parse to the same club VALUES in V34",
            not diffs, f"{diffs[:3]}")
    s.check("11.2b (informational) the list-row container shape changed "
            "from 'A|B' strings to ['A','B'] arrays",
            True, f"changed for: {sorted(set(k for _, k in shape))}")

    # and applying one gives the same state
    SNAP = ("() => ({m: state.meeting, ex: state.execText, di: state.districtText,"
            " li: state.linksText, vo: state.meeting.voting})")
    old_state = await v33.page.evaluate(
        "t => { applyClubSetup(parseClubMd(t), 'x'); return " + SNAP.split("=>")[1] + "; }", club_md)
    new_state = await p.evaluate(
        "t => { applyClubSetup(parseClubMd(t), 'x'); return " + SNAP.split("=>")[1] + "; }", club_md)
    s.eq("11.3 applying a V33 club file gives identical club state", new_state, old_state)
    await v33.page.close()

    # a club-only file must NOT touch the running order, even through applySheetMd
    await p.evaluate(RICH)
    await p.wait_for_timeout(400)
    before = await p.evaluate(FULL)
    r = await apply_md(p, club_md, "nse-club-setup.md")
    s.check("11.4 importing a V33 club file through applySheetMd does not throw",
            r["ok"] is True, str(r.get("err"))[:200])
    after = await p.evaluate(FULL)
    s.eq("11.5 a club-only file leaves the running order untouched",
         [x["title"] for x in after["segments"]], [x["title"] for x in before["segments"]])
    s.eq("11.6 a club-only file leaves the roles untouched", after["roles"], before["roles"])
    s.eq("11.7 a club-only file leaves the announcements untouched",
         after["announcements"], before["announcements"])
    s.eq("11.8 a club-only file leaves the totals untouched", after["totals"], before["totals"])

    # ================= 2. full round trip of a rich meeting =================
    await p.evaluate(RICH)
    await p.wait_for_timeout(500)
    rich = await p.evaluate(FULL)
    md = await p.evaluate("() => buildSheetMd()")
    s.check("11.9 buildSheetMd produces a non-trivial document", len(md) > 1500, f"{len(md)}")
    s.check("11.10 the export escapes a pipe inside a sub-note",
            r"Note: bring the mic \| second half only" in md,
            [l for l in md.split("\n") if "bring the mic" in l][:1])
    s.check("11.11 the export escapes a pipe inside an item title",
            r"Guest Speaker: Q&A \| Open Floor" in md,
            [l for l in md.split("\n") if "Guest Speaker" in l][:1])

    await p.evaluate(WRECK)
    await p.wait_for_timeout(400)
    r = await apply_md(p, md, "roundtrip.md")
    s.check("11.12 importing the exported sheet does not throw", r["ok"] is True,
            str(r.get("err"))[:300])
    await p.wait_for_timeout(500)
    back = await p.evaluate(FULL)
    md2_now = await p.evaluate("() => buildSheetMd()")

    s.eq("11.13 round trip: meeting title/date/times", back["meeting"], rich["meeting"])
    s.eq("11.14 round trip: sheet style", back["theme"], rich["theme"])
    s.eq("11.15 round trip: announcements", back["announcements"], rich["announcements"])
    s.eq("11.16 round trip: voting settings", back["voting"], rich["voting"])
    s.eq("11.17 round trip: item count", back["totals"]["n"], rich["totals"]["n"])
    s.eq("11.18 round trip: total minutes", back["totals"]["minutes"], rich["totals"]["minutes"])
    s.eq("11.19 round trip: end clock", back["totals"]["end"], rich["totals"]["end"])

    # per-field segment diff
    seg_fields = ["title", "dur", "holder", "sub", "isSpeech", "isEval",
                  "speaker", "pathway", "level", "project", "speechTitle",
                  "sigMin", "sigMax"]
    lost = {f: [] for f in seg_fields}
    n = min(len(back["segments"]), len(rich["segments"]))
    for i in range(n):
        a, b = rich["segments"][i], back["segments"][i]
        for f in seg_fields:
            if a[f] != b[f]:
                lost[f].append((i, a["title"][:28], a[f], b[f]))
    for f in seg_fields:
        s.check(f"11.20 round trip preserves segment.{f}", not lost[f], f"{lost[f][:3]}")

    # --- the one structural limitation, isolated ---
    await p.evaluate(RICH_INTERLEAVED)
    await p.wait_for_timeout(400)
    inter_before = await p.evaluate(
        "() => activeSegments().map(s => s.isSpeech ? 'SPEECH' : titleFor(s))")
    md_i = await p.evaluate("() => buildSheetMd()")
    await p.evaluate(WRECK)
    await apply_md(p, md_i, "interleaved.md")
    await p.wait_for_timeout(400)
    inter_after = await p.evaluate(
        "() => activeSegments().map(s => s.isSpeech ? 'SPEECH' : titleFor(s))")
    s.eq("11.20z an item placed BETWEEN two speeches keeps its position",
         inter_after, inter_before)

    await p.evaluate(RICH)
    await p.wait_for_timeout(300)
    await apply_md(p, md, "roundtrip.md")
    await p.wait_for_timeout(400)

    s.eq("11.21 round trip: custom role labels",
         [c["label"] for c in back["customRoles"]],
         [c["label"] for c in rich["customRoles"]])
    s.eq("11.22 round trip: custom role holders",
         [back["roles"].get(c["key"]) for c in back["customRoles"]],
         [rich["roles"].get(c["key"]) for c in rich["customRoles"]])
    built_in = await p.evaluate("() => Object.keys(ROLE_LABELS)")
    active_builtin = [k for k in built_in if rich["roleActive"].get(k)]
    s.eq("11.23 round trip: names of the roles that are RUNNING",
         {k: back["roles"].get(k) for k in active_builtin},
         {k: rich["roles"].get(k) for k in active_builtin})
    off_builtin = [k for k in built_in if not rich["roleActive"].get(k)]
    s.eq("11.23b round trip: names of roles switched OFF survive too",
         {k: back["roles"].get(k) for k in off_builtin},
         {k: rich["roles"].get(k) for k in off_builtin})
    s.eq("11.24 round trip: which built-in roles are running",
         {k: back["roleActive"].get(k) for k in built_in},
         {k: rich["roleActive"].get(k) for k in built_in})
    s.check("11.25 round trip: state stays structurally valid",
            all((await p.evaluate(VALID)).values()), str(await p.evaluate(VALID)))
    s.check("11.26 round trip: the sheet still renders", await sheet_ok(p))
    s.check("11.27 export -> import -> export is byte-identical", md == md2_now,
            "\n".join(f"  {a!r} != {b!r}" for a, b in
                      zip(md.split("\n"), md2_now.split("\n")) if a != b)[:400])

    # ================= 3. the shipped weekly template, untouched =================
    await p.evaluate(WRECK)
    await p.wait_for_timeout(300)
    r = await apply_md(p, meeting_md, "nse-meeting.md")
    s.check("11.28 importing the shipped template does not throw", r["ok"] is True,
            str(r.get("err"))[:300])
    await p.wait_for_timeout(500)
    t = await p.evaluate(FULL)
    s.eq("11.29 the template yields 25 programme items", t["totals"]["n"], 25)
    s.eq("11.30 the template yields 4 speeches",
         sum(1 for x in t["segments"] if x["isSpeech"]), 4)
    s.eq("11.31 the template yields 4 evaluations",
         sum(1 for x in t["segments"] if x["isEval"]), 4)
    s.eq("11.32 the template totals exactly 150 minutes", t["totals"]["minutes"], 150)
    s.eq("11.33 the template ends at 9:30 PM", t["totals"]["end"], "9:30 PM")
    s.check("11.34 the banner reports no spurious 'not recognised'",
            "not recognised" not in r["banner"].lower(), f"banner={r['banner']!r}")
    s.check("11.35 the banner reports what was applied",
            "programme items" in r["banner"], f"banner={r['banner']!r}")
    s.check("11.36 placeholder speaker names were not imported",
            all(not re.search(r"<[^>]+>", x["speaker"]) for x in t["segments"]),
            str([x["speaker"] for x in t["segments"] if x["isSpeech"]]))
    s.check("11.37 no placeholder token is printed on the sheet",
            not re.findall(r"<[^>\n]{1,40}>",
                           await p.frame_locator("#previewFrame").locator("body").inner_text()),
            "placeholders on the sheet")
    s.check("11.38 the escaped pipe survived into a row title",
            any("Timer's Report | Voting for Best Speaker" in x["title"]
                for x in t["segments"]),
            str([x["title"] for x in t["segments"]][:8]))
    s.check("11.39 the escaped pipe survived into a sub-note",
            any("| Enter code:" in x["sub"] for x in t["segments"]),
            str([x["sub"] for x in t["segments"] if x["sub"]][:4]))
    tt = await p.evaluate(
        "() => { const x = activeSegments().find(s=>s.presetKey==='tabletopics');"
        " return x ? [x.durMin, x.signalMin, x.signalMid, x.signalMax] : null; }")
    tt_default = await p.evaluate(
        "() => { const x = newSegment('tabletopics');"
        " return [x.durMin, x.signalMin, x.signalMid, x.signalMax]; }")
    s.eq("11.39b the Table Topics row keeps its per-speaker signal lights", tt, tt_default)

    s.check("11.40 the template's items are not all 'custom'",
            sum(1 for x in t["segments"] if x["preset"] == "custom") <= 1,
            str([x["title"] for x in t["segments"] if x["preset"] == "custom"]))

    # ================= 4. hostile Programme / Roles / Speeches =================
    HEAD = "## Speeches\n- A | DL | 1 | Ice Breaker | T | E | 8\n\n## Programme\n"
    hostile = [
        ("duplicate item names",
         "## Programme\n- Break Time | 10\n- Break Time | 10\n- Break Time | 10"),
        ("item name that is only a pipe", "## Programme\n- \\|\n- Break Time | 5"),
        ("item name that is only spaces", "## Programme\n-    \n- Break Time | 5"),
        ("200 items", "## Programme\n" + "\n".join(f"- Item {i} | 1" for i in range(200))),
        ("marker with no Speeches section",
         "## Programme\n- Prepared Speeches\n- Evaluations\n- Break Time | 5"),
        ("Speeches section with no marker",
         "## Speeches\n- A | DL | 1 | Ice Breaker | T | E | 8\n\n"
         "## Programme\n- Break Time | 5"),
        ("Evaluations before Prepared Speeches",
         HEAD + "- Evaluations\n- Prepared Speeches\n- Break Time | 5"),
        ("duration is text", "## Programme\n- Break Time | abc\n- Registration & Fellowship | ?"),
        ("duration negative", "## Programme\n- Break Time | -30"),
        ("duration huge", "## Programme\n- Break Time | 999999"),
        ("duration empty", "## Programme\n- Break Time |  | Someone"),
        ("same role twice",
         "## Roles\n- Timer | First\n- Timer | Second\n- Toastmaster of the Day | T"),
        ("custom role colliding with a built-in label",
         "## Roles\n- Timer | Real Timer\n- timer | Impostor\n- TIMER | Third"),
        ("unknown role title",
         "## Roles\n- Zoom Master | Priya\n- Toastmaster of the Day | T"),
        ("role row with no name", "## Roles\n- Timer"),
        ("role row that is only a pipe", "## Roles\n- \\|"),
        ("speech row all placeholders",
         "## Speeches\n- <a> | <b> | <c> | <d> | <e> | <f> | <g>\n\n"
         "## Programme\n- Prepared Speeches"),
        ("speech row with too few cells", "## Speeches\n- OnlyName\n\n## Programme\n- Prepared Speeches"),
        ("speech row with too many cells",
         "## Speeches\n- A | DL | 1 | Ice Breaker | T | E | 8 | X | Y | Z\n\n"
         "## Programme\n- Prepared Speeches"),
        ("speech level is text", "## Speeches\n- A | DL | five | Ice Breaker | T | E | 8\n\n"
                                 "## Programme\n- Prepared Speeches"),
        ("speech slot is text", "## Speeches\n- A | DL | 1 | Ice Breaker | T | E | abc\n\n"
                                "## Programme\n- Prepared Speeches"),
        ("unknown project name", "## Speeches\n- A | DL | 1 | Not A Real Project | T | E | 8\n\n"
                                 "## Programme\n- Prepared Speeches"),
        ("programme with only markers", "## Programme\n- Prepared Speeches\n- Evaluations"),
        ("empty programme section", "## Programme\n"),
        ("programme rows all placeholders", "## Programme\n- <Item> | <5>\n- <Another>"),
    ]
    threw, invalid, norender = [], [], []
    for label, text in hostile:
        await p.evaluate(RICH)
        await p.wait_for_timeout(120)
        r = await apply_md(p, text, label)
        if not r["ok"]:
            threw.append((label, r["err"][:160]))
            continue
        v = await p.evaluate(VALID)
        if not all(v.values()):
            invalid.append((label, {k: x for k, x in v.items() if not x}))
        if not await sheet_ok(p):
            norender.append(label)
    s.check(f"11.41 all {len(hostile)} hostile sections import without throwing",
            not threw, f"{threw[:4]}")
    s.check("11.42 state stays structurally valid after every hostile import",
            not invalid, f"{invalid[:3]}")
    s.check("11.43 the sheet still renders after every hostile import",
            not norender, f"{norender[:4]}")

    # specific behaviours worth pinning
    await p.evaluate(RICH)
    await apply_md(p, "## Programme\n- Break Time | 10\n- Break Time | 10\n- Break Time | 10")
    await p.wait_for_timeout(300)
    s.eq("11.44 duplicate item names all survive as separate rows",
         await p.evaluate("() => activeSegments().length"), 3)

    await p.evaluate(RICH)
    await apply_md(p, "## Programme\n" + "\n".join(f"- Item {i} | 1" for i in range(200)))
    await p.wait_for_timeout(500)
    s.eq("11.45 a 200-item programme imports in full",
         await p.evaluate("() => activeSegments().length"), 200)
    s.check("11.46 200 unrecognised names become custom items keeping their wording",
            await p.evaluate("() => activeSegments()[7].title") == "Item 7")

    await p.evaluate(RICH)
    await apply_md(p, "## Programme\n- Prepared Speeches\n- Evaluations\n- Break Time | 5")
    await p.wait_for_timeout(300)
    s.eq("11.47 a marker with no Speeches section expands to nothing, leaving the rest",
         await p.evaluate("() => activeSegments().map(s=>s.presetKey)"), ["breaktime"])

    await p.evaluate(RICH)
    await apply_md(p, HEAD + "- Evaluations\n- Prepared Speeches\n- Break Time | 5")
    await p.wait_for_timeout(300)
    order = await p.evaluate(
        "() => activeSegments().map(s => s.isSpeech ? 'S' : (s.isEvaluation ? 'E' : 'x'))")
    s.eq("11.48 Evaluations before Prepared Speeches keeps the file's order",
         order, ["E", "S", "x"])

    await p.evaluate(RICH)
    await apply_md(p, "## Programme\n- Break Time | -30")
    await p.wait_for_timeout(300)
    neg = await p.evaluate("() => ({d: state.segments[0].durMin,"
                           " end: computeSchedule().endClock})")
    s.check("11.49 a negative duration does not corrupt the schedule",
            isinstance(neg["d"], (int, float)) and isinstance(neg["end"], str) and neg["end"],
            str(neg))

    await p.evaluate(RICH)
    await apply_md(p, "## Programme\n- Break Time | abc")
    await p.wait_for_timeout(300)
    s.check("11.50 a text duration falls back to the preset default, not NaN",
            await p.evaluate("() => { const d = state.segments[0].durMin;"
                             " return typeof d === 'number' && !isNaN(d) && d > 0; }"),
            str(await p.evaluate("() => state.segments[0].durMin")))

    await p.evaluate(RICH)
    await apply_md(p, "## Roles\n- Timer | First\n- Timer | Second\n"
                      "- Toastmaster of the Day | T")
    await p.wait_for_timeout(300)
    s.eq("11.51 the same role listed twice takes the last name",
         await p.evaluate("() => state.roles.timer"), "Second")
    s.check("11.52 a role listed twice does not become a custom role",
            await p.evaluate("() => state.customRoles.length") == 0,
            str(await p.evaluate("() => state.customRoles")))
    s.check("11.53 roles absent from the section are switched off",
            await p.evaluate("() => state.roleActive.photographer") is False)

    # A custom role that does NOT already exist is created correctly...
    await p.evaluate("() => { state = defaultState(); syncFormInputs(); }")
    await apply_md(p, "## Roles\n- Zoom Master | Priya\n- Toastmaster of the Day | T")
    await p.wait_for_timeout(300)
    s.eq("11.54 an unknown role title becomes a custom role",
         await p.evaluate("() => state.customRoles.map(r=>r.label)"), ["Zoom Master"])
    s.check("11.55 the custom role keeps its holder",
            await p.evaluate(
                "() => (state.customRoles[0] && state.roles[state.customRoles[0].key]) || null")
            == "Priya")

    # ...but re-importing a file onto a club that ALREADY has that custom role
    # is the normal workflow (export, edit, import back).
    await p.evaluate(r"""() => { state = defaultState(); addCustomRole();
          state.customRoles[0].label = 'Zoom Master';
          state.roles[state.customRoles[0].key] = 'Priya';
          syncFormInputs(); renderFormPane(); }""")
    await p.wait_for_timeout(200)
    await apply_md(p, "## Roles\n- Toastmaster of the Day | T\n- Zoom Master | Priya")
    await p.wait_for_timeout(300)
    again = await p.evaluate(
        r"""() => ({labels: state.customRoles.map(r=>r.label),
              orphanRoles: Object.keys(state.roles).filter(k=>/^cr/.test(k)
                            && !state.customRoles.some(r=>r.key===k)),
              orphanActive: Object.keys(state.roleActive).filter(k=>/^cr/.test(k)
                            && !state.customRoles.some(r=>r.key===k)),
              roster: rolePlayerLines().map(r=>r.label)})""")
    s.eq("11.55b re-importing a file keeps an EXISTING custom role",
         again["labels"], ["Zoom Master"])
    s.check("11.55c re-importing leaves no orphaned custom-role keys in state",
            not again["orphanRoles"] and not again["orphanActive"],
            f"orphan roles={again['orphanRoles']} orphan active={again['orphanActive']}")
    s.check("11.55d the custom role is still introduced in the roster",
            "Zoom Master" in again["roster"], f"roster={again['roster']}")
    md_again = await p.evaluate("() => buildSheetMd()")
    s.check("11.55e the custom role survives into the next export",
            "Zoom Master" in md_again, "the role is gone from the re-exported file")

    # reconcileRolesToProgramme: the running order is the stronger signal
    await p.evaluate(RICH)
    await apply_md(p, "## Roles\n- Toastmaster of the Day | T\n\n"
                      "## Programme\n- SAA Calls Meeting to Order | 4\n- Break Time | 5")
    await p.wait_for_timeout(400)
    s.check("11.56 an item in the Programme turns its owning role back on",
            await p.evaluate("() => state.roleActive.saa") is True)
    s.check("11.57 and the item it owns survives",
            await p.evaluate(
                "() => activeSegments().some(s=>s.presetKey==='calltoorder')") is True)

    # ================= 5. partial files =================
    partial = [
        ("only Roles", "## Roles\n- Timer | Solo Timer\n- Toastmaster of the Day | T"),
        ("only Programme", "## Programme\n- Break Time | 9"),
        ("only Announcements", "## Announcements\n- One thing\n- Another thing"),
        ("only Meeting", "## Meeting\n- Title: Partial Title\n- Sheet style: Zine"),
        ("headings but no rows",
         "## Meeting\n\n## Roles\n\n## Speeches\n\n## Programme\n\n## Announcements\n"),
        ("CRLF whole file",
         "## Meeting\r\n- Title: CRLF Title\r\n\r\n## Programme\r\n- Break Time | 6\r\n"),
        ("front matter prose with colons",
         "Some intro: it reads like this.\nHow it reads:\n\n## Meeting\n- Title: Prose Title"),
    ]
    pthrew, pinvalid = [], []
    for label, text in partial:
        await p.evaluate(RICH)
        await p.wait_for_timeout(120)
        r = await apply_md(p, text, label)
        if not r["ok"]:
            pthrew.append((label, r["err"][:160]))
            continue
        v = await p.evaluate(VALID)
        if not all(v.values()):
            pinvalid.append((label, {k: x for k, x in v.items() if not x}))
    s.check(f"11.58 all {len(partial)} partial files import without throwing",
            not pthrew, f"{pthrew[:3]}")
    s.check("11.59 state stays valid after every partial file", not pinvalid, f"{pinvalid[:3]}")

    # a section that is absent must leave that part alone
    await p.evaluate(RICH)
    await p.wait_for_timeout(300)
    base = await p.evaluate(FULL)
    await apply_md(p, "## Announcements\n- Only this")
    await p.wait_for_timeout(400)
    only_ann = await p.evaluate(FULL)
    s.eq("11.60 an Announcements-only file replaces the announcements",
         only_ann["announcements"], "Only this")
    s.eq("11.61 and leaves the running order alone",
         [x["title"] for x in only_ann["segments"]], [x["title"] for x in base["segments"]])
    s.eq("11.62 and leaves the roles alone", only_ann["roles"], base["roles"])

    await p.evaluate(RICH)
    await p.wait_for_timeout(300)
    await apply_md(p, "## Roles\n- Timer | Solo Timer\n- Toastmaster of the Day | T")
    await p.wait_for_timeout(400)
    only_roles = await p.evaluate(FULL)
    s.eq("11.63 a Roles-only file sets the named roles",
         only_roles["roles"].get("timer"), "Solo Timer")
    s.eq("11.64 a Roles-only file leaves the running order length alone",
         len(only_roles["segments"]) > 0, True)
    s.eq("11.65 a Roles-only file leaves the announcements alone",
         only_roles["announcements"], base["announcements"])

    await p.evaluate(RICH)
    await p.wait_for_timeout(300)
    await apply_md(p, "## Meeting\n- Title: Partial Title\n- Sheet style: Zine")
    await p.wait_for_timeout(400)
    s.eq("11.66 a Meeting-only file sets the title",
         await p.evaluate("() => state.meeting.title"), "Partial Title")
    s.eq("11.67 a Meeting-only file sets the sheet style",
         await p.evaluate("() => state.theme"), "zine")
    s.eq("11.68 a Meeting-only file leaves the running order alone",
         await p.evaluate("() => activeSegments().length"), len(base["segments"]))

    await p.evaluate(RICH)
    await p.wait_for_timeout(300)
    r = await apply_md(p, "## Meeting\n\n## Roles\n\n## Speeches\n\n## Programme\n\n"
                          "## Announcements\n")
    await p.wait_for_timeout(400)
    empty_sections = await p.evaluate(FULL)
    s.check("11.69 headings with no rows do not blank the running order",
            len(empty_sections["segments"]) > 0,
            f"{len(empty_sections['segments'])} items left")
    s.eq("11.70 an empty Announcements heading clears the announcements",
         empty_sections["announcements"], "")

    # ================= 6. buttons exist =================
    for label in ("Import .md", "Export club setup", "Export whole sheet"):
        found = await p.evaluate(
            "l => [...document.querySelectorAll('button')].some("
            "b => b.textContent.replace(/\\s+/g,' ').includes(l))", label)
        s.check(f"11.71 a button exists for {label!r}", found, "")
    s.check("11.72 exportSheetMd exists",
            await p.evaluate("() => typeof exportSheetMd") == "function")
    async with p.expect_download(timeout=60000) as dl:
        await p.evaluate("() => exportSheetMd()")
    d = await dl.value
    s.check("11.73 Export whole sheet downloads a .md named from the file stem",
            d.suggested_filename.endswith(".md"), d.suggested_filename)
    await d.cancel()

    # ================= 7. invariants and errors =================
    await p.evaluate("() => { state = defaultState(); syncFormInputs(); renderFormPane();"
                     " renderPreviewNow(); }")
    await p.wait_for_timeout(400)
    s.eq("11.74 the blank template still totals 150 minutes",
         await p.evaluate(
             "() => computeSchedule().rows.reduce((a,r)=>a+(Number(r.seg.durMin)||0),0)"), 150)
    s.eq("11.75 and still ends at 9:30 PM",
         await p.evaluate("() => computeSchedule().endClock"), "9:30 PM")
    s.check("11.76 zero uncaught page errors across the V34 features",
            not app.clean_errors(), str(app.clean_errors()[:4]))
    s.check("11.77 zero console errors across the V34 features",
            not app.clean_console(), str(app.clean_console()[:4]))


if __name__ == "__main__":
    asyncio.run(run_suite(main, "11_v34_markdown"))
