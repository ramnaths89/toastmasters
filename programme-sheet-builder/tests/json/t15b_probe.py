from harness import App, head, ok
import json
head("probe — does the 'file was newer' banner actually appear, and what if the two copies are DIFFERENT meetings?")
for label, file_stamp, mem_stamp in [("file newer","2026-08-10T18:00:00.000Z","2026-08-10T09:00:00.000Z"),
                                     ("browser newer","2026-08-10T09:00:00.000Z","2026-08-10T18:00:00.000Z")]:
    with App() as a:
        a.attach_folder(); a.install_idb_stub()
        a.js("()=>{ state.meeting.title='THURSDAY AGENDA'; state.roles.tmod='Rama'; saveState(); }")
        a.wait(500); a.save_direct("Thu.nse.json"); a.wait(500)
        p = json.loads(a.dir_get("Thu.nse.json")); p["savedAt"] = file_stamp
        files = {"Thu.nse.json": json.dumps(p, indent=2)}
        a.js("""(s)=>{ const raw=JSON.parse(localStorage.getItem('nse-programme-builder-v6'));
            raw.savedAt=s; raw.state.meeting.title='A COMPLETELY DIFFERENT MEETING';
            raw.state.roles.tmod='Someone Else';
            localStorage.setItem('nse-programme-builder-v6', JSON.stringify(raw)); }""", mem_stamp)
        a.page.reload(wait_until="domcontentloaded", timeout=90000); a.wait(900)
        a.attach_folder()
        for n,t in files.items(): a.dir_set(n,t)
        a.install_idb_stub()
        a.js("""()=>{ window.__BANNERS=[]; const o=showBanner;
            showBanner=function(m,w){ window.__BANNERS.push([m,!!w]); return o(m,w); }; }""")
        a.js("()=>ensureFolder(false).then(reattachFile).then(refreshFileList)")
        a.wait(900)
        print("  [%s] shown=%r banners=%s" % (label, a.js("()=>state.meeting.title"),
                                              a.js("()=>window.__BANNERS")))
        a.js("()=>{ state.meeting.footerNote='x'; saveState(); }"); a.wait(2000)
        d = json.loads(a.dir_get("Thu.nse.json"))["state"]
        print("       disk after one keystroke: title=%r tmod=%r" % (d["meeting"]["title"], d["roles"]["tmod"]))
        print("       badge:", a.badge())
