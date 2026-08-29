from harness import App, head, ok
import json

def title_on_disk(a, name):
    t = a.dir_get(name)
    if not t: return None
    try: return json.loads(t)["state"]["meeting"]["title"]
    except Exception: return "<<CORRUPT %d bytes>>" % len(t)

HOOK = """()=>{ window.__BANNERS=[]; const o=showBanner;
  showBanner=function(m,w){ window.__BANNERS.push([m,!!w]); return o(m,w); }; }"""

head("T16c2 — Cancel branch, with the banner hook installed AFTER the reload")
with App(dialogs="dismiss") as a:
    a.attach_folder(); a.install_idb_stub()
    a.js("()=>{ state.meeting.title='MEETING ON DISK'; saveState(); }")
    a.wait(500); a.save_direct("C.nse.json"); a.wait(500)
    p = json.loads(a.dir_get("C.nse.json")); p["savedAt"]="2026-08-09T21:00:00.000Z"
    a.js("""()=>{ const raw=JSON.parse(localStorage.getItem('nse-programme-builder-v6'));
        raw.savedAt='2026-08-10T23:59:00.000Z'; raw.state.meeting.title='BROWSER VERSION';
        localStorage.setItem('nse-programme-builder-v6', JSON.stringify(raw)); }""")
    a.page.reload(wait_until="domcontentloaded", timeout=90000); a.wait(700)
    a.attach_folder(); a.dir_set("C.nse.json", json.dumps(p, indent=2)); a.install_idb_stub()
    a.js(HOOK)
    a.js("()=>ensureFolder(false).then(reattachFile).then(refreshFileList)")
    a.wait(900)
    print("  banners:", a.js("()=>window.__BANNERS"))
    print("  badge  :", a.badge())
    ok(any("replaced" in m for m,w in (a.js("()=>window.__BANNERS") or [])),
       "Cancel banners that the file will be replaced")

head("T16d2 — resyncBaseline read failure, restoring cleanly afterwards")
with App() as a:
    a.attach_folder(); a.install_idb_stub()
    a.js("()=>{ state.meeting.title='R0'; saveState(); }")
    a.wait(500); a.save_direct("Rz.nse.json"); a.wait(500)
    a.js("""()=>{ window.__realGetFile = fileHandle.getFile;
        window.__DIR.__st.faults.write={name:'X',message:'write blew up'};
        fileHandle.getFile = async function(){ throw new Error('read blew up too'); }; }""")
    a.js("()=>{ state.meeting.title='R1'; saveState(); }")
    a.wait(2100)
    print("  baselines:", a.js("()=>Object.keys(baseline)"))
    print("  badge    :", a.badge()["title"][:70])
    print("  pageerrors:", a.pageerrors)
    a.js("""()=>{ window.__DIR.__st.faults.write=null;
        fileHandle.getFile = window.__realGetFile; }""")
    a.js("()=>{ state.meeting.title='R2'; saveState(); }")
    a.wait(2300)
    print("  disk:", title_on_disk(a, "Rz.nse.json"), " badge:", a.badge())
    ok(title_on_disk(a, "Rz.nse.json") == "R2", "writing resumes once the disk is healthy")
