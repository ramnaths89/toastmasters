"""V30 feature 1 - 2025 Pathways Education Series projects."""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import V29, expand_speech, open_app, open_sections, run_suite  # noqa: E402

# From the Club Officer Guide to the 2025 Pathways Enhancements, as encoded in
# src/05_app.js EDU_SERIES. The test states them independently so a typo in the
# app is a failure rather than a shared assumption.
EXPECTED = {
    "3": {
        "Successful Club Series": [
            "Creating the Best Club Climate",
            "Meeting Roles and Responsibilities",
            "Keeping the Commitment",
            "Going Beyond Our Club",
        ],
    },
    "4": {
        "Successful Club Series": [
            "Finding New Members",
            "Closing the Sale",
            "How to Be a Distinguished Club",
            "Toastmasters Educational Program",
        ],
        "Better Speaker Series": [
            "Beginning Your Speech",
            "Concluding Your Speech",
            "Controlling Your Fear",
            "Impromptu Speaking",
            "Selecting Your Topic",
            "Know Your Audience",
            "Organizing Your Speech",
            "Creating an Introduction",
            "Preparation and Practice",
            "Using Body Language",
        ],
    },
    "5": {
        "Successful Club Series": [
            "Moments of Truth",
            "Evaluate to Motivate",
            "Mentoring",
        ],
        "Leadership Excellence Series": [
            "Service and Leadership",
            "The Leader as a Coach",
            "Developing a Mission",
            "Motivating People",
            "Building a Team",
            "Delegate to Empower",
            "Resolving Conflict",
            "Visionary Leader",
            "Values and Leadership",
            "Goal Setting and Planning",
            "Giving Effective Feedback",
        ],
    },
}
COUNTS = {"3": 4, "4": 14, "5": 14}


