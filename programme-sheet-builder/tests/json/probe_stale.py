from harness import App, head
import json
head("probe: same-length stale commit")
with App() as a:
    a.attach_folder()
    a.js("()=>{ state.meeting.title='V1'; }")
    a.save_direct("E.nse.json")
    a.wait(500)
    keep = a.dir_get("E.nse.json")
    a.js("()=>{ const keep=window.__DIR.__get('E.nse.json'); window.__DIR.__st.afterClose=(n,t)=>keep;"
         " window.__probe=[]; const w=writeHandle;"
         " window.writeHandle = async function(h,t){ try{ const r= await w(h,t); window.__probe.push(['ok',t.length]); return r; }"
         " catch(e){ window.__probe.push(['throw', e.message]); throw e; } }; }")
    a.js("()=>{ state.meeting.title='V2'; saveState(); }")
    a.wait(1800)
    print("  probe:", a.js("()=>window.__probe"))
    print("  lens: keep=%d" % len(keep))
    print("  new payload len:", a.js("()=>meetingPayload().length"))
    print("  badge:", a.badge())
    print("  disk title:", json.loads(a.dir_get("E.nse.json"))["state"]["meeting"]["title"])
