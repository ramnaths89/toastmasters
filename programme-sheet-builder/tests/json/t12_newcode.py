"""Attack the NEW write path: enqueueWrite / lastWritten / saveWarning /
reattachFile / the external-change guard."""
from harness import App, head, ok
import json

BANNER_HOOK = """()=>{ window.__BANNERS=[]; const orig=showBanner;
  showBanner=function(m,w){ window.__BANNERS.push([m,!!w]); return orig(m,w); }; }"""


def setup(a, name="E.nse.json", title="BASELINE"):
    a.js(BANNER_HOOK)
    a.attach_folder()
    a.install_idb_stub()
    a.js("(t)=>{ state.meeting.title=t; }", title)
    a.save_direct(name)
    a.wait(500)
    a.js("()=>{ window.__BANNERS=[]; window.__FSLOG=[]; }")


def title_on_disk(a, name):
    t = a.dir_get(name)
    if not t:
        return None
    try:
        return json.loads(t)["state"]["meeting"]["title"]
    except Exception:
        return "<<CORRUPT %d bytes>>" % len(t)


head("T12a — one short write wedges autosave FOREVER, with the wrong diagnosis")
with App() as a:
    setup(a, title="V1")
    # a single transient truncated commit (full disk, sync client, USB yank)
    a.js("()=>{ window.__DIR.__st.afterClose=(n,t)=>t.slice(0,100); }")
    a.js("()=>{ state.meeting.title='V2'; saveState(); }")
    a.wait(1700)
    print("  after the short write:", a.badge())
    print("  baseline length =", a.js("()=>getBaseline(fileHandle).length"),
          " file length =", len(a.dir_get("E.nse.json") or ""))
    # the fault is over — the disk is healthy again
    a.js("()=>{ window.__DIR.__st.afterClose=null; }")
    for i in range(3):
        a.js("(i)=>{ state.meeting.title='V3-'+i; saveState(); }", i)
        a.wait(1600)
    print("  after 3 more edits on a healthy disk:", a.badge())
    print("  disk:", (a.dir_get("E.nse.json") or "")[:60])
    print("  banners:", a.js("()=>window.__BANNERS"))
    ok(title_on_disk(a, "E.nse.json") == "V3-2",
       "autosave recovers once the disk is healthy again")

head("T12b — the savedAt read-back check: is it ever reached?")
with App() as a:
    setup(a, title="S1")
    a.js("()=>{ const keep=window.__DIR.__get('E.nse.json');"
         "       window.__DIR.__st.afterClose=(n,t)=> keep + ' '.repeat(t.length-keep.length); }")
    a.js("()=>{ state.meeting.title='S2'; saveState(); }")
    a.wait(1700)
    print("  badge:", a.badge())
    print("  disk still says:", title_on_disk(a, "E.nse.json"))
    ok(a.badge()["warn"] is True,
       "a same-LENGTH stale commit is caught by the savedAt check")

head("T12c — a failed MANUAL save still shows a green tick")
with App() as a:
    setup(a, title="M1")
    a.js("()=>{ window.__DIR.__st.faults.write={name:'QuotaExceededError',message:'no space'}; }")
    a.js("()=>{ state.meeting.title='M2'; }")
    a.js("()=>saveMeetingDirect()")
    a.wait(800)
    print("  banners:", a.js("()=>window.__BANNERS"))
    print("  badge  :", a.badge(), " saveWarning=", a.js("()=>saveWarning"))
    ok(a.badge()["warn"] is True, "a failed manual Save leaves a sticky warning")

head("T12d — 'superseded' is reported to the user as a failure")
with App() as a:
    setup(a, title="P1")
    a.js("()=>{ window.__DIR.__st.latency.close = 900; window.__BANNERS=[]; }")
    a.js("()=>{ state.meeting.title='P2'; saveState(); }")   # autosave fires at +1200
    a.wait(1250)                                             # its write is now in the chain
    a.js("()=>{ state.meeting.title='P3'; saveState(); }")   # queues another at +1200
    a.wait(80)
    a.js("()=>{ state.meeting.title='P4-manual'; saveMeetingDirect(); }")
    a.wait(4000)
    print("  banners:", a.js("()=>window.__BANNERS"))
    print("  badge  :", a.badge())
    print("  disk   :", title_on_disk(a, "E.nse.json"))
    b = a.js("()=>window.__BANNERS")
    ok(not any("superseded" in m for m, w in b),
       "the user is never shown a 'superseded' failure for a save that did land")

