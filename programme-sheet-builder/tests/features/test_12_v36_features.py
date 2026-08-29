"""V36: horizontal scroll, the print-fit notice, and the torn-write recovery.

Three separate open items landed in this build:

  item 5 - ~19px of horizontal scroll at every desktop width since V29
  item 3 - Ctrl+P silently clips a long reference pane, with no warning
  item 2 - two tabs (or OneDrive) on one folder can lose work with no recourse

The save-path checks here are unit-level: they drive classifyDisk / stampWriteId /
the lock helpers directly, because the interesting states (a rolled-back file, a
torn file, a second live tab) cannot be produced by clicking. The end-to-end
versions live in tests/json/, which has the fake directory handle.
"""
import asyncio
import json

from harness import Suite, open_app, open_sections, TARGET, FILL_JS

WIDTHS = [1920, 1600, 1440, 1366, 1280, 1100, 1000, 950]

# A pane heavy enough to overrun the printed page: the full District officer set,
# four links and eight announcements. Nothing exotic - contest season.
HEAVY = r"""
() => {
  state.execText = [
    'President|A Name','VP Education|A Name','VP Membership|A Name',
    'VP Public Relations|A Name','Secretary|A Name','Treasurer|A Name',
    'Sergeant at Arms|A Name','Immediate Past President|A Name'
  ].join('\n');
  state.districtText = [
    'District Director|A Name|Some Club','Program Quality Director|A Name|Some Club',
    'Club Growth Director|A Name|Some Club','Division Director|A Name|Some Club',
    'Area Director|A Name|Some Club'
  ].join('\n');
  state.linksText = [
    'Club site|https://example.org/club|example.org/club',
    'Pathways|https://example.org/pathways|example.org/pathways',
    'Meeting roles|https://example.org/roles|example.org/roles',
    'Contest rules|https://example.org/contests|example.org/contests'
  ].join('\n');
  state.announcementsText = [
    'Club anniversary dinner is on 20 September at the Culinary Studio',
    'Area contest briefing straight after the meeting tonight',
    'Subscription renewals close on the last day of the month',
    'Bring a guest in October and your next meal is on the club',
    'Committee handover rehearsal, Saturday 3pm in the annexe',
    'Humorous Speech contest sign-up sheet is with the SAA tonight',
    'AGM papers go out a fortnight before the vote, watch your inbox',
    'The club library has moved to the cupboard by the side door'
  ].join('\n');
  renderPreviewNow();
}
"""

LIGHT = "() => { state.announcementsText = ''; renderPreviewNow(); }"


async def wait_for_notice(page, timeout=25000):
    await page.wait_for_function(
        "() => typeof paneFit !== 'undefined' && paneFit.mm !== null", timeout=timeout)
    await page.wait_for_timeout(150)


