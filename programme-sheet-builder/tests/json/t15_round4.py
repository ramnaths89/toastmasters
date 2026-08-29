"""Round 4: the reattach reconciliation, per-file baselines, failure
invalidation, and whether the badge can stick on a resolved warning."""
from harness import App, head, ok
import json, re

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


def reconcile(label, file_stamp, mem_stamp, file_title="ON DISK", mem_title="IN BROWSER",
              corrupt_file=False, drop_file_stamp=False, drop_mem_stamp=False):
    """Build a file and a localStorage payload with controlled savedAt stamps,
    reload, and see which one wins."""
    with App() as a:
        a.js(BANNER_HOOK)
        a.attach_folder()
        a.install_idb_stub()
        a.js("(t)=>{ state.meeting.title=t; saveState(); }", file_title)
        a.wait(500)
        a.save_direct("M.nse.json")
        a.wait(500)
        txt = a.dir_get("M.nse.json")
        p = json.loads(txt)
        p["savedAt"] = file_stamp
        p["state"]["meeting"]["title"] = file_title
        if drop_file_stamp:
            del p["savedAt"]
        body = "{ truncated garbage" if corrupt_file else json.dumps(p, indent=2)
        files = {"M.nse.json": body}
        # localStorage side
        a.js("""(a)=>{ const raw = JSON.parse(localStorage.getItem('nse-programme-builder-v6'));
            raw.savedAt = a[0]; raw.state.meeting.title = a[1];
            if(a[2]) delete raw.savedAt;
            localStorage.setItem('nse-programme-builder-v6', JSON.stringify(raw)); }""",
             [mem_stamp, mem_title, drop_mem_stamp])
        a.reload_with_folder(files)
        shown = a.js("()=>state.meeting.title")
        banners = a.js("()=>window.__BANNERS")
        a.js("()=>{ state.meeting.footerNote='one keystroke'; saveState(); }")
        a.wait(2000)
        print("  %-34s shown=%-16r disk-after-keystroke=%-18r banner=%s"
              % (label, shown, title_on_disk(a, "M.nse.json"),
                 (banners[0][0][:52] + '…') if banners else None))
        return shown, title_on_disk(a, "M.nse.json")


head("T15a — reattach reconciliation: which copy wins, and is anything lost?")
OLD, NEW = "2026-08-10T09:00:00.000Z", "2026-08-10T18:00:00.000Z"
s, d = reconcile("file NEWER than browser", NEW, OLD)
ok(s == "ON DISK" and d == "ON DISK", "  the newer file wins and is not overwritten")
s, d = reconcile("browser NEWER than file", OLD, NEW)
ok(s == "IN BROWSER" and d == "IN BROWSER", "  the newer browser copy wins and is written out")
s, d = reconcile("stamps EQUAL", NEW, NEW)
print("       -> equal stamps resolve to:", s)
s, d = reconcile("file CORRUPT", NEW, OLD, corrupt_file=True)
ok(d == "IN BROWSER", "  a corrupt file is replaced by the browser copy")
s, d = reconcile("file has NO savedAt", NEW, OLD, drop_file_stamp=True)
print("       -> no-stamp file resolves to:", s, "| disk becomes:", d)
s, d = reconcile("browser has NO savedAt", OLD, NEW, drop_mem_stamp=True)
print("       -> no-stamp browser resolves to:", s, "| disk becomes:", d)
s, d = reconcile("file stamp MALFORMED", "not-a-date", OLD)
print("       -> malformed file stamp resolves to:", s, "| disk becomes:", d)


head("T15b — baseline invalidation under interleaved writes to two files")
with App() as a:
    a.js(BANNER_HOOK)
    a.attach_folder()
    a.install_idb_stub()
    a.js("()=>{ state.meeting.title='A0'; }")
    a.save_direct("A.nse.json")
    a.wait(500)
    a.js("()=>{ fileHandle=null; state.meeting.title='B0'; }")
    a.save_direct("B.nse.json")
    a.wait(500)
    print("  baselines held:", a.js("()=>Object.keys(baseline)"))
    # a write to A fails; does B's baseline survive?
    a.js("()=>pickMeetingFile('f:A.nse.json')")
    a.wait(600)
    a.js("()=>{ window.__DIR.__st.faults.write={name:'X',message:'A blew up'}; }")
    a.js("()=>{ state.meeting.title='A1'; saveState(); }")
    a.wait(1700)
    print("  after A's write failed, baselines:", a.js("()=>Object.keys(baseline)"))
    ok("B.nse.json" in a.js("()=>Object.keys(baseline)"),
       "a failure on A does not invalidate B's baseline")
    a.js("()=>{ window.__DIR.__st.faults.write=null; }")
    a.js("()=>pickMeetingFile('f:B.nse.json')")
    a.wait(700)
    a.js("()=>{ state.meeting.title='B1'; saveState(); }")
    a.wait(1900)
    print("  A:", title_on_disk(a, "A.nse.json"), " B:", title_on_disk(a, "B.nse.json"))
    print("  badge:", a.badge())
    ok(title_on_disk(a, "B.nse.json") == "B1", "B still autosaves after A's failure")

