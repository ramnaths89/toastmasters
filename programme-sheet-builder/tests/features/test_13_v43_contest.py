"""V43 feature 13 - contest mode.

Covers the whole seam the contest work added: the mode switch and what it is
allowed to destroy, the contest role set replacing the chapter one, contestant
lists on the sheet, the Contest Committee in the printed pane, and the JSON
round trip carrying all of it.

The assertions that matter most here are the NEGATIVE ones - that switching to a
contest and back does not eat the chapter roster, and that a pre-V43 file still
loads as a chapter meeting. Those are the two ways this feature could quietly
damage work that already exists.
"""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import open_app, open_sections, run_suite  # noqa: E402


async def sheet_text(p):
    """Inner text of the preview iframe's agenda table."""
    await p.evaluate("() => renderPreviewNow()")
    await p.wait_for_timeout(350)
    return await p.frame_locator("#previewFrame").locator("table").first.inner_text()


async def pane_text(p):
    await p.evaluate("() => renderPreviewNow()")
    await p.wait_for_timeout(350)
    return await p.frame_locator("#previewFrame").locator("aside.ref-pane").first.inner_text()


async def to_contest(p):
    """Switch without the confirm dialog getting in the way."""
    await p.evaluate("() => setMeetingMode('contest')")
    await p.wait_for_timeout(400)


