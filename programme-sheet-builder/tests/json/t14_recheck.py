"""Re-checks with the picker wired up, plus the truncated-file recovery path."""
from harness import App, head, ok
import json

BANNER_HOOK = """()=>{ window.__BANNERS=[]; const orig=showBanner;
  showBanner=function(m,w){ window.__BANNERS.push([m,!!w]); return orig(m,w); }; }"""


def title_on_disk(a, name):
    t = a.dir_get(name)
    if not t:
        return None
    try:
        return json.loads(t)["state"]["meeting"]["title"]
    except Exception:
        return "<<CORRUPT %d bytes>>" % len(t)


head("T14a — N6 re-check: does reconnecting the folder actually resume?")
with App() as a:
    a.js(BANNER_HOOK)
    a.attach_folder()
    a.install_idb_stub()
    a.js("()=>{ state.meeting.title='L1'; }")
    a.save_direct("Lapse.nse.json")
    a.wait(500)
    files = {n: a.dir_get(n) for n in a.dir_list()}
    a.page.reload(wait_until="domcontentloaded", timeout=90000)
    a.wait(900)
    a.attach_folder({"perm": "prompt", "requestPerm": "granted"})
    for n, t in files.items():
        a.dir_set(n, t)
    a.install_idb_stub()
    a.js("()=>ensureFolder(false).then(reattachFile).then(refreshFileList)")
    a.wait(700)
    print("  lapsed grant -> attached=%r badge=%s" % (a.open_file_name(), a.badge()))
    a.js("()=>pickMeetingFile('__folder')")       # the dropdown's "reconnect"
    a.wait(900)
    print("  after reconnect  -> attached=%r" % a.open_file_name())
    print("  badge:", a.badge(), " warning:", repr(a.js("()=>saveWarning")))
    a.js("()=>{ state.meeting.title='work after reconnect'; saveState(); }")
    a.wait(2000)
    print("  disk:", title_on_disk(a, "Lapse.nse.json"), " badge:", a.badge())
    ok(a.open_file_name() == "Lapse.nse.json", "reconnecting re-attaches the file")
    ok(title_on_disk(a, "Lapse.nse.json") == "work after reconnect",
       "edits resume reaching the file, as the warning promises")
    ok(a.js("()=>saveWarning") == "", "the warning clears")

head("T14b — after a truncated write, can the user get their meeting back?")
with App() as a:
    a.js(BANNER_HOOK)
    a.attach_folder()
    a.install_idb_stub()
    a.js("()=>{ state.meeting.title='REAL MEETING'; state.roles.tmod='Rama'; }")
    a.save_direct("T.nse.json")
    a.wait(500)
    a.js("()=>{ window.__DIR.__st.afterClose=(n,t)=>t.slice(0,100); }")
    a.js("()=>{ state.meeting.title='REAL MEETING v2'; saveState(); }")
    a.wait(1800)
    print("  disk after the short write:", title_on_disk(a, "T.nse.json"))
    a.js("()=>{ window.__DIR.__st.afterClose=null; }")          # disk healthy again
    a.js("()=>{ state.meeting.title='v3'; saveState(); }")
    a.wait(1800)
    print("  autosave on a healthy disk -> disk:", title_on_disk(a, "T.nse.json"))
    print("  badge:", a.badge())
    ok(title_on_disk(a, "T.nse.json") == "v3", "autosave repairs the corrupt file by itself")
    # escape hatch 1: reopen from the dropdown
    a.js("()=>{ window.__BANNERS=[]; }")
    a.js("()=>pickMeetingFile('f:T.nse.json')")
    a.wait(800)
    print("  reopening it says:", a.js("()=>window.__BANNERS"))
    print("  app title now:", repr(a.js("()=>state.meeting.title")))
    # escape hatch 2: press Save (confirm auto-accepted)
    a.js("()=>{ window.__BANNERS=[]; state.meeting.title='rescued'; saveMeetingDirect(); }")
    a.wait(1200)
    print("  dialogs:", a.dialog_log)
    print("  after pressing Save -> disk:", title_on_disk(a, "T.nse.json"), " badge:", a.badge())
    ok(title_on_disk(a, "T.nse.json") == "rescued", "a manual Save repairs the file")

head("T14c — re-attach trusts localStorage over the file it attaches to")
with App() as a:
    a.attach_folder()
    a.install_idb_stub()
    a.js("()=>{ state.meeting.title='MEETING ON DISK'; state.roles.tmod='Alice'; }")
    a.save_direct("Disk.nse.json")
    a.wait(500)
    files = {n: a.dir_get(n) for n in a.dir_list()}
    # localStorage now describes a DIFFERENT meeting (what a second tab, or an
    # older session, would leave behind)
    a.js("""()=>{ const raw = JSON.parse(localStorage.getItem('nse-programme-builder-v6'));
        raw.state.meeting.title = 'SOMETHING ELSE ENTIRELY';
        raw.state.roles.tmod = 'Bob';
        localStorage.setItem('nse-programme-builder-v6', JSON.stringify(raw)); }""")
    a.reload_with_folder(files)
    print("  attached:", repr(a.open_file_name()), " badge:", a.badge())
    print("  app shows:", a.js("()=>state.meeting.title"))
    print("  file holds:", title_on_disk(a, "Disk.nse.json"))
    a.js("()=>{ state.meeting.footerNote='one keystroke'; saveState(); }")
    a.wait(2000)
    print("  file after ONE keystroke:", title_on_disk(a, "Disk.nse.json"))
    print("  badge:", a.badge(), " dialogs:", a.dialog_log)
    ok(title_on_disk(a, "Disk.nse.json") == "MEETING ON DISK",
       "the file is not silently replaced by whatever localStorage held")

head("T14d — cancelling either confirm: is the user told anything?")
with App(dialogs="dismiss") as a:
    a.js(BANNER_HOOK)
    a.attach_folder()
    a.install_idb_stub()
    a.js("()=>{ state.meeting.title='ONE'; }")
    a.save_direct("X.nse.json")
    a.wait(500)
    a.js("()=>{ fileHandle=null; lastWritten=''; state.meeting.title='TWO'; window.__BANNERS=[]; }")
    a.save_direct("X.nse.json")
    a.wait(900)
    print("  banners after cancelling the overwrite:", a.js("()=>window.__BANNERS"))
    print("  badge:", a.badge(), " attached:", repr(a.open_file_name()))
    ok(a.js("()=>window.__BANNERS"), "cancelling the overwrite says something")