head("T12e — Save As inside the debounce: does the old file keep the last edit?")
with App() as a:
    setup(a, "Orig.nse.json", "ORIGINAL")
    a.js("()=>{ state.meeting.title='LATE EDIT TO ORIGINAL'; saveState(); }")
    a.wait(200)                                    # inside the 1200ms debounce
    a.js("""()=>{ /* exactly what confirmSaveDialog does for Save As */
        flushFileSave(); clearTimeout(fileSaveTimer); fileSaveTimer=null; fileHandle=null;
        state.meeting.fileName='Copy'; saveMeetingDirect('Copy.nse.json'); }""")
    a.wait(2500)
    print("  Orig:", title_on_disk(a, "Orig.nse.json"))
    print("  Copy:", title_on_disk(a, "Copy.nse.json"))
    print("  badge:", a.badge())
    ok(title_on_disk(a, "Orig.nse.json") == "LATE EDIT TO ORIGINAL",
       "the file being left behind keeps the edit made just before Save As")

head("T12f — reattachFile: folder granted, file gone / grant lapsed")
with App() as a:
    setup(a, "Gone.nse.json", "G1")
    files = {n: a.dir_get(n) for n in a.dir_list()}
    del files["Gone.nse.json"]                     # user deleted it between sessions
    a.reload_with_folder(files)
    print("  attached:", repr(a.open_file_name()), " badge:", a.badge())
    print("  saveWarning:", a.js("()=>saveWarning"))
    ok(a.badge()["warn"] is True, "a vanished file gives a sticky warning, not a green tick")
    a.js("()=>{ state.meeting.title='typing with no file'; saveState(); }")
    a.wait(1600)
    print("  badge after typing:", a.badge())
    ok(a.badge()["warn"] is True, "the warning survives typing")

with App() as a:
    setup(a, "Lapse.nse.json", "L1")
    files = {n: a.dir_get(n) for n in a.dir_list()}
    a.page.reload(wait_until="domcontentloaded", timeout=90000)
    a.wait(900)
    a.attach_folder({"perm": "prompt", "requestPerm": "granted"})
    for n, t in files.items():
        a.dir_set(n, t)
    a.install_idb_stub()
    a.js("()=>ensureFolder(false).then(reattachFile).then(refreshFileList)")
    a.wait(700)
    print("  lapsed grant -> attached:", repr(a.open_file_name()), " badge:", a.badge())
    print("  saveWarning:", a.js("()=>saveWarning"))
    # the user now does what the message says: reconnect the folder
    a.js("()=>pickMeetingFile('__folder')")
    a.wait(700)
    print("  after reconnecting the folder: attached=%r badge=%s"
          % (a.open_file_name(), a.badge()))
    print("  saveWarning:", a.js("()=>saveWarning"))
    a.js("()=>{ state.meeting.title='work after reconnect'; saveState(); }")
    a.wait(1700)
    print("  disk:", title_on_disk(a, "Lapse.nse.json"), " badge:", a.badge())
    ok(title_on_disk(a, "Lapse.nse.json") == "work after reconnect",
       "reconnecting the folder resumes saving into the open file, as the message promises")

head("T12g — the external-change guard vs a file legitimately edited elsewhere")
with App() as a:
    setup(a, "Shared.nse.json", "MINE")
    other = a.dir_get("Shared.nse.json").replace('"MINE"', '"THEIRS"')
    a.dir_set("Shared.nse.json", other)            # another tab / another machine wrote it
    a.js("()=>{ state.meeting.title='MINE v2'; saveState(); }")
    a.wait(1700)
    print("  badge:", a.badge())
    print("  disk :", title_on_disk(a, "Shared.nse.json"))
    ok(title_on_disk(a, "Shared.nse.json") == "THEIRS", "the other party's file was not clobbered")
    # the message says: reopen from the dropdown, or Save As. Does Save As work?
    a.js("()=>{ window.__BANNERS=[]; }")
    a.js("()=>{ fileHandle=null; state.meeting.fileName='Mine-copy'; saveMeetingDirect('Mine-copy.nse.json'); }")
    a.wait(900)
    print("  after Save As:", a.dir_list(), " badge:", a.badge(), " warning:", a.js("()=>saveWarning"))
    ok(a.badge()["warn"] is False, "Save As clears the warning and gets the user working again")
    # ... and what does a plain manual Save onto the changed file do?
