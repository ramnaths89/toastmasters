"""adoptState(): does merging over defaultState() actually happen for
meeting / roles / roleActive?  (05_app.js:297-301)"""
from harness import App, head, ok
import json, pathlib

HERE = pathlib.Path(__file__).resolve().parent
FIX = HERE / "fixtures"

head("T07a — a file whose meeting/roles/roleActive omit fields added later")
with App() as a:
    payload = {
        "app": "nse-programme-sheet", "v": 28,
        "state": {
            "meeting": {"title": "Old Meeting", "dateDisplay": "13 August 2026"},
            "roles": {"tmod": "Rama"},
            "roleActive": {"tmod": True},
            "segments": [{"id": "s1", "presetKey": "speech", "durMin": 7}],
        },
    }
    a.js("(t)=>applyMeetingText(t,'old.json')", json.dumps(payload))
    probe = a.js("""()=>({
        clubName: state.meeting.clubName,
        clubNumber: state.meeting.clubNumber,
        clubInitials: state.meeting.clubInitials,
        orgLine: state.meeting.orgLine,
        cadence: state.meeting.cadence,
        location: state.meeting.location,
        startTime: state.meeting.startTime,
        endTime: state.meeting.endTime,
        footerNote: state.meeting.footerNote,
        roles: state.roles,
        roleActive: state.roleActive,
        roleActiveTimer: state.roleActive.timer,
        rolesKeys: Object.keys(state.roles),
        execTextLen: (state.execText||'').length,
    })""")
    for k, v in probe.items():
        print("   %-16s %r" % (k, v))
    ok(probe["clubName"] == "Nee Soon East Toastmasters Club", "meeting.clubName took its default")
    ok(probe["cadence"] not in (None, ""), "meeting.cadence took its default")
    ok(probe["orgLine"] not in (None, ""), "meeting.orgLine took its default")
    ok(probe["startTime"] == "19:00", "meeting.startTime took its default")
    ok(len(probe["rolesKeys"]) > 1, "roles keeps the full role set")
    ok(probe["roleActiveTimer"] is True, "roleActive.timer defaults to on")

head("T07b — what the sheet then renders / what the next save writes back")
with App() as a:
    payload = {
        "app": "nse-programme-sheet", "v": 28,
        "state": {"meeting": {"title": "Old Meeting"}, "roles": {"tmod": "Rama"},
                  "roleActive": {"tmod": True},
                  "segments": [{"id": "s1", "presetKey": "speech"}]},
    }
    a.js("(t)=>applyMeetingText(t,'old.json')", json.dumps(payload))
    a.attach_folder()
    a.save_direct("resaved.nse.json")
    a.wait(400)
    out = json.loads(a.dir_get("resaved.nse.json"))
    print("   meeting written back:", json.dumps(out["state"]["meeting"], indent=2)[:400])
    print("   roleActive written back:", out["state"]["roleActive"])
    print("   roles written back:", out["state"]["roles"])
    html = a.js("()=>{ const el=document.getElementById('sheetWrap')||document.body; return el.innerText.slice(0,400); }")
    print("   sheet text starts:", repr(html[:300]))
    ok("undefined" not in html, "the rendered sheet contains no 'undefined'")

head("T07c — the real pre-V30 fixture")
with App() as a:
    text = (FIX / "v29.nse.json").read_text()
    a.js("(t)=>applyMeetingText(t,'v29')", text)
    probe = a.js("""()=>({clubInitials: state.meeting.clubInitials,
        orgLine: state.meeting.orgLine, cadence: state.meeting.cadence,
        fileName: state.meeting.fileName,
        suggested: suggestedFileStem(), base: fileBaseName()})""")
    for k, v in probe.items():
        print("   %-14s %r" % (k, v))
    ok(probe["cadence"] not in (None, ""), "v29 file gets the default cadence line")
    ok(probe["orgLine"] not in (None, ""), "v29 file gets the default org line")
