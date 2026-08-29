"""Write-path failures, permission shapes, and the file/folder disappearing."""
from harness import App, head, ok
import json

BANNER_HOOK = """()=>{ window.__BANNERS=[]; const orig=showBanner;
  showBanner=function(m,w){ window.__BANNERS.push([m,!!w]); return orig(m,w); }; }"""


def setup(a, name="E.nse.json", title="BASELINE"):
    a.js(BANNER_HOOK)
    a.attach_folder()
    a.js("(t)=>{ state.meeting.title=t; }", title)
    a.save_direct(name)
    a.wait(400)
    a.js("()=>{ window.__BANNERS=[]; window.__FSLOG=[]; }")
    return a.dir_get(name)


def report(a, name, label):
    d = a.dir_get(name)
    t = json.loads(d)["state"]["meeting"]["title"] if d else None
    print("  %-28s disk=%-20r badge=%s banners=%s" %
          (label, t, a.badge(), a.js("()=>window.__BANNERS")))
    return t


head("T04a — createWritable() / write() / close() throwing during an AUTOSAVE")
for fault in ["createWritable", "write", "close"]:
    with App() as a:
        setup(a)
        a.js("(f)=>{ window.__DIR.__st.faults[f] = {name:'InvalidStateError', message:f+' blew up'}; }", fault)
        a.js("()=>{ state.meeting.title='AFTER FAULT'; saveState(); }")
        a.wait(1700)
        t = report(a, "E.nse.json", fault + " autosave")
        ok(t == "BASELINE", "  %s: original file not damaged" % fault)
        ok(a.badge()["warn"] is True, "  %s: badge warns" % fault)
        # user keeps typing — does the warning survive?
        a.js("()=>{ state.meeting.title='STILL TYPING'; saveState(); }")
        a.wait(150)
        print("       badge after next keystroke:", a.badge())
        ok(a.badge()["warn"] is True, "  %s: warning survives the next keystroke" % fault)

head("T04b — QuotaExceededError on write() (disk full)")
with App() as a:
    setup(a, title="GOOD MEETING")
    a.js("()=>{ window.__DIR.__st.faults.write={name:'QuotaExceededError',message:'no space'}; }")
    a.js("()=>{ state.meeting.title='WORK DONE AFTER DISK FILLED'; saveState(); }")
    a.wait(1700)
    report(a, "E.nse.json", "quota autosave")
    a.save_direct()
    a.wait(500)
    report(a, "E.nse.json", "quota manual save")
    ok(a.badge()["warn"] is True, "disk-full manual Save leaves a warning badge")

head("T04c — close() succeeds but the file comes back EMPTY / stale")
with App() as a:
    setup(a, title="V1")
    a.js("()=>{ window.__DIR.__st.afterClose=(n,t)=>''; }")     # commits nothing
    a.js("()=>{ state.meeting.title='V2'; saveState(); }")
    a.wait(1700)
    report(a, "E.nse.json", "empty commit")
    ok(a.badge()["warn"] is True, "zero-length commit is detected")
with App() as a:
    setup(a, title="V1")
    a.js("()=>{ const keep=window.__DIR.__get('E.nse.json'); window.__DIR.__st.afterClose=(n,t)=>keep; }")
    a.js("()=>{ state.meeting.title='V2'; saveState(); }")
    a.wait(1700)
    t = report(a, "E.nse.json", "stale same-size commit")
    ok(t == "V2", "a same-length stale commit is detected")

head("T04d — permission: queryPermission 'prompt', requestPermission denied")
with App() as a:
    setup(a, title="P0")
    a.dir_ctl({"perm": "prompt"})
    a.js("()=>{ state.meeting.title='P1'; saveState(); }")
    a.wait(1700)
    report(a, "E.nse.json", "perm=prompt autosave")
    a.dir_ctl({"perm": "prompt", "requestPerm": "denied"})
    a.save_direct()
    a.wait(600)
    report(a, "E.nse.json", "perm denied manual save")
    ok(a.badge()["warn"] is True, "denied manual Save leaves a warning")

head("T04e — permission revoked between the check and the write")
with App() as a:
    setup(a, title="R0")
    a.js("""()=>{ const d=window.__DIR; const q=d.queryPermission.bind(d);
        d.queryPermission = async function(){ const r = await q(); d.__st.perm='denied';
            d.__st.faults.createWritable={name:'NotAllowedError',message:'permission revoked'};
            return r; }; }""")
    a.js("()=>{ state.meeting.title='R1'; saveState(); }")
    a.wait(1700)
    report(a, "E.nse.json", "revoked after check")
    ok(a.badge()["warn"] is True, "revoke-after-check warns")

head("T04f — the open file is DELETED / RENAMED by another program")
with App() as a:
    setup(a, "Del.nse.json", "KEEP ME")
    a.js("()=>{ window.__DIR.__st.files.delete('Del.nse.json'); }")
    print("  folder now:", a.dir_list())
    a.js("()=>{ state.meeting.title='AFTER DELETE'; saveState(); }")
    a.wait(1700)
    print("  folder after autosave:", a.dir_list())
    print("  badge:", a.badge())
    d = a.dir_get("Del.nse.json")
    ok(d is not None, "autosave recreated the deleted file")
with App() as a:
    setup(a, "Ren.nse.json", "ORIGINAL NAME")
    a.js("""()=>{ const st=window.__DIR.__st;
        st.files.set('Renamed-by-user.nse.json', st.files.get('Ren.nse.json'));
        st.files.delete('Ren.nse.json'); }""")
    a.js("()=>{ state.meeting.title='EDIT AFTER RENAME'; saveState(); }")
    a.wait(1700)
    print("  folder:", a.dir_list())
    print("  attached to:", a.open_file_name(), " badge:", a.badge())
    ok("Renamed-by-user.nse.json" in a.dir_list() and
       json.loads(a.dir_get("Renamed-by-user.nse.json"))["state"]["meeting"]["title"] == "EDIT AFTER RENAME",
       "edits follow the renamed file (they do not fork into a resurrected old name)")

head("T04g — the FOLDER goes away")
with App() as a:
    setup(a, "F.nse.json", "F0")
    a.js("()=>{ window.__DIR.__st.gone = true; }")
    a.js("()=>{ state.meeting.title='F1'; saveState(); }")
    a.wait(1700)
    print("  badge:", a.badge(), "banners:", a.js("()=>window.__BANNERS"))
    print("  pageerrors:", a.pageerrors)
    ok(a.badge()["warn"] is True, "a vanished folder warns")
    ok(not a.pageerrors, "no unhandled errors when the folder vanishes")