with App() as a:
    setup(a, "Shared.nse.json", "MINE")
    other = a.dir_get("Shared.nse.json").replace('"MINE"', '"THEIRS"')
    a.dir_set("Shared.nse.json", other)
    a.js("()=>{ state.meeting.title='MINE v2'; saveState(); }")
    a.wait(1700)
    a.js("()=>saveMeetingDirect()")                # user presses Save
    a.wait(900)
    print("  after pressing Save: disk =", title_on_disk(a, "Shared.nse.json"),
          " badge =", a.badge())
    ok(title_on_disk(a, "Shared.nse.json") == "THEIRS",
       "a manual Save also respects the external change")

head("T12h — the empty-sheet warning is not sticky")
with App() as a:
    setup(a, "Emp.nse.json", "E1")
    a.js("()=>{ window.__SEGS = state.segments.slice(); state.segments=[]; saveState(); }")
    a.wait(1600)
    print("  badge while empty:", a.badge())
    a.js("()=>{ state.meeting.title='still empty, still typing'; saveState(); }")
    a.wait(150)
    print("  badge after one more keystroke:", a.badge())
    ok(a.badge()["warn"] is True,
       "the 'no programme items, not autosaving' warning survives a keystroke")

head("T12i — two tabs now BOTH re-attach the same file")
with App() as a:
    setup(a, "Duel.nse.json", "TAB ONE")
    files = {n: a.dir_get(n) for n in a.dir_list()}
    a.install_idb_stub()
    p2 = a.ctx.new_page()
    p2.route("http*://**", lambda r: r.abort())
    p2.on("dialog", lambda d: d.accept("ok"))
    p2.goto(a.build.as_uri(), wait_until="domcontentloaded", timeout=90000)
    p2.wait_for_timeout(1000)
    p2.evaluate("(o)=>{ window.__DIR = window.__mkFakeDir(o); folderHandle = window.__DIR; }", {})
    p2.evaluate("(a)=>{ window.__DIR.__set(a[0], a[1]); }", ["Duel.nse.json", files["Duel.nse.json"]])
    p2.evaluate(App.IDB_STUB)
    p2.evaluate("()=>ensureFolder(false).then(reattachFile).then(refreshFileList)")
    p2.wait_for_timeout(700)
    print("  tab2 attached:", p2.evaluate("()=>openFileName()"),
          " badge:", p2.evaluate("()=>document.getElementById('saveDot').title"))
    p2.evaluate("()=>{ state.meeting.title='TAB TWO WORK'; saveState(); }")
    p2.wait_for_timeout(1700)
    a.js("()=>{ state.meeting.title='TAB ONE WORK'; saveState(); }")
    a.wait(1700)
    print("  tab1 badge:", a.badge())
    print("  tab1 view of its own file:", title_on_disk(a, "Duel.nse.json"))
    print("  NOTE: each tab has its own fake folder here, so this only shows that")
    print("        BOTH tabs re-attach and both believe they own the file.")
    p2.close()

head("T12j — can a manual Save be superseded and reported as a failure?")
with App() as a:
    setup(a, title="Q1")
    a.js("()=>{ window.__DIR.__st.latency.close = 2500; window.__BANNERS=[]; }")
    a.js("()=>{ state.meeting.title='Q2'; saveState(); }")
    a.wait(1300)                       # autosave #1 is inside writeHandle, chain busy
    a.js("()=>{ state.meeting.title='Q3-manual'; window.__P = saveMeetingDirect(); }")
    a.wait(60)
    a.js("()=>{ state.meeting.title='Q4'; saveState(); }")   # queues autosave #2
    a.wait(1400)                       # autosave #2 enqueues, bumping writeSeq past the manual save
    a.wait(4000)
    print("  banners:", a.js("()=>window.__BANNERS"))
    print("  badge  :", a.badge())
    print("  disk   :", title_on_disk(a, "E.nse.json"))
    b = a.js("()=>window.__BANNERS")
    ok(not any("superseded" in m for m, w in b),
       "no 'superseded' failure banner for a save whose content did reach disk")
