"""V31 changes: collapsed speech cards, the speaker-count stepper, the retired
Handmade theme, sections shut on load, and the Balance Segments text button.

(PNG removal is asserted in suite 4, alongside the exports it changed.)
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import PREV, expand_speech, open_app, open_sections, run_suite  # noqa: E402

CARD = "#speechList .speech-card"


async def card_ids(p):
    return await p.evaluate(
        "() => [...document.querySelectorAll('#speechList .speech-card')].map(c=>c.dataset.spId)")


async def open_cards(p):
    return await p.evaluate(
        "() => [...document.querySelectorAll('#speechList .speech-card.open')]"
        ".map(c=>c.dataset.spId)")


async def counts(p):
    return await p.evaluate(
        "() => ({sp: speechSegs().length, ev: evalSegs().length,"
        " label: (document.getElementById('spCount')||{}).textContent,"
        " cards: document.querySelectorAll('#speechList .speech-card').length})")


async def main(ctx, s):
    app = await open_app(ctx)
    p = app.page

    # ================= 5. every section shut on load =================
    shut = await p.evaluate(
        "() => [...document.querySelectorAll('details.section')].map(d=>[d.id||'(anon)', d.open])")
    s.check("8.1 every <details class=section> is shut on a fresh load",
            len(shut) > 0 and not any(o for _, o in shut), str(shut))
    # V43 added a sixth section, Contestants, which is display:none unless the
    # meeting is a contest. Pin BOTH numbers: the count in the DOM, and the count
    # a person actually sees on a fresh chapter sheet - which is still five, and
    # is the thing the original assertion was really about.
    s.eq("8.2 there are 6 collapsible sections in the DOM", len(shut), 6)
    visible = await p.evaluate(
        "() => [...document.querySelectorAll('details.section')]"
        ".filter(d => d.offsetParent !== null).length")
    s.eq("8.2b five of them are visible on a fresh chapter sheet", visible, 5)
    s.eq("8.3 no section carries the open attribute in the markup",
         await p.evaluate("() => document.querySelectorAll('details.section[open]').length"), 0)

    # ...and the content behind them is still fully rendered.
    s.check("8.4 renderSpeechCards populated while its section is shut",
            await p.evaluate("() => document.querySelectorAll('#speechList .speech-card').length") == 4)
    club = await p.evaluate("() => document.getElementById('f-clubName').value")
    s.check("8.5 syncFormInputs filled the meeting fields while shut",
            club.startswith("Nee Soon"), f"{club!r}")
    s.check("8.6 the roles inputs exist while shut",
            await p.evaluate("() => !!document.getElementById('r-tmod')"))
    await p.evaluate("() => { addCustomRole(); state.customRoles[0].label='Zoom Master';"
                     " renderCustomRoles(); }")
    s.check("8.7 renderCustomRoles populated while its section is shut",
            await p.evaluate("() => document.querySelectorAll('#customRoles .cr-row').length") == 1)
    s.check("8.8 the preview still renders with every section shut",
            "Toastmasters" in await p.frame_locator("#previewFrame").locator("body").inner_text())
    await p.evaluate("() => { removeCustomRole(state.customRoles[0].key); }")
    p.on("dialog", lambda d: asyncio.ensure_future(d.accept()))

    # ...and after loading a saved meeting.
    await p.evaluate(
        """() => { const o = JSON.parse(meetingPayload());
                   o.state.meeting.title = 'Reloaded Meeting';
                   applyMeetingText(JSON.stringify(o), 'x.nse.json'); }""")
    await p.wait_for_timeout(600)
    s.check("8.9 sections are still shut after loading a saved meeting",
            await p.evaluate("() => document.querySelectorAll('details.section[open]').length") == 0)
    s.check("8.10 the loaded meeting still populated the form",
            await p.evaluate("() => document.getElementById('f-title').value") == "Reloaded Meeting")
    s.check("8.11 the loaded meeting still rendered its speech cards",
            await p.evaluate("() => document.querySelectorAll('#speechList .speech-card').length") == 4)

    # ================= 1. speech cards collapse =================
    await open_sections(p)
    ids = await card_ids(p)
    s.eq("8.12 four speech cards, each with a data-sp-id", len(ids), 4)
    s.check("8.13 every card id is unique and non-empty",
            len(set(ids)) == 4 and all(ids), str(ids))
    s.eq("8.14 all speech cards start collapsed", await open_cards(p), [])
    s.eq("8.15 a collapsed card renders an empty .sc-details",
         (await p.locator(f"{CARD} .sc-details").first.inner_html()).strip(), "")
    s.check("8.16 a collapsed card's details are not visible",
            not await p.locator(f"{CARD} .sc-details").first.is_visible())

    head = p.locator(f"{CARD} .sc-head").first
    s.check("8.17 the head carries a grip", await head.locator(".sc-grip").count() == 1)
    # the badge is upper-cased by CSS, so compare case-insensitively
    s.eq("8.18 the head badge reads 'Speech 1'",
         (await head.locator(".sc-badge").inner_text()).strip().lower(), "speech 1")
    s.check("8.19 the head carries a name slot", await head.locator(".sc-name").count() == 1)
    s.check("8.20 the head carries a summary", await head.locator(".sc-sum").count() == 1)
    s.check("8.21 the head carries a remove button", await head.locator(".sc-remove").count() == 1)
    s.check("8.22 the head carries a caret", await head.locator(".caret").count() == 1)
    s.eq("8.23 a blank speech summarises as 'no project yet'",
         (await head.locator(".sc-sum").inner_text()).split(" · ")[0], "no project yet")
    s.eq("8.24 a blank speech shows an em dash for the speaker",
         (await head.locator(".sc-name").inner_text()).strip(), "—")

    # ---- expand / collapse ----
    await head.click()
    await p.wait_for_timeout(250)
    s.eq("8.25 clicking the head expands that card", await open_cards(p), [ids[0]])
    s.check("8.26 the expanded card shows its fields",
            await p.locator(f"{CARD}[data-sp-id='{ids[0]}'] .sc-details").is_visible())
    s.eq("8.27 the caret flips when open",
         (await p.locator(f"{CARD}[data-sp-id='{ids[0]}'] .caret").inner_text()).strip(), "▴")
    s.check("8.28 the other three cards stay collapsed",
            not await p.locator(f"{CARD}[data-sp-id='{ids[1]}'] .sc-details").is_visible())

    await p.locator(f"{CARD}[data-sp-id='{ids[2]}'] .sc-head").click()
    await p.wait_for_timeout(250)
    s.eq("8.29 a second card can be open at the same time",
         sorted(await open_cards(p)), sorted([ids[0], ids[2]]))

    await p.locator(f"{CARD}[data-sp-id='{ids[0]}'] .sc-head").click()
    await p.wait_for_timeout(250)
    s.eq("8.30 clicking an open head collapses it again", await open_cards(p), [ids[2]])
    s.eq("8.31 expandedSpeeches tracks exactly the open cards",
         await p.evaluate("() => [...expandedSpeeches]"), [ids[2]])

    # clicking the grip must NOT toggle
    await p.locator(f"{CARD}[data-sp-id='{ids[1]}'] .sc-grip").click()
    await p.wait_for_timeout(200)
    s.check("8.32 clicking the drag grip does not expand the card",
            ids[1] not in await open_cards(p), str(await open_cards(p)))

    # ---- the combobox still works inside an expanded card ----
    await expand_speech(p, ids[1])
    cbx = p.locator(f"{CARD}[data-sp-id='{ids[1]}'] .cbx").first
    s.check("8.33 an expanded card contains a project combobox", await cbx.count() == 1)
    await cbx.locator(".cbx-btn").click()
    await p.wait_for_timeout(200)
    s.check("8.34 the combobox opens inside an expanded card",
            "open" in (await cbx.get_attribute("class") or ""))
    await cbx.locator(".cbx-input").fill("Ice Breaker")
    await p.wait_for_timeout(200)
    await cbx.locator(".cbx-opt:not(.hide)").first.click()
    await p.wait_for_timeout(400)
    s.eq("8.35 picking a project inside an expanded card sets it",
         await p.evaluate("id => state.segments.find(s=>s.id===id).project", ids[1]),
         "Ice Breaker")
    s.check("8.36 and its timing lights follow the project",
            await p.evaluate("id => { const s=state.segments.find(x=>x.id===id);"
                             " return [s.signalMin, s.signalMax]; }", ids[1]) == [4, 6])
    s.check("8.37 the collapsed heads of other cards still say 'no project yet'",
            "no project yet" in await p.locator(
                f"{CARD}[data-sp-id='{ids[3]}'] .sc-sum").inner_text())
    s.check("8.38 the expanded card's own head summary picked up the project",
            "Ice Breaker" in await p.locator(
                f"{CARD}[data-sp-id='{ids[1]}'] .sc-sum").inner_text())

    # ---- refreshCardPreview must hit the RIGHT card (the pre-emptive fix) ----
    # Only card ids[1] and ids[2] are open, so a by-index lookup into .sc-preview
    # would write speech 2's text into speech 1's node. Give each speech a
    # distinct title, then refresh them all and check each preview.
    await expand_speech(p, ids[0])
    await expand_speech(p, ids[3])
    await p.evaluate(
        """ids => { ids.forEach((id,i)=>{ const sg = state.segments.find(s=>s.id===id);
                      sg.speechTitle = 'TITLE-' + i; }); }""", ids)
    # collapse cards 0 and 3 so the open set is sparse: only 1 and 2 remain
    await p.evaluate("ids => { toggleSpeech(ids[0]); }", ids)
    await p.wait_for_timeout(200)
    await p.evaluate("ids => { toggleSpeech(ids[3]); }", ids)
    await p.wait_for_timeout(250)
    s.eq("8.39 precondition: only the middle two cards are open",
         sorted(await open_cards(p)), sorted([ids[1], ids[2]]))
    await p.evaluate(
        "ids => ids.forEach(id => refreshCardPreview(state.segments.find(s=>s.id===id)))", ids)
    await p.wait_for_timeout(200)
    previews = await p.evaluate(
        """() => [...document.querySelectorAll('#speechList .speech-card')].map(c=>{
             const el = c.querySelector('.sc-preview');
             return [c.dataset.spId, el ? el.textContent : null]; })"""
    )
    mism = []
    for i, (cid, txt) in enumerate(previews):
        if txt is None:
            continue                      # collapsed card: no preview node, correct
        if f"TITLE-{i}" not in txt:
            mism.append((i, cid, txt[:80]))
    s.check("8.40 refreshCardPreview writes into the card it was given, not by index",
            not mism, f"{mism}")
    s.eq("8.41 collapsed cards have no .sc-preview node at all",
         [c for c, t in previews if t is None], [ids[0], ids[3]])

    # ---- typing a speaker name updates the collapsed head ----
    await p.evaluate("id => { updSpeech(id,'speakerName','Ada Lovelace'); }", ids[2])
    await p.wait_for_timeout(300)
    s.eq("8.42 typing a speaker name updates that card's head",
         (await p.locator(f"{CARD}[data-sp-id='{ids[2]}'] .sc-name").inner_text()).strip(),
         "Ada Lovelace")
    await p.evaluate("ids => { toggleSpeech(ids[2]); }", ids)
    await p.wait_for_timeout(250)
    s.eq("8.43 the name survives collapsing the card",
         (await p.locator(f"{CARD}[data-sp-id='{ids[2]}'] .sc-name").inner_text()).strip(),
         "Ada Lovelace")
    s.check("8.44 a collapsed head still summarises evaluator state",
            "Ev: " in await p.locator(f"{CARD}[data-sp-id='{ids[2]}'] .sc-sum").inner_text())

    # ---- expandedSpeeches must not travel in the .json ----
    payload = await p.evaluate("() => meetingPayload()")
    s.check("8.45 expandedSpeeches is not persisted into the .json",
            "expandedSpeeches" not in payload and "sc-details" not in payload, "")

    # ---- drag to reorder with cards collapsed ----
    await p.evaluate("() => { expandedSpeeches.clear(); renderSpeechCards(); }")
    await p.wait_for_timeout(250)
    names = ["A one", "B two", "C three", "D four"]
    await p.evaluate(
        "([ids,ns]) => { ids.forEach((id,i)=>{"
        " state.segments.find(s=>s.id===id).speakerName = ns[i]; });"
        " renderSpeechCards(); }", [ids, names])
    await p.wait_for_timeout(250)
    before_order = await p.evaluate("() => speechSegs().map(s=>s.speakerName)")
    # drive the app's own drag handlers (HTML5 DnD is not scriptable end-to-end)
    moved = await p.evaluate(
        """ids => {
             const dt = {effectAllowed:'', dropEffect:'', setData(){}, getData(){return '';}};
             const card = id => document.querySelector(`.speech-card[data-sp-id="${id}"]`);
             const ev = (t, tgt) => ({type:t, dataTransfer:dt, currentTarget:tgt,
                                      clientY: tgt.getBoundingClientRect().bottom - 2,
                                      preventDefault(){}, stopPropagation(){}});
             spDragStart(ev('dragstart', card(ids[0])), ids[0]);
             spDragOver(ev('dragover', card(ids[2])), ids[2]);
             spDrop(ev('drop', card(ids[2])), ids[2]);
             spDragEnd(ev('dragend', card(ids[0])));
             return speechSegs().map(s=>s.speakerName);
           }""", ids)
    await p.wait_for_timeout(350)
    s.check("8.46 drag-to-reorder still moves a collapsed card",
            moved != before_order and sorted(moved) == sorted(before_order),
            f"before={before_order} after={moved}")
    s.eq("8.47 reordering keeps four speeches", len(moved), 4)
    heads = [x.strip() for x in await p.locator(f"{CARD} .sc-name").all_inner_texts()]
    # a blank speaker renders as an em dash in the head
    want_heads = [n or "\u2014" for n in moved]
    s.check("8.48 the rendered heads follow the new order", heads == want_heads,
            f"{heads} vs {want_heads}")
    s.check("8.49 evaluations stay paired after a reorder",
            await p.evaluate("() => evalSegs().length") == 4)

    # ================= 2. the speaker-count stepper =================
    for eid in ("spDec", "spCount", "spInc"):
        s.check(f"8.50 #{eid} exists", await p.locator(f"#{eid}").count() == 1)
    c = await counts(p)
    s.eq("8.51 the stepper label starts at 4", c["label"], "4")
    s.eq("8.52 speeches and evaluations start in sync", (c["sp"], c["ev"]), (4, 4))

    # clicking the stepper must not toggle the <details> it sits in
    await p.evaluate("() => { document.getElementById('speechSection').open = true; }")
    await p.locator("#spInc").click()
    await p.wait_for_timeout(400)
    s.check("8.53 clicking + does not close the section it sits in",
            await p.evaluate("() => document.getElementById('speechSection').open") is True)
    c = await counts(p)
    s.eq("8.54 + adds one speech and one evaluation", (c["sp"], c["ev"]), (5, 5))
    s.eq("8.55 the count label follows", c["label"], "5")
    s.eq("8.56 a card is rendered for the new speech", c["cards"], 5)

    await p.locator("#spDec").click()
    await p.wait_for_timeout(400)
    c = await counts(p)
    s.eq("8.57 - removes one pair", (c["sp"], c["ev"], c["label"]), (4, 4, "4"))

    # the section must survive - was it closed by the click?
    s.check("8.58 clicking - does not close the section either",
            await p.evaluate("() => document.getElementById('speechSection').open") is True)

    # ---- range clamps + disabled ends ----
    await p.evaluate("() => setSpeechCount(8)")
    await p.wait_for_timeout(500)
    c = await counts(p)
    s.eq("8.59 the stepper reaches 8", (c["sp"], c["ev"], c["label"]), (8, 8, "8"))
    s.check("8.60 + is disabled at 8", await p.locator("#spInc").is_disabled())
    s.check("8.61 - is enabled at 8", not await p.locator("#spDec").is_disabled())
    await p.evaluate("() => setSpeechCount(99)")
    await p.wait_for_timeout(400)
    s.eq("8.62 setSpeechCount(99) clamps to 8",
         await p.evaluate("() => speechSegs().length"), 8)

    await p.evaluate("() => setSpeechCount(1)")
    await p.wait_for_timeout(600)
    c = await counts(p)
    s.eq("8.63 the stepper reaches 1", (c["sp"], c["ev"], c["label"]), (1, 1, "1"))
    s.check("8.64 - is disabled at 1", await p.locator("#spDec").is_disabled())
    s.check("8.65 + is enabled at 1", not await p.locator("#spInc").is_disabled())
    await p.evaluate("() => setSpeechCount(0)")
    await p.wait_for_timeout(300)
    s.eq("8.66 setSpeechCount(0) clamps to 1",
         await p.evaluate("() => speechSegs().length"), 1)
    await p.evaluate("() => setSpeechCount(-5)")
    await p.wait_for_timeout(300)
    s.eq("8.67 setSpeechCount(-5) clamps to 1",
         await p.evaluate("() => speechSegs().length"), 1)

    # ---- 4 -> 8 -> 1 -> 4 leaves a coherent state ----
    await p.evaluate("() => setSpeechCount(4)")
    await p.wait_for_timeout(600)
    final = await p.evaluate(
        """() => {
             const sp = speechSegs(), ev = evalSegs();
             const ids = state.segments.map(s=>s.id);
             return {sp: sp.length, ev: ev.length,
                     dupIds: ids.length !== new Set(ids).size,
                     stale: [...expandedSpeeches].filter(id => !sp.some(s=>s.id===id)),
                     cards: document.querySelectorAll('#speechList .speech-card').length,
                     headings: sp.map((s,i)=>speechHeading(s).startsWith('Prepared Speech '+(i+1)))};
           }"""
    )
    s.eq("8.68 4 -> 8 -> 1 -> 4 ends with 4 speeches and 4 evaluations",
         (final["sp"], final["ev"]), (4, 4))
    s.check("8.69 no duplicate segment ids after the round trip", not final["dupIds"])
    s.eq("8.70 no stale id left in expandedSpeeches", final["stale"], [])
    s.eq("8.71 the card list matches the speech count", final["cards"], 4)
    s.check("8.72 speech headings renumber 1..4", all(final["headings"]), str(final["headings"]))
    s.check("8.73 no evaluation is orphaned (every speech has its pair)",
            await p.evaluate(
                "() => speechSegs().every((s,i)=> !!evalSegs()[i])"))
    n_prep = await p.frame_locator("#previewFrame").locator(
        ".item-title").evaluate_all(
        "els => els.filter(e => /^Prepared Speech \\d/.test(e.textContent)).length")
    s.eq("8.74 the preview shows exactly 4 prepared speeches", n_prep, 4)

    # removing a card directly must not orphan its evaluation either
    ids = await card_ids(p)
    await expand_speech(p, ids[1])
    await p.evaluate("id => removeSpeechSlot(id)", ids[1])
    await p.wait_for_timeout(400)
    s.eq("8.75 removing one card removes exactly one speech and one evaluation",
         await p.evaluate("() => [speechSegs().length, evalSegs().length]"), [3, 3])
    s.eq("8.76 removing a card drops it from expandedSpeeches",
         await p.evaluate("() => [...expandedSpeeches]"), [])
    await p.evaluate("() => setSpeechCount(4)")
    await p.wait_for_timeout(500)

    # ---- the end-check complains when the count is not 4 ----
    await p.evaluate("() => setSpeechCount(6)")
    await p.wait_for_timeout(600)
    ec = await p.evaluate(
        "() => { const e=document.querySelector('.end-check'); return e ? e.textContent : ''; }")
    banner = await p.evaluate(
        "() => { const b=document.getElementById('banner'); return b ? b.textContent : ''; }")
    s.check("8.77 moving off 4 speeches is flagged to the user",
            "standard is four" in banner or "over" in ec.lower() or "under" in ec.lower(),
            f"banner={banner[:120]!r} endcheck={ec.strip()[:120]!r}")
    await p.evaluate("() => setSpeechCount(4)")
    await p.wait_for_timeout(600)
    s.eq("8.78 back at 4 the meeting totals 150 minutes again",
         await p.evaluate(
             "() => computeSchedule().rows.reduce((a,r)=>a+(Number(r.seg.durMin)||0),0)"), 150)
    s.eq("8.79 and lands on 9:30 PM again",
         await p.evaluate("() => computeSchedule().endClock"), "9:30 PM")

    # ================= 3. Handmade theme retired =================
    s.eq("8.80 THEMES has exactly 5 entries", await p.evaluate("() => THEMES.length"), 5)
    s.eq("8.81 the five theme keys are the expected ones",
         await p.evaluate("() => THEMES.map(t=>t.key)"),
         ["classic", "zine", "swiss", "brutalist", "neomemphis"])
    s.check("8.82 'handmade' is in RETIRED_THEMES",
            await p.evaluate("() => RETIRED_THEMES.includes('handmade')"))
    s.eq("8.83 the Sheet style dropdown offers exactly 5",
         await p.locator("#f-theme option").count(), 5)
    s.check("8.84 the dropdown offers no Handmade option",
            "handmade" not in (await p.locator("#f-theme").inner_html()).lower())

    res = await p.evaluate(
        """() => { try { bindTheme('handmade'); return {theme: state.theme, err: null}; }
                   catch(e){ return {theme: state.theme, err: String(e)}; } }""")
    s.eq("8.85 bindTheme('handmade') falls back to classic", res["theme"], "classic")
    s.check("8.86 bindTheme('handmade') throws nothing", res["err"] is None, str(res["err"]))

    loaded = await p.evaluate(
        """() => { const o = JSON.parse(meetingPayload());
                   o.state.theme = 'handmade';
                   try { const ok = adoptState(o); syncFormInputs(); renderPreviewNow();
                         return {ok, theme: state.theme, err:null}; }
                   catch(e){ return {ok:false, theme:state.theme, err:String(e)}; } }""")
    s.check("8.87 a saved meeting with theme 'handmade' loads without error",
            loaded["ok"] is True and loaded["err"] is None, str(loaded["err"]))
    s.eq("8.88 and its theme falls back to classic", loaded["theme"], "classic")
    await p.wait_for_timeout(400)
    body_cls = await p.frame_locator("#previewFrame").locator("body").get_attribute("class")
    s.check("8.89 the sheet renders with a real theme class after the fallback",
            "th-classic" in (body_cls or ""), f"{body_cls!r}")
    s.eq("8.90 the dropdown shows classic selected after the fallback",
         await p.locator("#f-theme").input_value(), "classic")

    # every remaining theme must still render
    bad_themes = []
    for key in ["classic", "zine", "swiss", "brutalist", "neomemphis"]:
        await p.evaluate("k => { bindTheme(k); renderPreviewNow(); }", key)
        await p.wait_for_timeout(300)
        cls = await p.frame_locator("#previewFrame").locator("body").get_attribute("class")
        txt = await p.frame_locator("#previewFrame").locator("body").inner_text()
        if f"th-{key}" not in cls or "Toastmasters" not in txt:
            bad_themes.append((key, cls))
    s.check("8.91 all five surviving themes render", not bad_themes, str(bad_themes))
    await p.evaluate("() => bindTheme('classic')")

    # ================= 6. the Balance Segments button =================
    bal = p.locator(".btn.balance")
    s.eq("8.92 there is one .btn.balance", await bal.count(), 1)
    s.eq("8.93 it reads 'Balance Segments'", (await bal.inner_text()).strip(), "Balance Segments")
    tip = await bal.get_attribute("data-tip") or ""
    s.check("8.94 it carries the tooltip on itself (data-tip)",
            "FLEXIBLE" in tip, f"{tip[:80]!r}")
    s.check("8.95 the tooltip CSS covers .btn.balance",
            await p.evaluate(
                "() => [...document.styleSheets].some(ss => { try { return [...ss.cssRules]"
                ".some(r => (r.selectorText||'').includes('.btn.balance[data-tip]')); }"
                " catch(e){ return false; } })"))
    bw = await bal.evaluate("e => e.getBoundingClientRect().width")
    s.check("8.96 it wraps to two lines but stays narrow", bw <= 90, f"width={bw}")

    # it must actually balance. The two flexible segments (Break 10-18, Table
    # Topics 12-20) can absorb about +/-6 min around the 150, so 21:33 is inside
    # their range and 21:45 deliberately is not.
    await p.evaluate("() => { state.meeting.endTime = '21:33'; }")
    await bal.click()
    await p.wait_for_timeout(500)
    s.eq("8.97 pressing Balance Segments lands the meeting on the new end time",
         await p.evaluate("() => computeSchedule().endClock"), "9:33 PM")
    ban = await p.evaluate("() => document.getElementById('banner').textContent")
    s.check("8.97b and reports an exact balance", "exactly" in ban, f"{ban[:120]!r}")

    await p.evaluate("() => { state.meeting.endTime = '21:45'; }")
    await bal.click()
    await p.wait_for_timeout(500)
    ban = await p.evaluate("() => document.getElementById('banner').textContent")
    s.check("8.97c an out-of-range target reports 'flex ranges maxed out' rather than lying",
            "maxed out" in ban and "short of" in ban, f"{ban[:160]!r}")

    await p.evaluate("() => { state.meeting.endTime = '21:30'; balanceToEndTime(); }")
    await p.wait_for_timeout(400)
    s.eq("8.98 and back to 9:30 PM", await p.evaluate("() => computeSchedule().endClock"),
         "9:30 PM")

    # ---- toolbar must not overflow at any width ----
    for w, h in ((1400, 900), (1024, 800), (390, 844)):
        await p.set_viewport_size({"width": w, "height": h})
        await p.wait_for_timeout(350)
        # scrollWidth alone is not the test: the data-tip tooltips are absolutely
        # positioned opacity:0 pseudo-elements that inflate it without ever being
        # seen. What matters is whether the document actually scrolls sideways
        # and whether any real element sticks out.
        ov = await p.evaluate(
            """() => { const t = document.querySelector('.toolbar');
                 const de = document.documentElement;
                 const out = [...t.querySelectorAll('*')]
                   .filter(e => e.getBoundingClientRect().right > window.innerWidth + 1)
                   .map(e => (e.tagName + '.' + (e.className||'').toString()).slice(0,40));
                 return {hScroll: de.scrollWidth > de.clientWidth,
                         bodyOver: document.body.scrollWidth > window.innerWidth,
                         out, tH: Math.round(t.getBoundingClientRect().height)}; }""")
        s.check(f"8.99 [{w}px] no real toolbar element overflows the viewport",
                not ov["out"], str(ov["out"]))
        s.check(f"8.99b [{w}px] the toolbar wraps rather than stacking",
                ov["tH"] <= (130 if w >= 1024 else 190), f"height={ov['tH']}px")
        # Separate check: a horizontal scrollbar on the whole document. This is
        # NOT caused by the Balance button - see the note in the report.
        s.check(f"8.99c [{w}px] the document does not scroll horizontally",
                not ov["hScroll"], f"documentElement scrollWidth exceeds clientWidth: {ov}")
    await p.set_viewport_size({"width": 1400, "height": 900})
    await p.wait_for_timeout(300)

    # Attribute the remaining horizontal scroll. Removing one data-tip at a time
    # only shows a reduction for the element that is currently the WIDEST, so
    # this names the binding contributor.
    ATTRIB = """() => { const de = document.documentElement, base = de.scrollWidth;
             const hits = [];
             document.querySelectorAll('[data-tip]').forEach(e=>{
               const v = e.getAttribute('data-tip'); e.removeAttribute('data-tip');
               if(de.scrollWidth < base) hits.push([(e.id || e.className).toString().slice(0,40),
                                                    base - de.scrollWidth]);
               e.setAttribute('data-tip', v); });
             return {base, client: de.clientWidth, over: base - de.clientWidth, hits}; }"""
    attrib = await p.evaluate(ATTRIB)
    s.check("8.99d the Balance button is not what widens the document",
            not any("balance" in h[0].lower() for h in attrib["hits"]), str(attrib))
    s.check("8.99e the Reset button's tooltip no longer overflows (tip-right applied)",
            not any("ghost" in h[0] for h in attrib["hits"]),
            f"Reset still contributes: {attrib}")
    # V36 gave #dlBtn tip-right too, so there is no residual left to attribute.
    # These two checks used to ASSERT the defect ("the residual is the #dlBtn
    # tooltip", "the previous build measures the same"), which is a fine way to
    # pin a known-and-accepted bug and a trap once it is fixed: they failed on the
    # build that fixed them. Rewritten to assert the fix, with the previous build
    # kept as the before-picture rather than as the expectation.
    s.check("8.99f no tooltip overflows the viewport any more",
            attrib["hits"] == [], str(attrib))
    s.check("8.99g there is no horizontal scroll at all", attrib["over"] == 0, str(attrib))

    prev = await open_app(ctx, PREV, viewport={"width": 1400, "height": 900})
    await prev.page.wait_for_timeout(300)
    prev_attrib = await prev.page.evaluate(
        """() => { const de = document.documentElement;
             document.querySelectorAll('.toolbar .btn.ghost.icon')
               .forEach(e => e.classList.add('tip-right'));
             const base = de.scrollWidth;
             const b = document.getElementById('dlBtn'), v = b.getAttribute('data-tip');
             b.removeAttribute('data-tip'); const noDl = de.scrollWidth;
             b.setAttribute('data-tip', v);
             return {base, client: de.clientWidth, dl: base - noDl}; }""")
    await prev.page.close()
    s.check("8.99h the previous build still shows the 19px this one fixed",
            prev_attrib["base"] - prev_attrib["client"] == 19 and prev_attrib["dl"] == 19,
            f"now={attrib} prev={prev_attrib}")

    # ================= error sweep =================
    s.check("8.100 zero uncaught page errors across the V31 features",
            not app.clean_errors(), str(app.clean_errors()[:4]))
    s.check("8.101 zero console errors across the V31 features",
            not app.clean_console(), str(app.clean_console()[:4]))


if __name__ == "__main__":
    asyncio.run(run_suite(main, "8_v31_features"))