async def main(ctx, s):
    # ---------- V29 baseline: the project catalogue before the enhancement ----------
    v29 = await open_app(ctx, V29)
    v29_projects = await v29.page.evaluate(
        "() => JSON.parse(JSON.stringify(PATHWAYS_DATA.projects))"
    )
    v29_pathabbrs = await v29.page.evaluate("() => PATHWAYS_DATA.paths.map(p=>p.abbr)")
    # Every project name a path actually offers at some level. Only these are
    # protected from being replaced by an Education Series title; an entry in the
    # catalogue that no level references is an orphan.
    v29_referenced = set(await v29.page.evaluate(
        "() => { const s=new Set(); Object.values(PATHWAYS_DATA.levels).forEach(lv =>"
        " Object.values(lv).forEach(list => list.forEach(p => s.add(p.n)))); return [...s]; }"
    ))
    v29_levels = await v29.page.evaluate(
        "() => { const o={}; PATHWAYS_DATA.paths.forEach(p=>{o[p.abbr]={};"
        "['1','2','3','4','5'].forEach(l=>{o[p.abbr][l]=projectsFor(p.abbr,l).map(x=>x.n);});});"
        " return o; }"
    )
    await v29.page.close()

    app = await open_app(ctx)
    p = app.page

    projects = await p.evaluate("() => JSON.parse(JSON.stringify(PATHWAYS_DATA.projects))")
    abbrs = await p.evaluate("() => PATHWAYS_DATA.paths.map(x=>x.abbr)")

    s.eq("1.1 eleven path abbreviations", len(abbrs), 11, f"abbrs={abbrs}")

    # ---------- 1.2 every Education Series title registered with {min:10,max:15,series} -
    missing, wrong = [], []
    for lvl, groups in EXPECTED.items():
        for series, titles in groups.items():
            for t in titles:
                e = projects.get(t)
                if e is None:
                    missing.append((lvl, t))
                elif not (e.get("min") == 10 and e.get("max") == 15 and e.get("series") == series):
                    wrong.append((t, e, series))
    s.check(
        "1.2 all series titles in PATHWAYS_DATA.projects as {min:10,max:15,series}",
        not missing and not wrong,
        f"missing={missing[:5]} wrong={wrong[:5]}",
    )

    # ---------- 1.3 per-level offering counts ----------
    for lvl, want in COUNTS.items():
        got = await p.evaluate("l => eduFor(l).length", lvl)
        s.eq(f"1.3 level {lvl} offers {want} series titles", got, want)

    # Series breakdown per level.
    for lvl, groups in EXPECTED.items():
        got = await p.evaluate(
            "l => { const c={}; eduFor(l).forEach(x=>{c[x.s]=(c[x.s]||0)+1;}); return c; }", lvl
        )
        want = {k: len(v) for k, v in groups.items()}
        s.eq(f"1.4 level {lvl} series breakdown", got, want)

    # ---------- 1.5 projectsFor: own projects FIRST, then series, all 11 paths ----------
    bad_order, bad_missing = [], []
    for abbr in abbrs:
        for lvl in ("3", "4", "5"):
            got = await p.evaluate(
                "([a,l]) => projectsFor(a,l).map(x=>({n:x.n, s:x.s||''}))", [abbr, lvl]
            )
            own_len = await p.evaluate(
                "([a,l]) => ((PATHWAYS_DATA.levels[a]||{})[l]||[]).length", [abbr, lvl]
            )
            head = got[:own_len]
            tail = got[own_len:]
            if any(x["s"] for x in head):
                bad_order.append((abbr, lvl, "series title inside the path block"))
            if not all(x["s"] for x in tail):
                bad_order.append((abbr, lvl, "path project after the series block"))
            want_tail = [t for g in EXPECTED[lvl].values() for t in g]
            if sorted(x["n"] for x in tail) != sorted(want_tail):
                bad_missing.append((abbr, lvl, len(tail)))
    s.check("1.5 projectsFor puts path projects before series, 11 paths x L3-5",
            not bad_order, f"{bad_order[:4]}")
    s.check("1.6 projectsFor appends the full series list for every path/level",
            not bad_missing, f"{bad_missing[:4]}")

    # ---------- 1.7 levels 1 and 2 unchanged vs V29 ----------
    diffs = []
    for abbr in abbrs:
        for lvl in ("1", "2"):
            got = await p.evaluate("([a,l]) => projectsFor(a,l).map(x=>x.n)", [abbr, lvl])
            was = (v29_levels.get(abbr) or {}).get(lvl)
            if was is not None and got != was:
                diffs.append((abbr, lvl, was, got))
    s.check("1.7 levels 1 & 2 identical to V29 for all paths", not diffs, f"{diffs[:3]}")

    # ---------- 1.8 no REFERENCED V29 project overwritten ----------
    # The guard now protects only projects a path actually offers. That is the
    # invariant that matters: a member's real project must never be retimed.
    clobbered, orphan_changed = [], []
    for name, meta in v29_projects.items():
        now = projects.get(name)
        referenced = name in v29_referenced
        if now is None:
            (clobbered if referenced else orphan_changed).append((name, "MISSING in V30"))
        elif now.get("min") != meta.get("min") or now.get("max") != meta.get("max") \
                or now.get("series"):
            (clobbered if referenced else orphan_changed).append(
                (name, f"V29={meta} V30={now}"))
    s.check(
        f"1.8 all {len(v29_referenced & set(v29_projects))} V29 projects referenced by a path "
        "level keep their exact min/max and stay untagged",
        not clobbered, f"{clobbered[:5]}",
    )
    # Exactly one unreferenced orphan may change, and only into its series entry.
    s.check(
        "1.8b only the orphan 'Mentoring' was replaced, and only by its series entry",
        [n for n, _ in orphan_changed] == ["Mentoring"]
        and projects.get("Mentoring") == {"min": 10, "max": 15,
                                          "series": "Successful Club Series"},
        f"orphans changed={orphan_changed}, Mentoring={projects.get('Mentoring')}",
    )
    s.check(
        "1.8c every V29 project name still exists in the V30 catalogue",
        all(n in projects for n in v29_projects), "",
    )
    # Genuine collisions must be recorded, not swallowed.
    skipped = await p.evaluate("() => EDU_SKIPPED")
    s.eq("1.8d EDU_SKIPPED is empty (no genuine collision remains)", skipped, [])

    # A series title that collided with a real project would be silently dropped
    # from EDU_BY_LEVEL rather than reported. Check nothing was dropped.
    dropped = []
    for lvl, groups in EXPECTED.items():
        listed = await p.evaluate("l => eduFor(l).map(x=>x.n)", lvl)
        for series, titles in groups.items():
            for t in titles:
                if t not in listed:
                    dropped.append((lvl, t))
    s.check("1.9 no series title silently dropped by the collision guard",
            not dropped, f"{dropped[:5]}")

    # ---------- 1.10 seriesOf ----------
    s.eq("1.10 seriesOf on a series title", await p.evaluate("seriesOf('Moments of Truth')"),
         "Successful Club Series")
    s.eq("1.11 seriesOf on an ordinary project", await p.evaluate("seriesOf('Ice Breaker')"), "")
    s.eq("1.12 seriesOf on an unknown title", await p.evaluate("seriesOf('Not A Project')"), "")

    # ---------- 1.13 timingLabel ----------
    s.eq("1.13 timingLabel for a series title", await p.evaluate("timingLabel('Mentoring')"),
         "10–15 min")

    # ---------- 1.14 ALL_PROJECTS is the V29 catalogue unioned with the series ----------
    # 'Mentoring' is a replacement, not an addition, so the union - not the sum.
    all_titles = {t for g in EXPECTED.values() for ts in g.values() for t in ts}
    all_n = await p.evaluate("ALL_PROJECTS.length")
    want_n = len(set(v29_projects) | all_titles)
    s.eq("1.14 ALL_PROJECTS = V29 catalogue union the series titles",
         all_n, want_n,
         f"V29={len(v29_projects)} series={len(all_titles)} overlap="
         f"{sorted(set(v29_projects) & all_titles)} V30={all_n}")
    s.check("1.14b ALL_PROJECTS is sorted and has no duplicates",
            await p.evaluate(
                "() => ALL_PROJECTS.length === new Set(ALL_PROJECTS).size"
                " && ALL_PROJECTS.every((n,i)=>i===0 || ALL_PROJECTS[i-1] <= n)"))

    # ================= UI =================
    # Pick speech 1, set pathway + Level 5, open the combobox.
    seg_id = await p.evaluate("() => state.segments.find(s=>s.isSpeech).id")
    await p.evaluate(
        "id => { catalogEdit(id,'pathway','DL'); catalogEdit(id,'pLevel','5'); }", seg_id
    )
    await p.wait_for_timeout(300)
    # V31: sections load shut and speech cards load collapsed.
    await open_sections(p)
    await expand_speech(p, seg_id)

    card = p.locator(f"#speechList .cbx[data-cbx='{seg_id}']").first
    s.check("1.15 speech card has a project combobox", await card.count() > 0)

    inp = card.locator(".cbx-input")
    ph = await inp.get_attribute("placeholder")
    s.check(
        f"1.16 combobox placeholder counts all {all_n} projects",
        ph == f"Click ▾ or type to search all {all_n} projects…",
        f"placeholder={ph!r}",
    )

    await card.locator(".cbx-btn").click()
    await p.wait_for_timeout(200)
    s.check("1.17 clicking ▾ opens the list", "open" in (await card.get_attribute("class") or ""))

    # Visible options, in order, with their meta.
    opts = await card.evaluate(
        """el => [...el.querySelectorAll('.cbx-opt')]
             .filter(o => !o.classList.contains('hide'))
             .map(o => ({n:o.querySelector('.cbx-n').textContent,
                         m:o.querySelector('.cbx-m').textContent,
                         here:o.classList.contains('here')}))"""
    )
    here = [o for o in opts if o["here"]]
    l5_titles = [t for g in EXPECTED["5"].values() for t in g]
    present = [t for t in l5_titles if any(o["n"] == t and o["here"] for o in here)]
    s.eq("1.18 all 14 L5 series titles appear in the in-level block", len(present), 14,
         f"missing={[t for t in l5_titles if t not in present][:4]}")

    labelled = [
        o for o in here
        if o["n"] in l5_titles
        and o["m"].split(" · ")[0] in ("Successful Club Series", "Leadership Excellence Series")
    ]
    s.eq("1.19 series options are labelled with their series name (not required/elective)",
         len(labelled), 14,
         f"sample={[o['m'] for o in here if o['n'] in l5_titles][:3]}")

    s.check(
        "1.20 series options show the 10-15 min timing",
        all(o["m"].endswith("10–15 min") for o in here if o["n"] in l5_titles),
        f"{[o['m'] for o in here if o['n'] in l5_titles][:3]}",
    )

    # Ordering inside the in-level block: path projects first.
    own = await p.evaluate("() => (PATHWAYS_DATA.levels['DL']['5']||[]).map(x=>x.n)")
    head_names = [o["n"] for o in here][: len(own)]
    s.eq("1.21 in-level block lists the path's own L5 projects before the series",
         head_names, own)

    # ---------- 1.22 search still narrows ----------
    await inp.fill("keeping the commitment")
    await p.wait_for_timeout(200)
    vis = await card.evaluate(
        "el => [...el.querySelectorAll('.cbx-opt')].filter(o=>!o.classList.contains('hide'))"
        ".map(o=>o.querySelector('.cbx-n').textContent)"
    )
    s.check("1.22 typing narrows the list to one series title",
            vis == ["Keeping the Commitment"], f"{vis}")

    # Symptom check for the collision guard: the Education Series 'Mentoring'
    # is dropped because an orphan 5-7 min catalogue project owns the name, so
    # picking it at L5 gives a member the WRONG timing lights.
    await inp.fill("Mentoring")
    await p.wait_for_timeout(200)
    exact = card.locator(".cbx-opt:not(.hide)").filter(has_text="Mentoring")
    metas = await card.evaluate(
        "el => [...el.querySelectorAll('.cbx-opt')].filter(o=>!o.classList.contains('hide'))"
        ".map(o=>[o.querySelector('.cbx-n').textContent, o.querySelector('.cbx-m').textContent])"
    )
    ment = [m for m in metas if m[0] == "Mentoring"]
    s.check("1.22b 'Mentoring' is offered as a 10-15 min Successful Club Series title",
            bool(ment) and "Successful Club Series" in ment[0][1] and "10–15" in ment[0][1],
            f"offered as {ment!r}")
    await p.evaluate("id => applyProjectChoice(state.segments.find(s=>s.id===id), 'Mentoring')",
                     seg_id)
    mlights = await p.evaluate(
        "id => { const s=state.segments.find(x=>x.id===id);"
        " return [s.signalMin, s.signalMid, s.signalMax]; }", seg_id)
    s.eq("1.22c picking 'Mentoring' sets 10 / 12.5 / 15", mlights, [10, 12.5, 15])
    await p.evaluate(
        "id => applyProjectChoice(state.segments.find(s=>s.id===id), 'Moments of Truth')", seg_id)
    await inp.fill("")

    # search on the series name itself
    await inp.fill("leadership excellence")
    await p.wait_for_timeout(200)
    vis2 = await card.evaluate(
        "el => [...el.querySelectorAll('.cbx-opt')].filter(o=>!o.classList.contains('hide')).length"
    )
    s.eq("1.23 searching the series name matches its 11 titles", vis2, 11)

    # ---------- 1.24 choosing one sets the timing lights ----------
    await inp.fill("Moments of Truth")
    await p.wait_for_timeout(150)
    await card.locator(".cbx-opt:not(.hide)").first.click()
    await p.wait_for_timeout(400)

    seg = await p.evaluate(
        "id => { const s = state.segments.find(x=>x.id===id);"
        " return {project:s.project, min:s.signalMin, mid:s.signalMid, max:s.signalMax,"
        " dur:s.durMin, lvl:s.pLevel}; }",
        seg_id,
    )
    s.eq("1.24 picking a series title sets seg.project", seg["project"], "Moments of Truth")
    s.eq("1.25 green light = 10", seg["min"], 10)
    s.eq("1.26 amber light = 12.5", seg["mid"], 12.5)
    s.eq("1.27 red light = 15", seg["max"], 15)
    s.eq("1.28 pLevel stays 5 after picking a series title", str(seg["lvl"]), "5")
    s.check("1.29 duration slot follows the 15 min red light", seg["dur"] >= 15,
            f"durMin={seg['dur']}")

    # ---------- 1.30 printed sheet shows the project + lights ----------
    await p.evaluate("() => renderPreviewNow()")
    await p.wait_for_timeout(500)
    fr = p.frame_locator("#previewFrame")
    body = await fr.locator("body").inner_text()
    s.check("1.30 preview iframe names the chosen series project",
            "Moments of Truth" in body, body[:200])
    s.check("1.31 preview shows the 10-15 min timing for it",
            "10–15 min" in body or "10-15 min" in body,
            "no 10-15 min range in the sheet")

    clean_html = await p.evaluate("() => buildSheetHTML(false)")
    s.check("1.32 clean export HTML contains the series project",
            "Moments of Truth" in clean_html)

    # ---------- 1.33 no errors ----------
    s.check("1.33 zero uncaught page errors during feature 1", not app.clean_errors(),
            str(app.clean_errors()[:3]))
    s.check("1.34 zero console errors during feature 1", not app.clean_console(),
            str(app.clean_console()[:3]))


if __name__ == "__main__":
    asyncio.run(run_suite(main, "1_education_series"))
