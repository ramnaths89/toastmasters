"""Non-Chrome fallback path, and what a reload does to an attached meeting."""
from harness import App, head, ok
import json, pathlib

head("T09a — FS_SUPPORTED false: Save downloads, picker reopens")
with App(fs_supported=False) as a:
    print("  FS_SUPPORTED =", a.js("()=>FS_SUPPORTED"))
    a.js("""()=>{ window.__DL=[]; const real=saveBlob;
        saveBlob = function(b,n){ window.__DL.push({name:n, size:b.size});
            const r=new FileReader(); r.onload=()=>window.__DLTEXT=r.result; r.readAsText(b); }; }""")
    a.js("()=>{ state.meeting.title='Firefox Meeting'; state.roles.tmod='Rama'; state.meeting.fileName='MyMeeting'; }")
    a.js("()=>saveMeetingDirect()")
    a.wait(400)
    print("  downloads:", a.js("()=>window.__DL"))
    txt = a.js("()=>window.__DLTEXT")
    ok(bool(txt), "a blob was produced")
    p = json.loads(txt)
    ok(p["state"]["meeting"]["title"] == "Firefox Meeting", "download carries the meeting")
    ok(p["v"] == 36, "download carries v36")
    dl = a.js("()=>window.__DL")
    ok(dl and dl[0]["name"].endswith(".nse.json"), "download name has the right extension")
    # dropdown offering
    a.js("()=>refreshFileList()")
    a.wait(200)
    print("  dropdown:", a.js("()=>document.getElementById('fileSelect').innerHTML"))
    # reopen through the picker path
    a.js("()=>{ state.meeting.title='WIPED'; state.roles.tmod=''; }")
    ok(a.js("(t)=>applyMeetingText(t,'MyMeeting.nse.json')", txt), "the downloaded file reopens")
    ok(a.js("()=>state.meeting.title") == "Firefox Meeting", "title restored")
    ok(a.js("()=>state.roles.tmod") == "Rama", "role restored")
    # autosave on the fallback path
    a.js("()=>{ state.meeting.title='EDITED AFTER OPEN'; saveState(); }")
    a.wait(1600)
    print("  downloads after an edit:", a.js("()=>window.__DL.length"), "(a second download would be wrong)")
    print("  badge:", a.badge())
    print("  pageerrors:", a.pageerrors)

head("T09b — reload: the attached file, the badge, and the next Save")
with App() as a:
    a.attach_folder()
    a.install_idb_stub()
    a.js("()=>{ state.meeting.title='Thursday Meeting'; saveState(); }")
    a.wait(600)
    a.js("()=>saveMeetingDirect()")             # auto name
    a.wait(600)
    first = a.dir_list()
    print("  saved as:", first, " fileName on state:", a.js("()=>state.meeting.fileName"))
    a.js("()=>{ state.meeting.title='Thursday Meeting v2'; saveState(); }")
    a.wait(1600)
    keep = {n: a.dir_get(n) for n in a.dir_list()}
    a.reload_with_folder(keep)
    print("  after reload: attached=%r badge=%s" % (a.open_file_name(), a.badge()))
    print("  state.meeting.fileName =", a.js("()=>state.meeting.fileName"))
    print("  restored title =", a.js("()=>state.meeting.title"))
    a.js("()=>{ state.meeting.title='Edited the next morning'; saveState(); }")
    a.wait(1700)
    on_disk = {n: json.loads(a.dir_get(n))["state"]["meeting"]["title"] for n in a.dir_list()}
    print("  disk after morning edits:", on_disk)
    print("  badge:", a.badge())
    ok(any(v == "Edited the next morning" for v in on_disk.values()),
       "post-reload edits reached the meeting file")
    # now the user presses Save
    a.js("()=>saveMeetingDirect()")
    a.wait(700)
    print("  folder after pressing Save:", a.dir_list())
    ok(len(a.dir_list()) == 1, "pressing Save updates the same file rather than making a second one")

head("T09c — reload with a stale IndexedDB folder handle whose grant lapsed")
with App() as a:
    a.attach_folder({"perm": "prompt", "requestPerm": "denied"})
    print("  ensureFolder(false):", a.js("()=>ensureFolder(false)"))
    a.js("()=>refreshFileList()")
    a.wait(300)
    print("  dropdown:", a.js("()=>document.getElementById('fileSelect').innerHTML"))
    print("  badge:", a.badge())
    a.js("()=>{ state.meeting.title='Typing with a lapsed grant'; saveState(); }")
    a.wait(1600)
    print("  badge after edit:", a.badge())
    print("  pageerrors:", a.pageerrors)
