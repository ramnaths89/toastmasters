from harness import App, head, ok
import json
head("T15d2 — reconciliation with BOTH stamps safely in the past (the real case)")
# The file was saved yesterday evening; the browser copy is from two days ago.
# The file is unambiguously newer, so reattachFile should load it.
with App() as a:
    a.attach_folder(); a.install_idb_stub()
    a.js("()=>{ state.meeting.title='THURSDAY AGENDA'; state.roles.tmod='Rama'; saveState(); }")
    a.wait(500); a.save_direct("Thu.nse.json"); a.wait(500)
    p = json.loads(a.dir_get("Thu.nse.json"))
    p["savedAt"] = "2026-08-09T21:00:00.000Z"          # file: yesterday 21:00
    files = {"Thu.nse.json": json.dumps(p, indent=2)}
    a.js("""()=>{ const raw=JSON.parse(localStorage.getItem('nse-programme-builder-v6'));
        raw.savedAt='2026-08-08T10:00:00.000Z';         /* browser: two days ago */
        raw.state.meeting.title='STALE BROWSER COPY'; raw.state.roles.tmod='';
        localStorage.setItem('nse-programme-builder-v6', JSON.stringify(raw)); }""")
    a.reload_with_folder(files)
    print("  shown after reattach:", repr(a.js("()=>state.meeting.title")))
    print("  localStorage savedAt now:",
          a.js("()=>JSON.parse(localStorage.getItem('nse-programme-builder-v6')).savedAt"))
    a.js("()=>{ state.meeting.footerNote='one keystroke'; saveState(); }")
    a.wait(2000)
    d = json.loads(a.dir_get("Thu.nse.json"))["state"]
    print("  file after one keystroke: title=%r tmod=%r" % (d["meeting"]["title"], d["roles"]["tmod"]))
    print("  badge:", a.badge())
    ok(d["meeting"]["title"] == "THURSDAY AGENDA",
       "yesterday's saved meeting is NOT replaced by a two-day-old browser copy")
