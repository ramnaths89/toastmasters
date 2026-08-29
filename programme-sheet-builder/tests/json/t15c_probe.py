from harness import App, head
import json
head("probe — what stamps does reattachFile actually compare?")
with App() as a:
    a.attach_folder(); a.install_idb_stub()
    a.js("()=>{ state.meeting.title='THURSDAY AGENDA'; saveState(); }")
    a.wait(500); a.save_direct("Thu.nse.json"); a.wait(500)
    p = json.loads(a.dir_get("Thu.nse.json")); p["savedAt"] = "2026-08-10T18:00:00.000Z"
    files = {"Thu.nse.json": json.dumps(p, indent=2)}
    a.js("""()=>{ const raw=JSON.parse(localStorage.getItem('nse-programme-builder-v6'));
        raw.savedAt='2026-08-10T09:00:00.000Z'; raw.state.meeting.title='DIFFERENT MEETING';
        localStorage.setItem('nse-programme-builder-v6', JSON.stringify(raw)); }""")
    print("  ls savedAt before reload:", a.js("()=>JSON.parse(localStorage.getItem('nse-programme-builder-v6')).savedAt"))
    a.page.reload(wait_until="domcontentloaded", timeout=90000); a.wait(900)
    print("  ls savedAt AFTER reload :", a.js("()=>JSON.parse(localStorage.getItem('nse-programme-builder-v6')).savedAt"))
    print("  title after reload      :", a.js("()=>state.meeting.title"))
    a.attach_folder()
    for n,t in files.items(): a.dir_set(n,t)
    a.install_idb_stub()
    r = a.js("""async ()=>{
        const h = await idbGet('file');
        const disk = await folderHandle.getFileHandle(h.name);
        const diskText = await (await disk.getFile()).text();
        let diskAt=0, memAt=0;
        try{ diskAt = Date.parse(JSON.parse(diskText).savedAt) || 0; }catch(e){}
        try{ memAt = Date.parse(JSON.parse(localStorage.getItem(STORE_KEY)).savedAt) || 0; }catch(e){}
        return {diskAt:new Date(diskAt).toISOString(), memAt:new Date(memAt).toISOString(), newer: diskAt>memAt}; }""")
    print("  comparison:", r)