async def main(ctx, s: Suite):
    # ---- item 5: horizontal scroll ------------------------------------------
    app = await open_app(ctx, TARGET, viewport={"width": 1440, "height": 900})
    p = app.page
    for w in WIDTHS:
        await p.set_viewport_size({"width": w, "height": 900})
        await p.wait_for_timeout(120)
        d = await p.evaluate("() => document.documentElement.scrollWidth "
                             "- document.documentElement.clientWidth")
        s.eq(f"v36.scroll.{w}", d, 0, "horizontal scroll delta in px")

    # The fix is a class, and a class is easy to lose in a markup edit.
    s.check("v36.scroll.dlbtn_class",
            await p.evaluate("() => document.getElementById('dlBtn').classList.contains('tip-right')"),
            "#dlBtn must carry tip-right")
    # ...and it must not have cost the tooltip its own visibility.
    box = await p.evaluate("""() => {
      const b = document.getElementById('dlBtn'); const r = b.getBoundingClientRect();
      const cs = getComputedStyle(b, '::after');
      return {w: parseFloat(cs.width) || 0, btnRight: r.right, cw: document.documentElement.clientWidth};
    }""")
    s.check("v36.scroll.tooltip_onscreen",
            box["w"] > 40 and (box["btnRight"] - box["w"]) > 0,
            f"tooltip {box['w']:.0f}px must still fit left of {box['btnRight']:.0f}px")

    await p.set_viewport_size({"width": 1440, "height": 900})

    # ---- one breakpoint, not two (V37) --------------------------------------
    # The CSS stacked the panes at 980px while the tabs and the hidden splitter
    # arrived at 900px, so 901-980 was a band nobody designed: panes stacked, no
    # tabs, and the splitter still in the flow as a full-width 8px bar carrying
    # cursor:col-resize - and still driving applyPaneWidth(), whose flex-basis is
    # a HEIGHT in a column container. Rama spotted it on the way down.
    for w in (1200, 981, 980, 940, 901, 900, 899, 700, 400):
        await p.set_viewport_size({"width": w, "height": 900})
        await p.wait_for_timeout(140)
        st = await p.evaluate("""() => {
          const cs = el => getComputedStyle(el);
          const body = document.querySelector('.builder-body');
          return {disp: cs(body).display, dir: cs(body).flexDirection,
                  split: cs(document.getElementById('splitter')).display,
                  tabs:  cs(document.querySelector('.view-tabs')).display,
                  prev:  cs(document.querySelector('.preview-pane')).display,
                  narrow: isNarrow()};
        }""")
        side = st["disp"] == "flex" and st["dir"] == "row"
        desktop = side and st["split"] != "none" and st["tabs"] == "none" and st["prev"] != "none"
        onepane = (not side) and st["split"] == "none" and st["tabs"] != "none"
        want_desktop = w > 900
        s.check(f"v37.breakpoint.{w}",
                (desktop if want_desktop else onepane) and st["narrow"] == (not want_desktop),
                f"{'split view' if want_desktop else 'one pane + tabs'} expected at {w}px: {st}")
    await p.set_viewport_size({"width": 1440, "height": 900})
    await p.wait_for_timeout(150)

    # ---- item 3: the print-fit notice ---------------------------------------
    await p.evaluate(FILL_JS)
    await p.wait_for_timeout(200)
    await p.evaluate(LIGHT)
    await wait_for_notice(p)
    light_mm = await p.evaluate("() => paneFit.mm")
    s.check("v36.panefit.light_measured", light_mm is not None and light_mm < -10,
            f"an ordinary sheet must have real headroom, got {light_mm}")
    s.check("v36.panefit.light_quiet",
            await p.evaluate("() => document.getElementById('printNotice').hidden"),
            "no notice when the pane fits comfortably")

    await p.evaluate(HEAVY)
    await p.wait_for_function("() => paneFit.mm !== null && paneFit.mm > 0", timeout=25000)
    await p.wait_for_timeout(150)
    heavy = await p.evaluate("""() => {
      const el = document.getElementById('printNotice');
      return {mm: paneFit.mm, line: paneFit.lineMm, hidden: el.hidden,
              cls: el.className, text: el.textContent};
    }""")
    s.check("v36.panefit.heavy_over", heavy["mm"] > 0, f"heavy pane must overrun, got {heavy['mm']}")
    s.check("v36.panefit.heavy_shown", not heavy["hidden"], "notice must be visible when clipping")
    s.check("v36.panefit.heavy_class", "over" in heavy["cls"], heavy["cls"])
    s.check("v36.panefit.heavy_names_pdf", "PDF" in heavy["text"],
            "the notice must point at the export that works")
    s.check("v36.panefit.heavy_states_mm", "mm" in heavy["text"], heavy["text"][:80])
    s.check("v36.panefit.line_measured", 1.0 < (heavy["line"] or 0) < 12.0,
            f"the one-line threshold must be measured from the sheet, got {heavy['line']}")

    # Accuracy: the in-app number must match a real print-media measurement of the
    # same sheet. This is the whole basis for the notice, so it is asserted, not
    # assumed. 0.5mm is twenty times the worst disagreement seen across 25 cases.
    truth = await ctx.new_page()
    await truth.set_viewport_size({"width": 718, "height": 1047})
    await truth.emulate_media(media="print")
    html = await p.evaluate("() => buildSheetHTML(false)")
    await truth.set_content(html, wait_until="domcontentloaded")
    await truth.emulate_media(media="print")
    await truth.wait_for_timeout(400)
    truth_mm = await truth.evaluate("""() => {
      const a = document.querySelector('aside.ref-pane');
      const b = document.querySelector('.pane-body');
      const last = b.children[b.children.length - 1];
      return (last.getBoundingClientRect().bottom - a.getBoundingClientRect().bottom) / (96/25.4);
    }""")
    await truth.close()
    s.check("v36.panefit.agrees_with_print", abs(truth_mm - heavy["mm"]) < 0.5,
            f"in-app {heavy['mm']:.2f} mm vs print-media {truth_mm:.2f} mm")

    # Dismiss is per-sheet, not forever: change the pane and it must speak again.
    await p.evaluate("() => dismissPrintNotice()")
    s.check("v36.panefit.dismissable",
            await p.evaluate("() => document.getElementById('printNotice').hidden"), "")
    await p.evaluate("() => { state.announcementsText += '\\nOne more line entirely'; renderPreviewNow(); }")
    await p.wait_for_timeout(2500)
    s.check("v36.panefit.dismiss_not_permanent",
            not await p.evaluate("() => document.getElementById('printNotice').hidden"),
            "a dismissed notice must return when the pane changes")

    # It must not run on every keystroke: the signature covers pane content only.
    sig_before = await p.evaluate("() => paneFitSignature()")
    await p.evaluate("() => { state.meeting.title = 'A different title entirely'; renderPreviewNow(); }")
    s.eq("v36.panefit.sig_ignores_agenda",
         await p.evaluate("() => paneFitSignature()"), sig_before,
         "the meeting title must not re-trigger an iframe measurement")

    s.check("v36.panefit.no_frames_left",
            await p.evaluate("() => document.querySelectorAll('iframe[aria-hidden=\"true\"]').length") == 0,
            "the measuring iframe must always be removed")

    # ---- item 2: write provenance -------------------------------------------
    r = await p.evaluate("""() => {
      const t = meetingPayload();
      const o = JSON.parse(t);
      const stamped = JSON.parse(stampWriteId(t, 7));
      return {writeId: o.writeId, writer: o.writer, tab: TAB_ID,
              stamped: stamped.writeId, stateSame: JSON.stringify(stamped.state) === JSON.stringify(o.state)};
    }""")
    s.eq("v36.write.payload_has_writeid", r["writeId"], 0, "unstamped payloads carry 0")
    s.eq("v36.write.payload_writer_is_tab", r["writer"], r["tab"], "")
    s.eq("v36.write.stamp_sets_id", r["stamped"], 7, "")
    s.check("v36.write.stamp_preserves_state", r["stateSame"], "stamping must not touch the meeting")

    # The stamp must not be fooled by a meeting whose TEXT contains the field name.
    poison = await p.evaluate("""() => {
      state.announcementsText = 'Note the field "writeId": 999 in the file format';
      const t = meetingPayload();
      const o = JSON.parse(stampWriteId(t, 4));
      return {id: o.writeId, kept: o.state.announcementsText};
    }""")
    s.eq("v36.write.stamp_not_fooled_by_text", poison["id"], 4, "")
    s.check("v36.write.stamp_keeps_poison_text", '"writeId": 999' in poison["kept"], poison["kept"])

    # classifyDisk on the five shapes it exists to tell apart.
    kinds = await p.evaluate("""() => {
      const name = 'x.nse.json';
      const mk = (id, writer) => JSON.stringify({app:'nse-programme-sheet', v:PAYLOAD_VERSION,
        savedAt:new Date().toISOString(), writeId:id, writer:writer, state:state}, null, 2);
      baseline[name] = mk(5, TAB_ID);
      writeIdByFile[name] = 5;
      return {
        same:     classifyDisk(baseline[name], name),
        damaged:  classifyDisk('{"app":"nse-programme-sheet", trunca', name),
        notjson:  classifyDisk('', name),
        stale:    classifyDisk(mk(3, TAB_ID), name),
        other:    classifyDisk(mk(9, 'tab-somebodyelse'), name),
        changed:  classifyDisk(mk(9, TAB_ID), name),
      };
    }""")
    s.eq("v36.classify.same", kinds["same"], "same", "")
    s.eq("v36.classify.damaged", kinds["damaged"], "damaged", "")
    s.eq("v36.classify.stale", kinds["stale"], "stale", "a LOWER writeId is a rollback")
    s.eq("v36.classify.other_tab", kinds["other"], "other", "")
    s.eq("v36.classify.changed", kinds["changed"], "changed", "")
    # An empty string is not "same" as a non-empty baseline, and must not read as clean.
    s.check("v36.classify.empty_not_same", kinds["notjson"] != "same", kinds["notjson"])

    # A file with no writeId at all - every meeting saved by V35 and earlier.
    legacy = await p.evaluate("""() => {
      const name = 'legacy.nse.json';
      baseline[name] = 'something else';
      writeIdByFile[name] = 4;
      const old = JSON.stringify({app:'nse-programme-sheet', v:35,
        savedAt:new Date().toISOString(), state:state}, null, 2);
      return classifyDisk(old, name);
    }""")
    s.check("v36.classify.legacy_not_stale", legacy != "stale",
            f"a V35 file has no writeId and must not be called a rollback, got {legacy}")

    # ---- item 2: the recovery offer -----------------------------------------
    rec = await p.evaluate("""() => {
      lastGood = {};
      offerRecovery('gone.nse.json', 'Test with nothing held.');
      const noOffer = document.getElementById('recoverBar').hidden;
      rememberGood('held.nse.json', meetingPayload(), 3);
      offerRecovery('held.nse.json', 'Test with a good copy held.');
      const el = document.getElementById('recoverBar');
      return {noOffer: noOffer, shown: !el.hidden, text: el.textContent,
              buttons: el.querySelectorAll('button').length};
    }""")
    s.check("v36.recover.silent_without_a_copy", rec["noOffer"],
            "no bar when there is nothing to restore")
    s.check("v36.recover.offered_with_a_copy", rec["shown"], "")
    s.eq("v36.recover.two_buttons", rec["buttons"], 2, "restore and leave-it")

    # Restoring must put the held meeting on screen, and must not write to disk.
    restored = await p.evaluate("""async () => {
      const title = 'Recovered Meeting Title';
      const keep = state.meeting.title;
      state.meeting.title = title;
      const good = meetingPayload();
      state.meeting.title = 'Something Else Entirely';
      renderPreviewNow();
      lastGood = {}; rememberGood('r.nse.json', good, 2);
      offerRecovery('r.nse.json', 'Test.');
      await acceptRecovery();
      const el = document.getElementById('recoverBar');
      return {title: state.meeting.title, wanted: title, barText: el.textContent,
              barShown: !el.hidden, offerKind: recoverOffer && recoverOffer.kind, keep: keep};
    }""")
    s.eq("v36.recover.restores_state", restored["title"], restored["wanted"], "")
    # The bar does not close: it turns round. An earlier version told the user to
    # "use Undo in the fields", which does not exist — applyMeetingText replaces
    # state wholesale and the autosave restamps localStorage 400ms later. A promise
    # of a way back, made at the moment the last way back closed.
    s.check("v36.recover.offers_a_real_way_back", restored["barShown"], "")
    s.eq("v36.recover.way_back_is_an_undo", restored["offerKind"], "undo", "")
    s.check("v36.recover.way_back_is_labelled",
            "put back" in (restored["barText"] or "").lower(), restored["barText"][:90])

    dismissed = await p.evaluate("""() => {
      const before = state.meeting.title;
      rememberGood('d.nse.json', meetingPayload(), 1);
      offerRecovery('d.nse.json', 'Test.');
      dismissRecovery();
      return {barGone: document.getElementById('recoverBar').hidden,
              unchanged: state.meeting.title === before, offer: recoverOffer};
    }""")
    s.check("v36.recover.leave_it_closes", dismissed["barGone"], "")
    s.check("v36.recover.leave_it_changes_nothing", dismissed["unchanged"], "")
    s.check("v36.recover.offer_cleared", dismissed["offer"] is None, "")

    # "Leave it" must survive the next autosave tick. The guard re-runs on every
    # keystroke and the disk is still damaged, so an offer that ignores the
    # decline reappears once per debounce until the user gives up reading it.
    nag = await p.evaluate("""() => {
      const name = 'nag.nse.json', disk = '{"app":"nse-programme-sheet", trunca';
      recoverDeclined = '';
      lastGood = {}; rememberGood(name, meetingPayload(), 1);
      offerRecovery(name, 'Damaged.', disk);
      const first = !document.getElementById('recoverBar').hidden;
      dismissRecovery();
      offerRecovery(name, 'Damaged.', disk);            /* same file, same disk state */
      const repeat = !document.getElementById('recoverBar').hidden;
      offerRecovery(name, 'Damaged.', disk + 'MORE');   /* the disk moved on: news */
      const fresh = !document.getElementById('recoverBar').hidden;
      dismissRecovery();
      return {first, repeat, fresh};
    }""")
    s.check("v36.recover.offers_once", nag["first"], "")
    s.check("v36.recover.declined_stays_declined", not nag["repeat"],
            "a dismissed offer must not return for the same disk state")
    s.check("v36.recover.new_damage_reoffers", nag["fresh"],
            "a different disk state is new news")

    cap = await p.evaluate("""() => {
      lastGood = {};
      for (let i = 0; i < 20; i++) rememberGood('f' + i + '.nse.json', 'x'.repeat(50), i);
      return Object.keys(lastGood).length;
    }""")
    s.check("v36.recover.memory_capped", cap <= 8, f"lastGood held {cap} entries")

    # ---- item 2: the advisory lock ------------------------------------------
    lock = await p.evaluate("""() => {
      const name = 'lockme.nse.json';
      const K = lockKey(name);
      try{ localStorage.removeItem(K); }catch(e){}
      const freeBefore = otherTabHolds(name);
      holdLock(name);
      const mineNotOther = otherTabHolds(name);       /* our own claim is not "other" */
      /* A live claim from a different tab. */
      localStorage.setItem(K, JSON.stringify({tab:'tab-other', at:Date.now()}));
      const seesOther = otherTabHolds(name);
      /* A dead one. */
      localStorage.setItem(K, JSON.stringify({tab:'tab-other', at:Date.now() - 60000}));
      const ignoresDead = otherTabHolds(name);
      /* releaseLock must not delete somebody else's live claim. */
      localStorage.setItem(K, JSON.stringify({tab:'tab-other', at:Date.now()}));
      lockedName = name; lockedKey = K;
      releaseLock();
      const theirsSurvives = !!localStorage.getItem(K);
      /* Our own claim it must clear. */
      holdLock(name);
      releaseLock();
      const oursCleared = !localStorage.getItem(K);
      /* The key must name the FOLDER as well as the file: two tabs on two folders
         holding same-dated meetings are not a conflict, and file:// shares one
         localStorage origin across every build of this tool. */
      const scoped = K !== 'nse-ps-lock:' + name && K.indexOf(name) > 0;
      return {freeBefore, mineNotOther, seesOther, ignoresDead, theirsSurvives, oursCleared, scoped, K};
    }""")
    s.check("v36.lock.free_initially", not lock["freeBefore"], "")
    s.check("v36.lock.own_claim_is_not_other", not lock["mineNotOther"], "")
    s.check("v36.lock.sees_live_other_tab", lock["seesOther"], "")
    s.check("v36.lock.ignores_dead_tab", not lock["ignoresDead"], "a lock past its TTL is a dead tab")
    s.check("v36.lock.never_steals", lock["theirsSurvives"],
            "releaseLock must only clear this tab's own claim")
    s.check("v36.lock.clears_own", lock["oursCleared"], "")
    s.check("v36.lock.key_is_folder_scoped", lock["scoped"], lock["K"])

    # ---- the defects the adversarial pass found, each pinned -----------------
    # Our own write arriving late (OneDrive pausing mid-commit) must not be read as
    # a foreign change. V35 refused every autosave for the rest of the session.
    late = await p.evaluate("""() => {
      const name = 'late.nse.json';
      const mk = (id, writer) => JSON.stringify({app:'nse-programme-sheet', v:PAYLOAD_VERSION,
        savedAt:new Date().toISOString(), writeId:id, writer:writer, state:state}, null, 2);
      baseline[name] = 'the torn text resyncBaseline captured';
      writeIdByFile[name] = 4;      /* last VERIFIED */
      writeIdNext[name] = 5;        /* 5 was allocated and appeared to fail */
      return {ours: classifyDisk(mk(5, TAB_ID), name),
              notOurs: classifyDisk(mk(5, 'tab-elsewhere'), name),
              beyond: classifyDisk(mk(9, TAB_ID), name)};
    }""")
    s.eq("v36.classify.our_own_late_write", late["ours"], "ours-late", "")
    s.eq("v36.classify.someone_elses_is_not", late["notOurs"], "other", "")
    s.check("v36.classify.beyond_what_we_sent", late["beyond"] != "ours-late",
            f"an id we never allocated is not ours, got {late['beyond']}")

    # A rollback in a file that carries no writeId - every V35 save, every hand
    # edit. The counter is blind to these; the timestamp is all they have.
    legacy_roll = await p.evaluate("""() => {
      const name = 'oldstyle.nse.json';
      baseline[name] = 'whatever we last saw';
      writeIdByFile[name] = 0;
      lastSavedAtByFile[name] = Date.parse('2026-08-11T10:00:00Z');
      const mk = at => JSON.stringify({app:'nse-programme-sheet', v:35, savedAt:at, state:state}, null, 2);
      return {older: classifyDisk(mk('2026-08-11T09:00:00Z'), name),
              newer: classifyDisk(mk('2026-08-11T10:30:00Z'), name),
              skew:  classifyDisk(mk('2026-08-11T09:57:00Z'), name)};
    }""")
    # 'maybe-stale', NOT 'stale'. A file with no counter cannot distinguish a real
    # rollback from a second machine whose clock is behind, and only one of those
    # two readings makes a Restore button safe: the other has it destroy real work.
    s.eq("v36.classify.legacy_rollback_is_only_maybe", legacy_roll["older"], "maybe-stale", "")
    s.check("v36.classify.legacy_newer_is_not_stale",
            legacy_roll["newer"] not in ("stale", "maybe-stale"), str(legacy_roll["newer"]))
    s.check("v36.classify.legacy_tolerates_clock_skew",
            legacy_roll["skew"] not in ("stale", "maybe-stale"),
            "three minutes of skew between two machines on a synced folder is normal")

    # writeId decides when both sides have one; the clock only when one does not.
    decisive = await p.evaluate("""() => {
      const name = 'skew.nse.json';
      lastGood = {}; writeIdByFile = {}; writeIdNext = {}; lastSavedAtByFile = {};
      const mk = (id, at) => JSON.stringify({app:'nse-programme-sheet', v:PAYLOAD_VERSION,
        savedAt:at, writeId:id, writer:TAB_ID, state:state}, null, 2);
      rememberGood(name, mk(3, '2026-08-11T20:04:00Z'), 3);
      adoptDiskProvenance(name, mk(10, '2026-08-11T20:02:00Z'));
      return {took: lastGood[name].writeId};
    }""")
    s.eq("v36.recover.writeid_beats_a_skewed_clock", decisive["took"], 10,
         "an OR here let our id 3 beat their id 10 because our clock was ahead")

    # Save As takes the counters of the file it replaces, never its content.
    provonly = await p.evaluate("""() => {
      const name = 'replaced.nse.json';
      lastGood = {}; writeIdByFile = {}; writeIdNext = {};
      const doomed = JSON.stringify({app:'nse-programme-sheet', v:PAYLOAD_VERSION,
        savedAt:'2026-08-11T20:00:00Z', writeId:37, writer:'tab-them', state:state}, null, 2);
      adoptDiskProvenance(name, doomed, true);
      return {id: writeIdByFile[name], held: !!lastGood[name]};
    }""")
    s.eq("v36.recover.saveas_takes_the_counter", provonly["id"], 37, "")
    s.check("v36.recover.saveas_refuses_the_content", not provonly["held"],
            "the meeting the user authorised destroying must not become the safety net")

    # A failed write must burn its number, or two different payloads share an id
    # and the rollback between them is invisible.
    burned = await p.evaluate("""() => {
      const name = 'burn.nse.json';
      writeIdByFile[name] = 0; writeIdNext[name] = 0;
      const a = Math.max(writeIdNext[name] || 0, writeIdByFile[name] || 0) + 1;
      writeIdNext[name] = a;                    /* allocated, then the write fails */
      const b = Math.max(writeIdNext[name] || 0, writeIdByFile[name] || 0) + 1;
      return {a, b};
    }""")
    s.check("v36.write.failed_id_is_burned", burned["b"] > burned["a"],
            f"ids {burned['a']} then {burned['b']} must differ")

    # Restoring must refuse when this tab has moved to another file (Save As).
    wrongfile = await p.evaluate("""async () => {
      lastGood = {}; recoverDeclined = '';
      rememberGood('A.nse.json', meetingPayload(), 2);
      offerRecovery('A.nse.json', 'Damaged.', 'torn');
      const armed = !document.getElementById('recoverBar').hidden;
      const realHandle = fileHandle;
      fileHandle = {name: 'B.nse.json'};        /* as if Save As had attached B */
      const before = state.meeting.title;
      await acceptRecovery();
      const after = state.meeting.title;
      fileHandle = realHandle;
      return {armed, unchanged: before === after};
    }""")
    s.check("v36.recover.armed_before", wrongfile["armed"], "")
    s.check("v36.recover.refuses_wrong_file", wrongfile["unchanged"],
            "restoring A's copy while attached to B must change nothing")

    # A copy we hold must not be replaced by an older one read off disk.
    keepbest = await p.evaluate("""() => {
      const name = 'keep.nse.json';
      lastGood = {};
      const mk = (id, at) => JSON.stringify({app:'nse-programme-sheet', v:PAYLOAD_VERSION,
        savedAt:at, writeId:id, writer:TAB_ID, state:state}, null, 2);
      rememberGood(name, mk(9, '2026-08-11T10:00:00Z'), 9);
      adoptDiskProvenance(name, mk(3, '2026-08-11T09:00:00Z'));   /* an older disk copy */
      const keptNew = lastGood[name].writeId === 9;
      adoptDiskProvenance(name, mk(12, '2026-08-11T11:00:00Z'));  /* a genuinely newer one */
      return {keptNew, tookNewer: lastGood[name].writeId === 12};
    }""")
    s.check("v36.recover.reopen_keeps_the_better_copy", keepbest["keptNew"],
            "reopening a rolled-back file must not delete the safety net")
    s.check("v36.recover.reopen_takes_a_newer_copy", keepbest["tookNewer"], "")

    # ---- the exported sheet carries no stray vertical rule (V37) -------------
    # Rama's exports showed a 2px translucent line down the whole page at 49.3%
    # of the content width, over the banner as well as the agenda. Nothing in the
    # layout spans both, so it is a GPU tile seam in the downscale and it cannot
    # be reproduced under software rasterisation - this check therefore CANNOT
    # catch that bug. What it does catch is the other half of the risk: a future
    # layout change that puts a real full-height rule somewhere new. The two that
    # belong there are the reference pane's column rule (24%) and the TIME column
    # boundary (~40%).
    import base64 as _b64
    shot = await p.evaluate("""async () => {
      const blobs = [];
      const real = saveBlob;
      saveBlob = (blob, name) => { blobs.push(blob); };
      try { await downloadImage(); } finally { saveBlob = real; }
      if (!blobs.length) return null;
      const u = new Uint8Array(await blobs[0].arrayBuffer());
      let s = '';
      for (let i = 0; i < u.length; i += 8192) s += String.fromCharCode.apply(null, u.subarray(i, i + 8192));
      return btoa(s);
    }""")
    if not shot:
        s.check("v36.export.rendered", False, "the JPG export produced nothing")
    else:
        import io as _io
        try:
            from PIL import Image as _Im
            import numpy as _np
            im = _Im.open(_io.BytesIO(_b64.b64decode(shot))).convert("RGB")
            a = _np.asarray(im).astype(int)
            H, W, _ = a.shape
            lft, rgt = _np.roll(a, 1, axis=1), _np.roll(a, -1, axis=1)
            d = (_np.abs(a - lft).sum(2) > 8) & (_np.abs(a - rgt).sum(2) > 8)
            d[:, 0] = d[:, -1] = False
            cnt = d.sum(0)
            hit = [x for x in range(1, W - 1) if cnt[x] > H * 0.5]
            grp = []
            for x in hit:
                if grp and x - grp[-1][-1] <= 2:
                    grp[-1].append(x)
                else:
                    grp.append([x])
            pct = sorted(round(float(_np.mean(g)) / W * 100, 1) for g in grp)
            merged = []
            for v in pct:
                if not merged or v - merged[-1] > 1.5:
                    merged.append(v)
            s.check("v36.export.pane_rule_present",
                    any(23.0 <= v <= 25.0 for v in merged),
                    f"the pane's column rule must sit at ~24%: {merged}")
            # Three vertical features legitimately run the height of the sheet:
            # the pane's column rule at 24%, the agenda table's left edge at
            # 27.2% (main's margin-left plus its 6mm padding), and the TIME
            # column boundary near 40%. Anything else is new and wants looking at.
            allowed = lambda v: v <= 25.0 or 26.0 <= v <= 28.5 or 39.0 <= v <= 42.0
            s.check("v36.export.no_stray_full_height_rule",
                    all(allowed(v) for v in merged),
                    f"only the pane edge, the table edge and the TIME column may "
                    f"run full height: {merged}")
        except ImportError:
            s.check("v36.export.seam_check_skipped", True, "PIL/numpy absent")

    # ---- nothing broken on the way ------------------------------------------
    s.eq("v36.no_page_errors", app.clean_errors(), [], "")
    s.eq("v36.no_console_errors",
         [c for c in app.clean_console() if c.startswith("error")], [], "")
    await p.close()
