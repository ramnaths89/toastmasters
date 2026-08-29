from harness import App, head, ok
import json
head("probe — the manual-Save override confirm after a truncated write")
with App() as a:
    a.attach_folder(); a.install_idb_stub()
    a.js("()=>{ state.meeting.title='REAL'; }")
    a.save_direct("T.nse.json"); a.wait(500)
    print("  lastWritten len after good save:", a.js("()=>lastWritten.length"))
    a.js("()=>{ window.__DIR.__st.afterClose=(n,t)=>t.slice(0,100); }")
    a.js("()=>{ state.meeting.title='v2'; saveState(); }"); a.wait(1800)
    print("  lastWritten len after short write:", a.js("()=>lastWritten.length"),
          " disk len:", len(a.dir_get("T.nse.json")))
    a.js("()=>{ window.__DIR.__st.afterClose=null; }")
    a.js("()=>{ state.meeting.title='v3'; saveState(); }"); a.wait(1800)
    print("  lastWritten len after refused autosave:", a.js("()=>lastWritten.length"))
    print("  badge:", a.badge()["title"][:80])
    a.js("()=>{ state.meeting.title='rescue'; saveMeetingDirect(); }"); a.wait(1200)
    print("  dialogs:", a.dialog_log)
    print("  disk:", (a.dir_get("T.nse.json") or "")[:40])
    ok(a.dialog_log, "the override confirm fires when the file really does differ")
