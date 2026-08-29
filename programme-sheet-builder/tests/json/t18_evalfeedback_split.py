"""V38: Evaluation and Feedback split into (1st Speech) and (2nd Speech).

The project is two 5-7 min speeches - the second incorporates the evaluator's
feedback on the first - so the sheet has to be able to say which one tonight is.
The un-suffixed name is kept in PATHWAYS_DATA.projects as `legacy` so a meeting
saved before this build still resolves its duration and note, and is filtered out
of the picker so it cannot read as a third option.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import App, head, ok

OLD = "Evaluation and Feedback"
P1, P2 = OLD + " (1st Speech)", OLD + " (2nd Speech)"
PATHS = ["DL", "EH", "MS", "PI", "PM", "VC", "EC", "IP", "LD", "SR", "TC"]

res = []
with App(build=os.environ.get("PSB_BUILD")) as app:
    head("catalog")
    res.append(ok(app.js("(n)=>!!PATHWAYS_DATA.projects[n]", P1), f"{P1} exists"))
    res.append(ok(app.js("(n)=>!!PATHWAYS_DATA.projects[n]", P2), f"{P2} exists"))
    res.append(ok(app.js("(n)=>!!PATHWAYS_DATA.projects[n]", OLD),
                  f"{OLD} still resolvable (saved meetings)"))
    res.append(ok(app.js("(n)=>!!PATHWAYS_DATA.projects[n].legacy", OLD), f"{OLD} flagged legacy"))
    for n in (P1, P2):
        t = app.js("(n)=>[PATHWAYS_DATA.projects[n].min, PATHWAYS_DATA.projects[n].max]", n)
        res.append(ok(t == [5, 7], f"{n} is 5-7 min  | {t}"))
        res.append(ok(bool(app.js("(n)=>PATHWAYS_DATA.projects[n].note", n)), f"{n} has a note"))

    head("every path's Level 1 offers both, and not the old name")
    for abbr in PATHS:
        names = app.js("(a)=>projectsFor(a,'1').map(p=>p.n)", abbr)
        res.append(ok(P1 in names and P2 in names and OLD not in names,
                      f"{abbr} L1  | {[n for n in names if 'Evaluation' in n]}"))
        req = app.js("(a)=>projectsFor(a,'1').filter(p=>p.n.startsWith('Evaluation')).map(p=>p.e)", abbr)
        res.append(ok(req == [False, False], f"{abbr} L1 both required, not elective  | {req}"))

    head("the picker")
    choices = app.js("""()=>{const seg=state.segments.find(s=>s.isSpeech);
        seg.pathway='PM'; seg.pLevel='1'; return projectChoices(seg).map(c=>c.n);}""")
    res.append(ok(choices.count(P1) == 1 and choices.count(P2) == 1, "both offered exactly once"))
    res.append(ok(OLD not in choices, "un-suffixed name never offered"))
    top = choices[:len(app.js("()=>projectsFor('PM','1').length") * [0]) or 6]
    res.append(ok(P1 in top and P2 in top, f"both sit in the in-level head of the list"))
    cnt = app.js("()=>PICKABLE_PROJECT_COUNT")
    allp = app.js("()=>ALL_PROJECTS.length")
    res.append(ok(cnt == allp - 1, f"placeholder count excludes the legacy name | {cnt} of {allp}"))

    head("a meeting saved before the split still works")
    info = app.js("(n)=>{const i=projectInfo(n); return i && [i.min,i.max];}", OLD)
    res.append(ok(info == [5, 7], f"projectInfo('{OLD}') still resolves | {info}"))
    lbl = app.js("(n)=>timingLabel(n)", OLD)
    res.append(ok("5" in lbl and "7" in lbl, f"timingLabel still renders | {lbl!r}"))

    head("the sheet renders both without error")
    out = app.js("""(ns)=>{ const segs=state.segments.filter(s=>s.isSpeech);
        segs[0].pathway='PM'; segs[0].pLevel='1'; segs[0].project=ns[0];
        if(segs[1]){ segs[1].pathway='PM'; segs[1].pLevel='1'; segs[1].project=ns[1]; }
        renderPreviewNow();
        const h=buildSheetHTML(false);
        return [h.includes(ns[0]), h.includes(ns[1])]; }""", [P1, P2])
    res.append(ok(out == [True, True], f"both names appear on the printed sheet | {out}"))
    res.append(ok(not app.pageerrors, f"no JS errors | {app.pageerrors[:1]}"))

print(f"\n{sum(res)}/{len(res)} passed")
sys.exit(0 if all(res) else 1)