async def main(ctx, s):
    app = await open_app(ctx)
    p = app.page
    await open_sections(p)

    # ---------- 13.1 a fresh sheet is a chapter meeting ----------
    s.eq("13.1 default mode is chapter",
         await p.evaluate("() => state.meeting.mode"), "chapter")
    s.check("13.2 isContest() false on a fresh sheet",
            await p.evaluate("() => isContest()") is False)
    s.eq("13.3 meeting-type selector exists",
         await p.locator("#f-mode").count(), 1)
    s.eq("13.4 selector shows Chapter Meeting",
         await p.evaluate("() => document.getElementById('f-mode').value"), "chapter")
    s.check("13.5 body carries mode-chapter",
            await p.evaluate("() => document.body.classList.contains('mode-chapter')"))

    # A pristine template must switch WITHOUT a confirm, or the very first click
    # on a fresh sheet trains people to dismiss the dialog that matters.
    s.check("13.6 a fresh chapter order is pristine",
            await p.evaluate("() => runningOrderIsPristine('chapter')") is True)

    # ---------- 13.7 the switch ----------
    # Type a chapter roster first: the point of the test is that it survives.
    await p.evaluate("""() => {
      state.roles.tmod = 'Chapter TME';
      state.roles.saa = 'Chapter SAA';
      syncFormInputs();
    }""")
    await p.wait_for_timeout(200)

    await to_contest(p)
    s.eq("13.7 mode is contest", await p.evaluate("() => state.meeting.mode"), "contest")
    s.check("13.8 isContest() true", await p.evaluate("() => isContest()") is True)
    s.check("13.9 body swaps to mode-contest",
            await p.evaluate("() => document.body.classList.contains('mode-contest')"))
    s.check("13.10 selector followed the state",
            await p.evaluate("() => document.getElementById('f-mode').value") == "contest")

    # ---------- 13.11 the chapter roster survives ----------
    s.eq("13.11 chapter TME name kept through the switch",
         await p.evaluate("() => state.roles.tmod"), "Chapter TME")
    s.eq("13.12 chapter SAA name kept through the switch",
         await p.evaluate("() => state.roles.saa"), "Chapter SAA")

    # ---------- 13.13 the running order really changed ----------
    keys = await p.evaluate("() => state.segments.map(s => s.presetKey)")
    s.check("13.13 no chapter presets left in a contest order",
            not any(k in keys for k in ("welcome", "speech", "evaluation", "tabletopics")),
            f"keys={keys}")
    s.check("13.14 contest presets present",
            all(k in keys for k in ("csetup", "cbriefjudges", "contest", "cresults")),
            f"keys={keys}")
    s.eq("13.15 exactly two contest blocks in the template",
         await p.evaluate("() => state.segments.filter(s => s.isContestants).length"), 2)

    # ---------- 13.16 timings land on the published end time ----------
    s.eq("13.16 contest start time", await p.evaluate("() => state.meeting.startTime"), "18:45")
    s.eq("13.17 contest end time", await p.evaluate("() => state.meeting.endTime"), "21:30")
    total = await p.evaluate("() => state.segments.reduce((n,s)=>n+(Number(s.durMin)||0),0)")
    s.eq("13.18 contest template totals 165 min (18:45 -> 21:30)", total, 165)

    # ---------- 13.19 no Word of the Day can leak in ----------
    await p.evaluate("() => { state.roleActive.langeval = true; syncLanguageEvaluatorSegment(); }")
    await p.wait_for_timeout(150)
    s.check("13.19 a ticked Language Evaluator adds no row to a contest",
            await p.evaluate("() => state.segments.some(s => s.presetKey === 'langeval')") is False)
    await p.evaluate("() => { state.roleActive.langeval = false; }")

    # ---------- 13.20 the contest role set is what is chased ----------
    open_roles = await p.evaluate("() => openRoleLabels()")
    s.check("13.20 open roles are contest appointments, not chapter roles",
            "Chief Judge" in open_roles and "Toastmaster of the Day" not in open_roles,
            f"open={open_roles}")
    s.check("13.21 a named chapter role is not listed as open during a contest",
            "Sergeant-at-Arms" not in open_roles, f"open={open_roles}")

    # The grid in the form must be the contest one.
    await open_sections(p)
    s.eq("13.22 roles grid renders the contest appointments",
         await p.locator("#rolesGrid #r-cjudge").count(), 1)
    s.eq("13.23 chapter role fields are gone from the grid",
         await p.locator("#rolesGrid #r-tmod").count(), 0)

    # ---------- 13.24 contestants ----------
    seg_id = await p.evaluate("() => state.segments.find(s => s.isContestants).id")
    s.eq("13.24 a contest block starts with no contestants",
         await p.evaluate("id => state.segments.find(s=>s.id===id).contestants.length", seg_id), 0)
    body = await sheet_text(p)
    s.check("13.25 an empty block says so on the sheet",
            "Contestants to be confirmed" in body, body[:200])

    await p.evaluate("""id => {
      const seg = state.segments.find(s=>s.id===id);
      seg.contestants = ['Sam Ong', '', 'Alex Tan'];
    }""", seg_id)
    body = await sheet_text(p)
    s.check("13.26 contestant names print", "Sam Ong" in body and "Alex Tan" in body)
    s.check("13.27 a blank slot prints TBD rather than vanishing",
            body.count("TBD") >= 1)
    nums = await p.frame_locator("#previewFrame").locator(".contestant-list .cl-num").all_inner_texts()
    s.eq("13.28 contestants are numbered in draw order", nums, ["1.", "2.", "3."])

    # ---------- 13.29 the printed pane ----------
    pane = await pane_text(p)
    s.check("13.29 pane shows the Contest Committee", "CONTEST COMMITTEE" in pane.upper(), pane[:300])
    s.check("13.30 pane drops the Executive Committee during a contest",
            "EXECUTIVE COMMITTEE" not in pane.upper(), pane[:300])
    s.check("13.31 pane drops the Pathways legend during a contest",
            "PATHWAYS" not in pane.upper(), pane[:300])
    s.check("13.32 District Officers survive into a contest",
            "DISTRICT OFFICERS" in pane.upper(), pane[:300])

    # ---------- 13.33 the JSON round trip ----------
    # meetingPayload() already returns serialised JSON - do not stringify twice.
    payload = await p.evaluate("() => meetingPayload()")
    s.check("13.33 mode is written into the saved payload",
            json.loads(payload)["state"]["meeting"]["mode"] == "contest")
    ok = await p.evaluate("txt => adoptState(JSON.parse(txt))", payload)
    s.check("13.34 the payload re-adopts cleanly", ok is True)
    s.eq("13.35 mode survives the round trip",
         await p.evaluate("() => state.meeting.mode"), "contest")
    s.eq("13.36 contestants survive the round trip",
         await p.evaluate("() => state.segments.find(s=>s.isContestants).contestants"),
         ["Sam Ong", "", "Alex Tan"])

    # ---------- 13.37 a hostile / legacy file ----------
    # A pre-V43 file carries no mode at all and IS a chapter meeting.
    legacy = await p.evaluate("""() => {
      const st = JSON.parse(JSON.stringify(state));
      delete st.meeting.mode;
      return JSON.stringify({state: st});
    }""")
    await p.evaluate("txt => adoptState(JSON.parse(txt))", legacy)
    s.eq("13.37 a file with no mode loads as a chapter meeting",
         await p.evaluate("() => state.meeting.mode"), "chapter")

    # Junk in the mode field is reported, not silently swallowed.
    await p.evaluate("""() => {
      const st = JSON.parse(JSON.stringify(state));
      st.meeting.mode = 'banquet';
      adoptState({state: st});
    }""")
    s.eq("13.38 an unknown mode falls back to chapter",
         await p.evaluate("() => state.meeting.mode"), "chapter")
    s.check("13.39 and the fallback is reported as a repair",
            any("banquet" in r for r in await p.evaluate("() => lastAdoptRepairs")),
            str(await p.evaluate("() => lastAdoptRepairs")))

    # A string where the contestant array should be must not spread per-character.
    await p.evaluate("""() => {
      const st = JSON.parse(JSON.stringify(state));
      st.meeting.mode = 'contest';
      st.segments = buildContestSegments();
      st.segments.find(s => s.isContestants).contestants = 'abcde';
      adoptState({state: st});
    }""")
    s.eq("13.40 a string in contestants becomes an empty list, not 5 letters",
         await p.evaluate("() => state.segments.find(s=>s.isContestants).contestants"), [])

    # ---------- 13.41 switching back ----------
    await p.evaluate("() => setMeetingMode('chapter')")
    await p.wait_for_timeout(400)
    s.eq("13.41 back to chapter", await p.evaluate("() => state.meeting.mode"), "chapter")
    keys = await p.evaluate("() => state.segments.map(s => s.presetKey)")
    s.check("13.42 chapter running order restored",
            "welcome" in keys and "speech" in keys, f"keys={keys}")
    s.check("13.43 no contest blocks left behind",
            await p.evaluate("() => state.segments.filter(s=>s.isContestants).length") == 0)
    s.eq("13.44 chapter start time restored",
         await p.evaluate("() => state.meeting.startTime"), "19:00")
    pane = await pane_text(p)
    s.check("13.45 the Executive Committee comes back", "EXECUTIVE COMMITTEE" in pane.upper())
    s.check("13.46 the Pathways legend comes back", "PATHWAYS" in pane.upper())

    # ================= the adversarial round =================
    # Everything below was found by attacking the V43 diff rather than by any
    # check above passing or failing. Each one is a way real work was destroyed
    # or a sheet was silently wrong.

    # ---------- 13.49 pristine must notice EVERY editable field ----------
    # The first runningOrderIsPristine() compared eight fields and missed five.
    # Editing any of these and switching mode wiped the running order with no
    # confirm, and the wipe was then autosaved over the file on disk.
    for cid, js, what in [
        ("13.49", "() => { state.segments.find(s=>s.isSpeech).pathway = 'DL'; }", "pathway"),
        ("13.50", "() => { state.segments.find(s=>s.isSpeech).pLevel = '2'; }", "level"),
        ("13.51", "() => { const s0=state.segments.find(s=>s.isSpeech); s0.signalMin=5.5; }", "timing lights"),
        ("13.52", "() => { state.segments.find(s=>s.isSpeech).signalsManual = true; }", "manual-lights flag"),
        ("13.53", "() => { state.segments.find(s=>s.presetKey==='awards').sub = 'Best Speaker only'; }", "sub-note"),
        ("13.54", "() => { state.segments.find(s=>s.flexible).flexMax = 25; }", "flex range"),
        ("13.55", "() => { state.segments.find(s=>s.isSpeech).speakerName = 'Someone'; }", "speaker name"),
    ]:
        await p.evaluate("() => { adoptState({state: defaultState()}); }")
        s.check(f"{cid} a fresh order is pristine before editing the {what}",
                await p.evaluate("() => runningOrderIsPristine('chapter')") is True)
        await p.evaluate(js)
        s.check(f"{cid}b editing the {what} makes it NOT pristine",
                await p.evaluate("() => runningOrderIsPristine('chapter')") is False,
                f"{what} edit went undetected — mode switch would wipe it silently")

    # A row added or removed must also count.
    await p.evaluate("() => { adoptState({state: defaultState()}); state.segments.pop(); }")
    s.check("13.56 a deleted row makes it NOT pristine",
            await p.evaluate("() => runningOrderIsPristine('chapter')") is False)

    # ---------- 13.57 the pane-fit signature follows the contest pane ----------
    await p.evaluate("() => { adoptState({state: defaultState()}); }")
    sig_chapter = await p.evaluate("() => paneFitSignature()")
    await to_contest(p)
    sig_contest = await p.evaluate("() => paneFitSignature()")
    s.check("13.57 signature changes with the meeting mode", sig_chapter != sig_contest,
            "a stale chapter measurement would be reused for the contest pane")
    before = await p.evaluate("() => paneFitSignature()")
    await p.evaluate("() => { state.roles.cjudge = 'A Very Long Chief Judge Name Indeed'; }")
    s.check("13.58 signature changes when a contest appointment is named",
            before != await p.evaluate("() => paneFitSignature()"))
    before = await p.evaluate("() => paneFitSignature()")
    await p.evaluate("() => { state.roleActive.ctally2 = false; }")
    s.check("13.59 signature changes when an appointment is unticked",
            before != await p.evaluate("() => paneFitSignature()"))
    await p.evaluate("() => { state.roleActive.ctally2 = true; }")

    # ---------- 13.60 a custom role reaches the contest sheet ----------
    await p.evaluate("""() => {
      state.customRoles = [{key:'cr1', label:'Contest Sergeant Reserve'}];
      state.roleActive.cr1 = true;
      state.roles.cr1 = 'Kim Wong';
    }""")
    pane = await pane_text(p)
    s.check("13.60 a custom role prints in the Contest Committee",
            "Contest Sergeant Reserve" in pane and "Kim Wong" in pane,
            "collected and chased but printed nowhere: " + pane[:250])
    s.check("13.61 a custom role is still chased as open when blank",
            "Contest Sergeant Reserve" in await p.evaluate(
                "() => { state.roles.cr1=''; return openRoleLabels(); }"))
    await p.evaluate("() => { state.customRoles = []; delete state.roles.cr1; }")

    # ---------- 13.62 unticking Test Speaker takes its row with it ----------
    await p.evaluate("() => { adoptState({state: defaultState()}); setMeetingMode('contest'); }")
    await p.wait_for_timeout(300)
    s.check("13.62 the test-speech row is in a fresh contest order",
            await p.evaluate(
                "() => state.segments.some(s=>s.presetKey==='ctestspeech' && !s.disabled)"))
    await p.evaluate("() => toggleRoleActive('ctestspk', false)")
    await p.wait_for_timeout(250)
    s.check("13.63 unticking Test Speaker disables the Test Speaker Speech row",
            await p.evaluate(
                "() => state.segments.some(s=>s.presetKey==='ctestspeech' && s.disabled)"),
            "the row stood in the running order still naming a dropped appointment")
    body = await sheet_text(p)
    s.check("13.64 and it is gone from the printed running order",
            "Test Speaker Speech" not in body)
    await p.evaluate("() => toggleRoleActive('ctestspk', true)")
    await p.wait_for_timeout(250)
    s.check("13.65 ticking it again brings the row back",
            await p.evaluate(
                "() => state.segments.some(s=>s.presetKey==='ctestspeech' && !s.disabled)"))
    # An appointment that owns nothing must NOT strip rows.
    await p.evaluate("() => toggleRoleActive('ctally1', false)")
    await p.wait_for_timeout(250)
    s.check("13.66 unticking a tally counter leaves the ballot-collection rows standing",
            await p.evaluate(
                "() => state.segments.filter(s=>s.presetKey==='ccollect' && !s.disabled).length") == 2)
    await p.evaluate("() => toggleRoleActive('ctally1', true)")

    # ---------- 13.67 a customised clock survives the mode switch ----------
    await p.evaluate("""() => {
      adoptState({state: defaultState()});
      state.meeting.startTime = '19:30';
      state.meeting.endTime = '22:00';
      setMeetingMode('contest');
    }""")
    await p.wait_for_timeout(300)
    s.eq("13.67 a club's own start time is not overwritten",
         await p.evaluate("() => state.meeting.startTime"), "19:30")
    s.eq("13.68 a club's own end time is not overwritten",
         await p.evaluate("() => state.meeting.endTime"), "22:00")
    # ...but the default clock still moves with the mode.
    await p.evaluate("() => { adoptState({state: defaultState()}); setMeetingMode('contest'); }")
    await p.wait_for_timeout(300)
    s.eq("13.69 the default clock still follows the mode",
         await p.evaluate("() => state.meeting.startTime"), "18:45")

    # ---------- 13.70 a cleared contestant list is reported ----------
    await p.evaluate("""() => {
      const st = JSON.parse(JSON.stringify(state));
      st.segments.find(s => s.isContestants).contestants = 'abcde';
      adoptState({state: st});
    }""")
    s.check("13.70 clearing a malformed contestant list is reported as a repair",
            any("contestant" in r.lower() for r in await p.evaluate("() => lastAdoptRepairs")),
            str(await p.evaluate("() => lastAdoptRepairs")))

    # ---------- 13.71 renaming a contest block mirrors into Contestants ----------
    await p.evaluate("() => { adoptState({state: defaultState()}); setMeetingMode('contest'); }")
    await p.wait_for_timeout(300)
    await open_sections(p)
    cid2 = await p.evaluate("() => state.segments.find(s=>s.isContestants).id")
    await p.evaluate("id => updateSeg(id, 'title', 'Humorous Speech Contest')", cid2)
    await p.wait_for_timeout(250)
    field = await p.locator(f'.ct-block[data-ct-id="{cid2}"] .ct-title').input_value()
    s.eq("13.71 the Contestants section follows a rename made in Programme Segments",
         field, "Humorous Speech Contest")

    # ---------- 13.72 the Area Director is not printed twice ----------
    # Caught by eye on the rendered PDF, not by any assertion above: the Area
    # Director held a contest appointment (they give the closing address) AND is
    # a District Officer, so the pane listed "Area Director / <name>" twice in
    # the same column, about 20 mm apart.
    await p.evaluate("""() => {
      adoptState({state: defaultState()});
      setMeetingMode('contest');
      state.roles.cadirector = 'Pat Chen';
      state.districtText = 'Area Director|Pat Chen|<Their Club>';
    }""")
    await p.wait_for_timeout(300)
    pane = await pane_text(p)
    s.eq("13.72 'Area Director' appears exactly once in the printed pane",
         pane.upper().count("AREA DIRECTOR"), 1, pane[:300])
    body = await sheet_text(p)
    s.check("13.73 but the Closing Address still names them in the running order",
            "Pat Chen" in body, body[-400:])

    # ---------- 13.47 nothing threw the whole way through ----------
    s.check("13.47 no uncaught page errors", not app.clean_errors(), str(app.clean_errors()[:3]))
    s.check("13.48 no console errors", not app.clean_console(), str(app.clean_console()[:3]))

    await p.close()


if __name__ == "__main__":
    asyncio.run(run_suite(main, "13_v43_contest"))
