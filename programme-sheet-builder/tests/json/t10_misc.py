"""Remaining shapes: emptying the running order then saving, the auto-name
re-stamp making a second file, flushFileSave without permission."""
from harness import App, head, ok
import json

head("T10a — delete every row through the UI, then press Save")
with App() as a:
    a.attach_folder()
    a.js("()=>{ state.meeting.title='REAL MEETING'; state.roles.tmod='Rama'; }")
    a.save_direct("Real.nse.json")
    a.wait(400)
    before = a.dir_get("Real.nse.json")
    n = a.js("""()=>{ let guard=0;
        while(state.segments.length && guard++ < 500){ removeSeg(state.segments[0].id); }
        return state.segments.length; }""")
    print("  segments after clearing:", n)
    a.wait(1800)
    ok(a.dir_get("Real.nse.json") == before, "autosave refused the empty sheet (fix 2)")
    print("  badge:", a.badge())
    a.js("()=>saveMeetingDirect()")     # user presses Save
    a.wait(600)
    after = json.loads(a.dir_get("Real.nse.json"))
    print("  segments on disk after pressing Save:", len(after["state"]["segments"]))
    print("  banner-less?  badge:", a.badge())
    ok(len(after["state"]["segments"]) > 0,
       "manual Save also refuses to blank the meeting on disk")

head("T10b — the auto name is re-stamped with the clock, so Save after a reload forks the file")
with App() as a:
    a.attach_folder()
    a.install_idb_stub()
    a.js("""()=>{ const R=Date; let t = new R('2026-08-13T18:47:00');
        window.__setNow = ms => { t = new R(ms); };
        window.Date = function(...a){ return a.length ? new R(...a) : new R(t); };
        window.Date.now = ()=> t.getTime();
        window.Date.prototype = R.prototype; }""")
    a.js("()=>{ state.meeting.dateDisplay='Thursday, 13 August 2026'; state.meeting.title='Evening Meeting'; saveState(); }")
    a.wait(600)
    a.js("()=>saveMeetingDirect()")
    a.wait(600)
    print("  saved as:", a.dir_list())
    keep = {n: a.dir_get(n) for n in a.dir_list()}
    a.reload_with_folder(keep)
    print("  after reload attached:", repr(a.open_file_name()))
    a.js("""()=>{ const R=Date; let t = new R('2026-08-14T09:15:00');
        window.Date = function(...a){ return a.length ? new R(...a) : new R(t); };
        window.Date.now = ()=> t.getTime(); window.Date.prototype = R.prototype; }""")
    a.js("()=>{ state.meeting.title='Evening Meeting - corrected'; saveState(); }")
    a.wait(600)
    a.js("()=>saveMeetingDirect()")
    a.wait(700)
    print("  folder after the next-day Save:", a.dir_list())
    for n in a.dir_list():
        print("     %-44s title=%r" % (n, json.loads(a.dir_get(n))["state"]["meeting"]["title"]))
    ok(len(a.dir_list()) == 1, "one meeting stays one file across a reload")

head("T10c — flushFileSave ignores permission and the size check")
with App() as a:
    a.attach_folder()
    a.js("()=>{ state.meeting.title='F0'; }")
    a.save_direct("F.nse.json")
    a.wait(400)
    a.js("()=>{ window.__DIR.__st.perm='denied'; window.__FSLOG=[]; }")
    a.js("()=>{ state.meeting.title='F1'; saveState(); }")
    a.wait(150)
    a.js("()=>flushFileSave()")
    a.wait(500)
    print("  fslog:", [(e['ev'], e['marker']) for e in a.fslog()])
    print("  disk :", json.loads(a.dir_get("F.nse.json"))["state"]["meeting"]["title"])
    print("  badge:", a.badge())
    print("  NOTE: flushFileSave() writes without checking handleUsable() and")
    print("        swallows every error (.catch(()=>{})), so a failed final flush")
    print("        is invisible.")

head("T10d — flushFileSave drops the pending edit when the sheet is empty")
with App() as a:
    a.attach_folder()
    a.js("()=>{ state.meeting.title='G0'; }")
    a.save_direct("G.nse.json")
    a.wait(400)
    a.js("()=>{ state.meeting.title='G1'; saveState(); }")
    a.wait(150)
    a.js("()=>{ const keep = state.segments.slice(); state.segments=[];"
         "        flushFileSave(); state.segments = keep; }")
    a.wait(2000)
    print("  disk:", json.loads(a.dir_get("G.nse.json"))["state"]["meeting"]["title"])
    print("  (the queued timer was cleared by flushFileSave before the guard bailed out)")

head("T10e — a corrupt/half-written file in the folder")
with App() as a:
    a.attach_folder()
    a.js("()=>{ state.meeting.title='SAFE'; }")
    a.save_direct("Safe.nse.json")
    a.wait(400)
    a.js("""()=>{ window.__BANNERS=[]; const o=showBanner;
        showBanner=function(m,w){ window.__BANNERS.push([m,!!w]); return o(m,w); }; }""")
    good = a.dir_get("Safe.nse.json")
    a.dir_set("Half.nse.json", good[: len(good) // 2])
    a.js("()=>pickMeetingFile('f:Half.nse.json')")
    a.wait(600)
    print("  banners:", a.js("()=>window.__BANNERS"))
    print("  still attached to:", a.open_file_name(), "title:", a.js("()=>state.meeting.title"))
    ok(a.js("()=>state.meeting.title") == "SAFE", "a truncated file does not disturb the open meeting")
    ok(a.open_file_name() == "Safe.nse.json", "the good file stays attached")
