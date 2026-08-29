"""V33: configurable voting note, top add-item bar, derived club initials,
re-stamped save filename, and the Club Setup Markdown round trip.

The Markdown parser gets the bulk of the attention: it is the only place in the
app that eats a file a human hand-edited, so it is attacked with colons, pipes,
CRLF, junk, duplicates, and malformed rows. The bar is "nothing throws and
nothing silently corrupts state", not "everything is understood".
"""

import asyncio
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import open_app, open_sections, run_suite  # noqa: E402

NSE_MD = "/home/claude/psb/nse-club-setup.md"
BLANK_MD = "/home/claude/psb/blank-club-setup.md"

VOTE_ROWS = ["speechvote", "ttvote", "evalvote"]

# The Club Setup fields a round trip must preserve.
CLUB_FIELDS = ["clubName", "clubNumber", "clubInitials", "orgLine", "cadence",
               "location", "footerNote", "startTime", "endTime"]

SNAPSHOT = """() => ({
  meeting: Object.fromEntries(%s.map(k => [k, state.meeting[k]])),
  voting: JSON.parse(JSON.stringify(state.meeting.voting || {})),
  exec: state.execText, district: state.districtText, links: state.linksText,
})""" % (str(CLUB_FIELDS).replace("'", '"'))


def md_note(link, code):
    return f"Voting Link: {link} | Enter code: {code}"


async def parse(p, text):
    """parseClubMd in the page; returns None if it threw."""
    return await p.evaluate(
        "t => { try { return {ok:true, out: parseClubMd(t)}; }"
        " catch(e){ return {ok:false, err: String(e)}; } }", text)


async def apply_md(p, text, label="test.md"):
    return await p.evaluate(
        "([t,l]) => { try { const n = applyClubSetup(parseClubMd(t), l);"
        " return {ok:true, applied:n}; } catch(e){ return {ok:false, err:String(e)}; } }",
        [text, label])