head("T15c — does failure-invalidation disable the two-tab guard for the next write?")
with App() as a:
    a.js(BANNER_HOOK)
    a.attach_folder()
    a.install_idb_stub()
    a.js("()=>{ state.meeting.title='MINE'; }")
    a.save_direct("S.nse.json")
    a.wait(500)
    # one transient failure -> baseline invalidated
    a.js("()=>{ window.__DIR.__st.faults.createWritable={name:'X',message:'transient'}; }")
    a.js("()=>{ state.meeting.title='MINE v2'; saveState(); }")
    a.wait(1700)
    print("  baseline after the failure:", a.js("()=>Object.keys(baseline)"))
    # the other tab now writes the file
    a.dir_set("S.nse.json", a.dir_get("S.nse.json").replace('"MINE"', '"THEIRS - hours of work"'))
    a.js("()=>{ window.__DIR.__st.faults.createWritable=null; }")
    a.js("()=>{ state.meeting.title='MINE v3'; saveState(); }")
    a.wait(1900)
    print("  disk:", title_on_disk(a, "S.nse.json"), " dialogs:", a.dialog_log, " badge:", a.badge())
    ok(title_on_disk(a, "S.nse.json") != "MINE v3" or a.dialog_log,
       "the other tab's file is not silently overwritten after a transient failure")

head("T15d — can an OLDER payload land after failure and recovery?")
with App() as a:
    a.attach_folder()
    a.install_idb_stub()
    a.js("()=>{ state.meeting.title='R0'; }")
    a.save_direct("R.nse.json")
    a.wait(500)
    a.js("()=>{ window.__FSLOG=[]; window.__DIR.__st.latency.close=2500;"
         "       window.__DIR.__st.faults.close={name:'X',message:'slow then fail'}; }")
    a.js("()=>{ state.meeting.title='R1'; saveState(); }")
    a.wait(1300)
    a.js("()=>{ window.__DIR.__st.latency.close=5; window.__DIR.__st.faults.close=null; }")
    a.js("()=>{ state.meeting.title='R2 (newest)'; saveState(); }")
    a.wait(6000)
    print("  commits:", [(e["marker"], e["t"]) for e in a.fslog() if e["ev"] == "close"])
    print("  disk:", title_on_disk(a, "R.nse.json"), " badge:", a.badge())
    ok(title_on_disk(a, "R.nse.json") == "R2 (newest)",
       "the newest payload is what survives a failure-then-recovery")

head("T15e — can the badge stick on a warning after the problem is fixed?")
with App() as a:
    a.attach_folder()
    a.install_idb_stub()
    a.js("()=>{ state.meeting.title='W0'; }")
    a.save_direct("W.nse.json")
    a.wait(500)
    a.js("()=>{ window.__DIR.__st.faults.write={name:'X',message:'temporary'}; }")
    a.js("()=>{ state.meeting.title='W1'; saveState(); }")
    a.wait(1700)
    print("  during the fault :", a.badge())
    a.js("()=>{ window.__DIR.__st.faults.write=null; }")
    a.js("()=>{ state.meeting.title='W2'; saveState(); }")
    a.wait(1900)                       # this autosave SUCCEEDS and clears the warning
    print("  after the successful write, user stops typing:")
    print("    saveWarning =", repr(a.js("()=>saveWarning")))
    print("    disk        =", title_on_disk(a, "W.nse.json"))
    print("    badge       =", a.badge())
    ok(a.badge()["warn"] is False,
       "the badge goes green again once a write has actually succeeded")
    a.js("()=>{ state.meeting.title='W3'; saveState(); }")
    a.wait(200)
    print("  after one more keystroke:", a.badge())

head("T15f — the baseline is keyed on file NAME, not on the folder")
with App() as a:
    a.js(BANNER_HOOK)
    a.attach_folder()
    a.install_idb_stub()
    a.js("()=>{ state.meeting.title='FOLDER ONE COPY'; }")
    a.save_direct("meeting.nse.json")
    a.wait(500)
    one = a.dir_get("meeting.nse.json")
    print("  baseline keys:", a.js("()=>Object.keys(baseline)"))
    # user switches to a different folder that happens to hold the same file name
    a.js("""(t)=>{ window.__DIR2 = window.__mkFakeDir({});
        window.__DIR2.__set('meeting.nse.json', t);
        window.__DIR = window.__DIR2; }""",
         one.replace('"FOLDER ONE COPY"', '"FOLDER TWO - DIFFERENT MEETING"'))
    a.js("()=>pickMeetingFile('__folder')")
    a.wait(700)
    a.js("()=>pickMeetingFile('f:meeting.nse.json')")
    a.wait(700)
    print("  loaded:", repr(a.js("()=>state.meeting.title")))
    a.js("()=>{ state.meeting.title='edited in folder two'; saveState(); }")
    a.wait(1900)
    print("  folder two file:", title_on_disk(a, "meeting.nse.json"), " badge:", a.badge())
    ok(title_on_disk(a, "meeting.nse.json") == "edited in folder two",
       "a same-named file in a different folder is not blocked by a stale baseline")
