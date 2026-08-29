from harness import App, head, ok
import json
head("T15e2 — same, but reattachFile runs IMMEDIATELY after load (as the app does)")
with App() as a:
    a.attach_folder(); a.install_idb_stub()
    a.js("()=>{ state.meeting.title='THURSDAY AGENDA'; state.roles.tmod='Rama'; saveState(); }")
    a.wait(500); a.save_direct("Thu.nse.json"); a.wait(500)
    p = json.loads(a.dir_get("Thu.nse.json")); p["savedAt"] = "2026-08-09T21:00:00.000Z"
    body = json.dumps(p, indent=2)
    a.js("""()=>{ const raw=JSON.parse(localStorage.getItem('nse-programme-builder-v6'));
        raw.savedAt='2026-08-08T10:00:00.000Z'; raw.state.meeting.title='STALE BROWSER COPY';
        raw.state.roles.tmod='';
        localStorage.setItem('nse-programme-builder-v6', JSON.stringify(raw)); }""")
    a.page.reload(wait_until="domcontentloaded", timeout=90000)
    # no wait: rebuild the folder and fire the startup chain as fast as we can
    a.js("(t)=>{ window.__DIR = window.__mkFakeDir({}); folderHandle = window.__DIR;"
         "        window.__DIR.__set('Thu.nse.json', t); }", body)
    a.install_idb_stub()
    a.js("()=>{ window.__T0=performance.now(); window.__CHAIN = ensureFolder(false).then(reattachFile)"
         "        .then(()=>{ window.__DONE = performance.now()-window.__T0; }); }")
    a.wait(1500)
    print("  reattach finished %s ms after it was started" % a.js("()=>Math.round(window.__DONE)"))
    print("  shown:", repr(a.js("()=>state.meeting.title")))
    print("  localStorage savedAt now:",
          a.js("()=>JSON.parse(localStorage.getItem('nse-programme-builder-v6')).savedAt"))
    a.js("()=>{ state.meeting.footerNote='one keystroke'; saveState(); }")
    a.wait(2000)
    d = json.loads(a.dir_get("Thu.nse.json"))["state"]
    print("  file after one keystroke: title=%r tmod=%r" % (d["meeting"]["title"], d["roles"]["tmod"]))
    ok(d["meeting"]["title"] == "THURSDAY AGENDA",
       "with fast startup, the newer file wins")