async def main(ctx, s):
    app = await open_app(ctx)
    p = app.page
    await open_sections(p)
    await p.evaluate(
        "() => { window.showDirectoryPicker = () => Promise.reject("
        "Object.assign(new Error('no picker'), {name:'AbortError'})); }")

    # ================= 1. voting note =================
    notes = await p.evaluate(
        "() => state.segments.filter(s=>['speechvote','ttvote','evalvote'].includes(s.presetKey))"
        ".map(s=>[s.presetKey, s.sub])")
    s.eq("10.1 all three vote rows exist in the template", len(notes), 3)
    want = {"speechvote": "NSE_1", "ttvote": "NSE_2", "evalvote": "NSE_3"}
    bad = [(k, v) for k, v in notes if v != md_note("https://slido.com", want[k])]
    s.check("10.2 each vote row reads 'Voting Link: <link> | Enter code: <code>'",
            not bad, f"{bad}")
    sheet = await p.frame_locator("#previewFrame").locator("body").inner_text()
    s.check("10.3 the note is printed on the sheet",
            "Voting Link:" in sheet and "Enter code:" in sheet, "")
    s.eq("10.4 the sheet shows all three codes",
         sum(1 for c in ("NSE_1", "NSE_2", "NSE_3") if c in sheet), 3)

    # the four Club Setup inputs exist and are populated
    for eid, val in (("f-votingLink", "https://slido.com"), ("f-voteSpeech", "NSE_1"),
                     ("f-voteTT", "NSE_2"), ("f-voteEval", "NSE_3")):
        s.eq(f"10.5 #{eid} is populated from state", await p.locator(f"#{eid}").input_value(), val)

    # ---- bindVoting rewrites existing rows live ----
    await p.locator("#f-votingLink").fill("https://vote.example.org")
    await p.wait_for_timeout(300)
    await p.locator("#f-voteSpeech").fill("ABC_9")
    await p.wait_for_timeout(400)
    live = await p.evaluate(
        "() => state.segments.filter(s=>s.presetKey==='speechvote').map(s=>s.sub)[0]")
    s.eq("10.6 bindVoting rewrites an existing row live",
         live, md_note("https://vote.example.org", "ABC_9"))
    others = await p.evaluate(
        "() => state.segments.filter(s=>s.presetKey==='ttvote').map(s=>s.sub)[0]")
    s.eq("10.7 the other rows pick up the new link too",
         others, md_note("https://vote.example.org", "NSE_2"))
    sheet = await p.frame_locator("#previewFrame").locator("body").inner_text()
    s.check("10.8 the sheet shows the edited link and code",
            "vote.example.org" in sheet and "ABC_9" in sheet, "")

    # ---- applyStandardTimings rebuilds from the CLUB's codes ----
    p.on("dialog", lambda d: asyncio.ensure_future(d.accept()))
    await p.evaluate("() => { state.segments.filter(s=>s.presetKey==='ttvote')"
                     ".forEach(s=>{ s.sub = 'wiped'; }); }")
    await p.evaluate("() => applyStandardTimings()")
    await p.wait_for_timeout(600)
    after = await p.evaluate(
        "() => state.segments.filter(s=>['speechvote','ttvote','evalvote'].includes(s.presetKey))"
        ".map(s=>[s.presetKey, s.sub])")
    codes_now = {"speechvote": "ABC_9", "ttvote": "NSE_2", "evalvote": "NSE_3"}
    bad = [(k, v) for k, v in after
           if v != md_note("https://vote.example.org", codes_now[k])]
    s.check("10.9 applyStandardTimings rebuilds the note from the CLUB's codes, "
            "not a baked constant", not bad, f"{bad}")

    # ---- round trip ----
    payload = await p.evaluate("() => meetingPayload()")
    ok = await p.evaluate(
        "t => { const r = adoptState(JSON.parse(t)); syncFormInputs(); renderFormPane();"
        " renderPreviewNow(); return r; }", payload)
    s.check("10.10 a meeting with custom voting settings reloads", ok is True)
    s.eq("10.11 the voting link survives save-and-reopen",
         await p.evaluate("() => state.meeting.voting.link"), "https://vote.example.org")
    s.eq("10.12 the voting codes survive save-and-reopen",
         await p.evaluate("() => state.meeting.voting.codes.speechvote"), "ABC_9")
    s.eq("10.13 the reloaded form fields show them",
         await p.locator("#f-voteSpeech").input_value(), "ABC_9")
    s.eq("10.14 the reloaded rows still carry the note",
         await p.evaluate(
             "() => state.segments.filter(s=>s.presetKey==='speechvote')[0].sub"),
         md_note("https://vote.example.org", "ABC_9"))

    # ---- a pre-V33 payload with no voting key ----
    legacy = await p.evaluate(
        """() => { const o = JSON.parse(meetingPayload());
                   delete o.state.meeting.voting;
                   try { const r = adoptState(o); syncFormInputs(); renderFormPane();
                         renderPreviewNow();
                         return {ok:r, voting: state.meeting.voting, err:null}; }
                   catch(e){ return {ok:false, voting:null, err:String(e)}; } }""")
    s.check("10.15 a pre-V33 meeting (no voting key) loads without throwing",
            legacy["ok"] is True and legacy["err"] is None, str(legacy["err"]))
    s.check("10.16 it gets a voting object with a link",
            bool(legacy["voting"] and legacy["voting"].get("link")), str(legacy["voting"]))
    s.check("10.17 its vote rows still render a usable note",
            "Voting Link:" in await p.evaluate(
                "() => state.segments.filter(s=>s.presetKey==='speechvote')[0].sub"))

    # reset to the shipped defaults for the rest of the suite
    await p.evaluate("() => { state = defaultState(); syncFormInputs(); renderFormPane();"
                     " renderPreviewNow(); }")
    await open_sections(p)
    await p.wait_for_timeout(300)

    # ================= 2. add-item bar at the top =================
    s.eq("10.18 #addSegTypeTop exists", await p.locator("#addSegTypeTop").count(), 1)
    s.eq("10.19 #addSegType (foot) still exists", await p.locator("#addSegType").count(), 1)
    top_opts = await p.evaluate(
        "() => [...document.getElementById('addSegTypeTop').options].map(o=>o.value)")
    foot_opts = await p.evaluate(
        "() => [...document.getElementById('addSegType').options].map(o=>o.value)")
    s.eq("10.20 the two option lists match exactly", top_opts, foot_opts)
    s.check("10.21 the option list is non-trivial", len(top_opts) > 5, f"{len(top_opts)}")

    before_n = await p.evaluate("() => state.segments.length")
    first_before = await p.evaluate("() => state.segments[0].presetKey")
    total_before = await p.evaluate(
        "() => computeSchedule().rows.reduce((a,r)=>a+(Number(r.seg.durMin)||0),0)")
    await p.evaluate("() => { document.getElementById('addSegTypeTop').value = 'custom';"
                     " addSeg(true); }")
    await p.wait_for_timeout(400)
    s.eq("10.22 addSeg(true) unshifts one segment",
         await p.evaluate("() => state.segments.length"), before_n + 1)
    s.eq("10.23 the new segment is FIRST",
         await p.evaluate("() => state.segments[0].presetKey"), "custom")
    s.check("10.24 the previous first row moved down",
            await p.evaluate("() => state.segments[1].presetKey") == first_before)
    s.check("10.25 the schedule recomputed after a top insert",
            await p.evaluate(
                "() => computeSchedule().rows.reduce((a,r)=>a+(Number(r.seg.durMin)||0),0)")
            > total_before)
    s.check("10.26 the new card is rendered and expanded",
            await p.evaluate(
                "() => { const id = state.segments[0].id;"
                " return !!document.querySelector('.seg-card[data-seg-id=' + JSON.stringify(id) + ']')"
                " && expandedSegs.has(id); }"))
    s.check("10.27 the new top card is the first card in the list",
            await p.evaluate(
                "() => document.querySelector('#segList .seg-card').dataset.segId"
                " === state.segments[0].id"))

    await p.evaluate("() => { document.getElementById('addSegType').value = 'custom';"
                     " addSeg(false); }")
    await p.wait_for_timeout(400)
    s.eq("10.28 addSeg(false) appends one segment",
         await p.evaluate("() => state.segments.length"), before_n + 2)
    s.eq("10.29 the appended segment is LAST",
         await p.evaluate("() => state.segments[state.segments.length-1].presetKey"), "custom")
    s.check("10.30 the appended card is rendered and expanded",
            await p.evaluate(
                "() => { const s = state.segments[state.segments.length-1];"
                " return !!document.querySelector('.seg-card[data-seg-id=' + JSON.stringify(s.id) + ']')"
                " && expandedSegs.has(s.id); }"))
    s.check("10.31 no page error from either add bar", not app.clean_errors(),
            str(app.clean_errors()[:2]))

    await p.evaluate("() => { state = defaultState(); syncFormInputs(); renderFormPane();"
                     " renderPreviewNow(); }")
    await open_sections(p)
    await p.wait_for_timeout(300)

    # ================= 3. club initials follow the club name =================
    s.eq("10.32 initialsFromName drops Toastmasters/Club",
         await p.evaluate("() => initialsFromName('Nee Soon East Toastmasters Club')"), "NSE")
    cases = [
        ("Kebun Baru Toastmasters Club", "KB"),
        ("The Advanced Club of Orators", "O"),
        ("Bishan Speakers", "BS"),
        ("", ""),
        ("   ", ""),
        ("3 Wise Monkeys Toastmasters Club", "3WM"),
        ("A B C D E F G H I J", "ABCDEFGH"),
    ]
    bad = []
    for name, wantv in cases:
        got = await p.evaluate("n => initialsFromName(n)", name)
        if got != wantv:
            bad.append((name, got, wantv))
    s.check("10.33 initialsFromName handles the awkward names", not bad, f"{bad}")

    # NOTE: do not null lastClubName - syncFormInputs() seeds it from the loaded
    # club name, and that seeding is exactly what makes the first edit derive.
    await p.locator("#f-clubName").fill("Kebun Baru Toastmasters Club")
    await p.wait_for_timeout(400)
    s.eq("10.34 typing a club name updates the initials field",
         await p.locator("#f-clubInitials").input_value(), "KB")
    s.eq("10.35 and updates state", await p.evaluate("() => state.meeting.clubInitials"), "KB")

    # type your own -> never overwritten
    await p.locator("#f-clubInitials").fill("ZZZ")
    await p.evaluate("() => bindMeeting('clubInitials', 'ZZZ')")
    await p.locator("#f-clubName").fill("Bishan Speakers Toastmasters Club")
    await p.wait_for_timeout(400)
    s.eq("10.36 a typed initials value is NOT overwritten by a later name change",
         await p.evaluate("() => state.meeting.clubInitials"), "ZZZ")
    s.eq("10.37 and the field still shows it",
         await p.locator("#f-clubInitials").input_value(), "ZZZ")

    # clearing it lets deriving resume
    await p.evaluate("() => bindMeeting('clubInitials', '')")
    await p.locator("#f-clubName").fill("Yishun Ring Toastmasters Club")
    await p.wait_for_timeout(400)
    s.eq("10.38 clearing the field lets it resume deriving",
         await p.evaluate("() => state.meeting.clubInitials"), "YR")

    # the derived value drives the save filename
    await p.evaluate("() => { state.meeting.fileName = ''; fileHandle = null; }")
    stem = await p.evaluate("() => fileBaseName()")
    s.check("10.39 the derived initials drive the save filename",
            stem.startswith("YR-ProgSheet-"), f"{stem!r}")

    await p.evaluate("() => { state = defaultState(); syncFormInputs();"
                     " renderFormPane(); renderPreviewNow(); }")
    await open_sections(p)
    await p.wait_for_timeout(300)

    # ================= 4. the save filename re-stamps the time =================
    auto_cases = [
        ("NSE-ProgSheet-2026-08-13-1930", True),
        ("NSE-ProgSheet-2026-08-13-930", True),
        ("YR-ProgSheet-2026-01-02-0000", True),
        ("ABCDEFGH-ProgSheet-2026-08-13-1930", True),
        ("Voices of a Nation", False),
        ("NSE-ProgSheet-2026-08-13", False),
        ("NSE-Prog-2026-08-13-1930", False),
        ("NSE-ProgSheet-2026-08-13-19305", False),
        ("", False),
        ("TOOLONGINITIALS-ProgSheet-2026-08-13-1930", False),
    ]
    bad = []
    for stem_v, wantv in auto_cases:
        got = await p.evaluate("s => isAutoName(s)", stem_v)
        if got != wantv:
            bad.append((stem_v, got, wantv))
    s.check("10.40 isAutoName recognises exactly the generated shape", not bad, f"{bad}")

    # a stale auto name must be regenerated, not offered back
    await p.evaluate("() => { fileHandle = null;"
                     " state.meeting.fileName = 'NSE-ProgSheet-2020-01-01-0101'; }")
    fresh = await p.evaluate("() => fileBaseName()")
    s.check("10.41 a stored AUTO name is regenerated, not returned as-is",
            fresh != "NSE-ProgSheet-2020-01-01-0101"
            and re.fullmatch(r"NSE-ProgSheet-\d{4}-\d{2}-\d{2}-\d{4}", fresh) is not None,
            f"{fresh!r}")
    await p.evaluate("() => saveMeeting()")
    await p.wait_for_timeout(300)
    dlg_val = await p.locator("#saveFileName").input_value()
    s.check("10.42 the Save dialog offers a CURRENT timestamp, not the stored one",
            dlg_val != "NSE-ProgSheet-2020-01-01-0101"
            and re.fullmatch(r"NSE-ProgSheet-\d{4}-\d{2}-\d{2}-\d{4}", dlg_val) is not None,
            f"{dlg_val!r}")
    await p.keyboard.press("Escape")
    await p.wait_for_timeout(200)

    # a typed name is never regenerated
    await p.evaluate("() => { state.meeting.fileName = 'Voices of a Nation'; }")
    s.eq("10.43 a typed name is returned untouched",
         await p.evaluate("() => fileBaseName()"), "Voices of a Nation")
    await p.evaluate("() => saveMeeting()")
    await p.wait_for_timeout(300)
    s.eq("10.44 the dialog prefills a typed name unchanged",
         await p.locator("#saveFileName").input_value(), "Voices of a Nation")
    await p.keyboard.press("Escape")
    await p.wait_for_timeout(200)

    # an open file's own name wins, and drives the downloads
    await p.evaluate("() => { fileHandle = {name: 'Chapter-Meeting-Aug.nse.json'}; }")
    s.eq("10.45 an open file's name wins over the stored one",
         await p.evaluate("() => fileBaseName()"), "Chapter-Meeting-Aug")
    got = {}
    for kind, ext in (("html", ".html"), ("jpg", ".jpg")):
        async with p.expect_download(timeout=180000) as dl:
            await p.evaluate("k => pickDownload(k)", kind)
        d = await dl.value
        got[kind] = d.suggested_filename
        await d.cancel()
    s.eq("10.46 downloads match the open file's name (HTML)",
         got["html"], "Chapter-Meeting-Aug.html")
    s.eq("10.47 downloads match the open file's name (JPG)",
         got["jpg"], "Chapter-Meeting-Aug.jpg")
    await p.evaluate("() => { fileHandle = null; state.meeting.fileName = ''; }")

    # two saves in a row must not repeat the first timestamp
    t1 = await p.evaluate("() => suggestedFileStem()")
    await p.evaluate("s => { state.meeting.fileName = s; fileHandle = null; }", t1)
    await p.evaluate("() => saveMeeting()")
    await p.wait_for_timeout(250)
    second = await p.locator("#saveFileName").input_value()
    s.check("10.48 a second save offers a regenerated stamp, never the stored one",
            re.fullmatch(r"[A-Z]{1,8}-ProgSheet-\d{4}-\d{2}-\d{2}-\d{4}", second) is not None,
            f"{second!r}")
    await p.keyboard.press("Escape")
    await p.wait_for_timeout(200)

    # ================= 5. RETIRED =================
    # Everything from here to the end of this suite exercised parseClubMd,
    # applyClubSetup and the two generated .md files. Markdown save/import was
    # BUILT in V34 and REMOVED in V35, deliberately and after measurement: a JSON
    # round trip loses nothing, Markdown lost hand-tuned timing lights, flex ranges
    # and custom-role bindings, and with an autosave on every keystroke a lossy
    # format degrades a meeting each time it is reopened.
    #
    # These checks therefore failed on V35 and on every build since, for a feature
    # that is not coming back. A suite that is permanently three-red is a suite
    # people stop reading, which is the only way a real failure hides in one.
    # Deleted rather than skipped: the code they tested is gone.
    s.check("10.49 the Markdown importer is gone (V35), and stays gone",
            await p.evaluate("() => typeof parseClubMd === 'undefined'"),
            "parseClubMd is back — if that is deliberate, restore this suite from "
            "the V34 source in progsheet-src-and-tests.zip")
    s.eq("10.50 JSON is the only save format",
         await p.evaluate("() => FILE_EXT"), ".nse.json", "")

    await p.close()
