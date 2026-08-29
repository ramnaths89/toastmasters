"""The silent-divergence class: green tick on screen, stale/wrong bytes on disk."""
from harness import App, head, ok
import json

BANNER_HOOK = """()=>{ window.__BANNERS=[];
  const orig = showBanner;
  showBanner = function(m,w){ window.__BANNERS.push([m,!!w]); return orig(m,w); }; }"""


def banners(a):
    return a.js("()=>window.__BANNERS")


head("T02a — a failed MANUAL save leaves the badge green")
with App() as a:
    a.js(BANNER_HOOK)
    a.attach_folder()
    a.js("()=>{ state.meeting.title='Good'; }")
    a.save_direct("M.nse.json")
    a.wait(300)
    good = a.dir_get("M.nse.json")
    # now every close() truncates
    a.js("()=>{ window.__DIR.__st.afterClose=(n,t)=>t.slice(0,40); }")
    a.js("()=>{ window.__BANNERS=[]; state.meeting.title='Later work'; }")
    a.save_direct()
    a.wait(500)
    print("  banners:", banners(a))
    print("  badge  :", a.badge())
    ok(a.badge()["warn"] is True, "failed manual save turns the badge to warn")
    print("  on disk now:", repr(a.dir_get("M.nse.json"))[:80])


head("T02b — one keystroke after a failed autosave repaints the badge green")
with App() as a:
    a.attach_folder()
    a.js("()=>{ state.meeting.title='Attached'; }")
    a.save_direct("B.nse.json")
    a.wait(300)
    ondisk_before = a.dir_get("B.nse.json")
    # permission silently lapses
    a.dir_ctl({"perm": "denied"})
    a.js("()=>{ state.meeting.title='Edit 1'; saveState(); }")
    a.wait(1600)
    b1 = a.badge()
    print("  after failed autosave:", b1)
    ok(b1["warn"] is True, "autosave failure warns")
    a.js("()=>{ state.meeting.title='Edit 2'; saveState(); }")
    a.wait(120)                       # flashSaved fires immediately inside saveState
    b2 = a.badge()
    print("  after next keystroke :", b2)
    ok(b2["warn"] is True, "badge STAYS warn while the file is stale")
    a.wait(1600)
    ok(a.dir_get("B.nse.json") == ondisk_before, "(file is indeed stale)")


head("T02c — localStorage failure permanently kills FILE autosave too")
with App() as a:
    a.attach_folder()
    a.js("()=>{ state.meeting.title='Before quota'; }")
    a.save_direct("Q.nse.json")
    a.wait(300)
    base = json.loads(a.dir_get("Q.nse.json"))["state"]["meeting"]["title"]
    a.js("""()=>{ const real = localStorage.setItem.bind(localStorage);
        localStorage.setItem = function(){ const e=new Error('quota'); e.name='QuotaExceededError'; throw e; }; }""")
    a.js("()=>{ state.meeting.title='After quota A'; saveState(); }")
    a.wait(1600)
    t1 = json.loads(a.dir_get("Q.nse.json"))["state"]["meeting"]["title"]
    print("  badge:", a.badge())
    print("  disk title after 1st failing save:", t1)
    # localStorage recovers, but storageOK is latched false
    a.js("""()=>{ localStorage.setItem = Storage.prototype.setItem.bind(localStorage); }""")
    a.js("()=>{ state.meeting.title='After quota B'; saveState(); }")
    a.wait(1600)
    t2 = json.loads(a.dir_get("Q.nse.json"))["state"]["meeting"]["title"]
    print("  disk title after recovery   :", t2)
    ok(t2 == "After quota B",
       "file autosave resumes once localStorage works again (storageOK not latched)")
    ok(t1 == "After quota A",
       "a localStorage quota error does not stop the FILE from being written")


head("T02d — reload with the folder still granted: is the open file re-attached?")
with App() as a:
    a.attach_folder()
    a.install_idb_stub()
    a.js("()=>{ state.meeting.title='Session One'; saveState(); }")
    a.wait(600)
    a.save_direct("R.nse.json")
    a.wait(400)
    files = {n: a.dir_get(n) for n in a.dir_list()}
    a.reload_with_folder(files)
    print("  after reload openFileName:", repr(a.open_file_name()))
    print("  badge:", a.badge())
    print("  restored title:", a.js("()=>state.meeting.title"))
    ok(a.open_file_name() != "", "the open meeting file is re-attached after a reload")
    a.js("()=>{ state.meeting.title='Post reload edit'; saveState(); }")
    a.wait(1700)
    now = json.loads(a.dir_get("R.nse.json"))["state"]["meeting"]["title"]
    print("  disk title after post-reload edit:", now)
    ok(now == "Post reload edit", "edits after a reload still reach the file")
    print("  badge:", a.badge())
