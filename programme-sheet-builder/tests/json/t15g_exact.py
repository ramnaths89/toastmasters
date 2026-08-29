from harness import App, head, ok
import json
head("probe — the exact comparison at realistic startup timing")
with App() as a:
    a.attach_folder(); a.install_idb_stub()
    a.js("()=>{ state.meeting.title='THURSDAY AGENDA'; saveState(); }")
    a.wait(600); a.save_direct("Thu.nse.json"); a.wait(600)
    p = json.loads(a.dir_get("Thu.nse.json")); p["savedAt"] = "2026-08-09T21:00:00.000Z"
    body = json.dumps(p, indent=2)
    a.js("""()=>{ const raw=JSON.parse(localStorage.getItem('nse-programme-builder-v6'));
        raw.savedAt='2026-08-08T10:00:00.000Z'; raw.state.meeting.title='STALE BROWSER COPY';
        localStorage.setItem('nse-programme-builder-v6', JSON.stringify(raw)); }""")
    a.page.reload(wait_until="domcontentloaded", timeout=90000)
    r = a.js("""(t)=>{ window.__DIR = window.__mkFakeDir({}); folderHandle = window.__DIR;
        window.__DIR.__set('Thu.nse.json', t);
        window.idbSet = async ()=>true;
        window.idbGet = async (k)=> k==='folder' ? window.__DIR : window.__DIR.__handleFor('Thu.nse.json');
        return { at: Math.round(performance.now()),
                 mem: JSON.parse(localStorage.getItem(STORE_KEY)).savedAt }; }""", body)
    print("  at +%sms after load, localStorage savedAt = %s" % (r["at"], r["mem"]))
    a.js("()=>{ window.__R = ensureFolder(false).then(reattachFile); }")
    a.wait(1500)
    print("  shown:", repr(a.js("()=>state.meeting.title")))
    print("  localStorage savedAt at +1500ms:",
          a.js("()=>JSON.parse(localStorage.getItem(STORE_KEY)).savedAt"))
    ok(a.js("()=>state.meeting.title") == "THURSDAY AGENDA",
       "the newer file is loaded when the comparison runs before the startup restamp")
