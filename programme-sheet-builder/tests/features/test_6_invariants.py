"""Long-standing invariants that V30 must not have broken.

The blank template totals exactly 150 minutes and a 19:00 start lands on 21:30.
Also a whole-app error sweep across the V30 features in one session.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import V29, open_app, run_suite  # noqa: E402

TOTAL_JS = """() => {
  const {rows, endMin, endClock} = computeSchedule();
  const total = rows.reduce((a, r) => a + (Number(r.seg.durMin) || 0), 0);
  return {total, endMin, endClock, rows: rows.length,
          start: state.meeting.startTime, end: state.meeting.endTime};
}"""


async def main(ctx, s):
    # ---------- V29 baseline ----------
    v29 = await open_app(ctx, V29)
    base = await v29.page.evaluate(TOTAL_JS)
    await v29.page.close()

    app = await open_app(ctx)
    p = app.page
    got = await p.evaluate(TOTAL_JS)

    s.eq("6.1 the blank template still totals exactly 150 minutes", got["total"], 150,
         f"V29 total was {base['total']}; V30 rows={got['rows']}")
    s.eq("6.2 the blank template start time is 19:00", got["start"], "19:00")
    s.eq("6.3 a 19:00 start still lands on 21:30", got["endClock"], "9:30 PM",
         f"endMin={got['endMin']}")
    s.eq("6.4 the segment count is unchanged from V29", got["rows"], base["rows"])
    s.eq("6.5 the computed end matches the declared end time",
         got["end"], "21:30")

    last_clock = await p.evaluate(
        "() => { const r = computeSchedule().rows; return r[r.length-1].clock; }")
    s.eq("6.6 the last agenda row is clocked at 9:30 PM", last_clock, "9:30 PM")

    # the end-check widget must agree
    endcheck = await p.evaluate(
        "() => { const e = document.querySelector('.end-check'); return e ? e.textContent : ''; }")
    s.check("6.7 the on-screen end check agrees (no over/under warning)",
            "9:30" in endcheck and "over" not in endcheck.lower()
            and "under" not in endcheck.lower(),
            f"end-check={endcheck.strip()[:160]!r}")

    # a different start time still lands 150 minutes later
    await p.evaluate("() => { state.meeting.startTime = '18:30'; renderPreviewNow(); }")
    s.eq("6.8 an 18:30 start lands on 9:00 PM (150 min unchanged)",
         await p.evaluate("() => computeSchedule().endClock"), "9:00 PM")
    await p.evaluate("() => { state.meeting.startTime = '19:00'; renderPreviewNow(); }")

    # ---------- the invariant survives the V30 features ----------
    await p.evaluate("() => { addCustomRole(); state.customRoles[0].label = 'Zoom Master';"
                     " state.roles[state.customRoles[0].key] = 'Priya Menon';"
                     " renderCustomRoles(); renderPreviewNow(); }")
    await p.wait_for_timeout(300)
    s.eq("6.9 adding a custom role does not change the 150 min total",
         (await p.evaluate(TOTAL_JS))["total"], 150)
    s.eq("6.10 adding a custom role does not move the 9:30 PM finish",
         (await p.evaluate(TOTAL_JS))["endClock"], "9:30 PM")

    # a fresh reset must come back to 150 too
    await p.evaluate("() => { state = defaultState(); syncFormInputs(); renderFormPane();"
                     " renderPreviewNow(); }")
    await p.wait_for_timeout(300)
    fresh = await p.evaluate(TOTAL_JS)
    s.eq("6.11 defaultState() rebuilt from scratch totals 150 minutes", fresh["total"], 150)
    s.eq("6.12 and still ends at 9:30 PM", fresh["endClock"], "9:30 PM")

    # The Language Evaluator is deliberately unticked in the template because
    # ticking it adds 3 min - guard that the default really is off.
    s.check("6.13 langeval starts unticked (it would add 3 min to the exact 150)",
            await p.evaluate("() => state.roleActive.langeval") is False)
    await p.evaluate("() => toggleRoleActive('langeval', true)")
    await p.wait_for_timeout(400)
    lg = await p.evaluate(TOTAL_JS)
    s.eq("6.14 ticking the Language Evaluator keeps 150 min (Balance absorbs the 3 min)",
         lg["total"], 150, f"endClock={lg['endClock']}")
    s.eq("6.14b and the meeting still ends at 9:30 PM", lg["endClock"], "9:30 PM")
    await p.evaluate("() => toggleRoleActive('langeval', false)")
    await p.wait_for_timeout(400)
    s.eq("6.15 unticking it returns to 150", (await p.evaluate(TOTAL_JS))["total"], 150)

    # ---------- 6.16 end-to-end error sweep across every V30 feature ----------
    await p.evaluate(
        "() => { window.showDirectoryPicker = () => Promise.reject("
        "Object.assign(new Error('no picker'), {name:'AbortError'})); }")
    seq = """async () => {
      const sid = state.segments.find(s=>s.isSpeech).id;
      catalogEdit(sid,'pathway','PM'); catalogEdit(sid,'pLevel','4');
      applyProjectChoice(state.segments.find(s=>s.id===sid), 'Controlling Your Fear');
      renderFormPane(); renderPreviewNow();
      addCustomRole(); addCustomRole();
      state.customRoles[0].label='Zoom Master'; state.roles[state.customRoles[0].key]='A B';
      state.customRoles[1].label='Joke Master';
      renderCustomRoles();
      toggleRoleActive(state.customRoles[1].key, false);
      toggleRoleActive(state.customRoles[1].key, true);
      openSaveDialog(false); closeSaveDialog();
      state.meeting.fileName = 'Sweep-Name';
      adoptState(JSON.parse(meetingPayload()));
      syncFormInputs(); renderFormPane(); renderPreviewNow();
      setMobileView('preview'); setMobileView('edit');
      toggleDownloadMenu(null); closeDownloadMenu();
      return true;
    }"""
    ok = await p.evaluate(seq)
    await p.wait_for_timeout(700)
    s.check("6.16 a full V30 feature sweep runs without throwing", ok is True)
    s.check("6.17 ZERO uncaught page errors across the whole session",
            not app.clean_errors(), str(app.clean_errors()[:5]))
    s.check("6.18 ZERO console errors across the whole session (fonts excluded)",
            not app.clean_console(), str(app.clean_console()[:5]))

    # Report anything that WAS filtered, so a real error hidden behind the font
    # filter would still be visible in the log.
    filtered = [e for e in app.errors if e not in app.clean_errors()] + \
               [c for c in app.console if c not in app.clean_console()]
    if filtered:
        print(f"    (filtered as expected network/font noise: {len(filtered)} entries)")
    s.check("6.19 every filtered console entry really is font/network noise",
            all("font" in f.lower() or "ERR_" in f or "Failed to load resource" in f
                for f in filtered),
            str(filtered[:4]))


if __name__ == "__main__":
    asyncio.run(run_suite(main, "6_invariants"))
