"""Round 5: the value-compare reconciliation, the corrupt-file path, the new
cancel branch, resyncBaseline failure, and badge honesty in both directions."""
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


def build(a, name="M.nse.json", title="THURSDAY AGENDA"):
    a.attach_folder()
    a.install_idb_stub()
    a.js("(t)=>{ state.meeting.title=t; state.roles.tmod='Rama'; saveState(); }", title)
    a.wait(500)
    a.save_direct(name)
    a.wait(500)
    return a.dir_get(name)


head("T16a — same meeting, different savedAt: is the user left alone?")
with App() as a:
    txt = build(a)
    p = json.loads(txt)
    p["savedAt"] = "2026-08-09T21:00:00.000Z"          # only the stamp differs
    a.js("""()=>{ const raw=JSON.parse(localStorage.getItem('nse-programme-builder-v6'));
        raw.savedAt='2026-08-08T10:00:00.000Z';
        localStorage.setItem('nse-programme-builder-v6', JSON.stringify(raw)); }""")
    a.reload_with_folder({"M.nse.json": json.dumps(p, indent=2)})
    print("  dialogs:", a.dialog_log)
    print("  shown  :", repr(a.js("()=>state.meeting.title")), " badge:", a.badge())
    ok(not a.dialog_log, "identical meetings with different stamps ask nothing")
    ok(a.badge()["warn"] is False, "and leave a clean badge")
    a.js("()=>{ state.meeting.footerNote='x'; saveState(); }")
    a.wait(2000)
    ok(title_on_disk(a, "M.nse.json") == "THURSDAY AGENDA", "the file is untouched in substance")

head("T16b — the file is CORRUPT: what happens to the attachment?")
with App() as a:
    a.js(BANNER_HOOK)
    txt = build(a, "Bad.nse.json")
    a.reload_with_folder({"Bad.nse.json": "{ truncated garbage"})
    print("  attached :", repr(a.open_file_name()))
    print("  badge    :", a.badge())
    print("  banners  :", a.js("()=>window.__BANNERS"))
    print("  IDB file :", repr(a.js("()=>localStorage.getItem('__fake_idb_file')")))
    a.js("()=>{ state.meeting.title='trying to carry on'; saveState(); }")
    a.wait(2000)
    print("  disk after typing:", title_on_disk(a, "Bad.nse.json"))
    ok(a.open_file_name() != "", "the app stays attached to a corrupt file so it can repair it")
    ok("no longer in that folder" not in (a.badge()["title"] or ""),
       "the message describes what actually happened")

head("T16c — CANCEL the new reconciliation confirm, then type")
with App(dialogs="dismiss") as a:
    a.js(BANNER_HOOK)
    txt = build(a, "C.nse.json", "MEETING ON DISK")
    p = json.loads(txt)
    p["savedAt"] = "2026-08-09T21:00:00.000Z"
    p["state"]["meeting"]["title"] = "MEETING ON DISK"
    a.js("""()=>{ const raw=JSON.parse(localStorage.getItem('nse-programme-builder-v6'));
        raw.savedAt='2026-08-10T23:59:00.000Z';        /* browser looks newer */
        raw.state.meeting.title='BROWSER VERSION';
        localStorage.setItem('nse-programme-builder-v6', JSON.stringify(raw)); }""")
    a.reload_with_folder({"C.nse.json": json.dumps(p, indent=2)})
    print("  dialogs :", [m for _, m in a.dialog_log])
    print("  shown   :", repr(a.js("()=>state.meeting.title")))
    print("  banners :", a.js("()=>window.__BANNERS"))
    print("  badge   :", a.badge())
    ok(any("does not match" in m for _, m in a.dialog_log), "the user is asked")
    ok(a.js("()=>state.meeting.title") == "BROWSER VERSION", "Cancel keeps what is on screen")
    ok(a.badge()["warn"] is True or a.js("()=>window.__BANNERS"),
       "Cancel warns that the file is about to be replaced")
    a.js("()=>{ state.meeting.footerNote='typing'; saveState(); }")
    a.wait(2000)
    print("  disk after typing:", title_on_disk(a, "C.nse.json"))
    ok(title_on_disk(a, "C.nse.json") == "BROWSER VERSION",
       "and the replacement then happens exactly as announced")

head("T16d — resyncBaseline when the re-read itself fails")
with App() as a:
    a.js(BANNER_HOOK)
    build(a, "Rz.nse.json", "R0")
    a.js("""()=>{ const d=window.__DIR;
        d.__st.faults.write={name:'X',message:'write blew up'};
        const real = d.getFileHandle.bind(d);
        d.getFileHandle = async function(n,o){ const h = await real(n,o);
            h.getFile = async function(){ throw new Error('read blew up too'); };
            return h; };
        /* the attached handle must fail its re-read as well */
        fileHandle.getFile = async function(){ throw new Error('read blew up too'); }; }""")
    a.js("()=>{ state.meeting.title='R1'; saveState(); }")
    a.wait(2000)
    print("  baselines:", a.js("()=>Object.keys(baseline)"))
    print("  badge    :", a.badge())
    print("  pageerrors:", a.pageerrors)
    ok(not a.pageerrors, "a failed re-read does not throw out of the chain")
    # now everything recovers
    a.js("""()=>{ window.__DIR.__st.faults.write=null;
        delete fileHandle.getFile; }""")
    a.js("()=>{ state.meeting.title='R2'; saveState(); }")
    a.wait(2200)
    print("  disk:", title_on_disk(a, "Rz.nse.json"), " badge:", a.badge())
    ok(title_on_disk(a, "Rz.nse.json") == "R2", "writing resumes once the disk is healthy")

head("T16e — badge honesty in both directions over a fault/recovery cycle")
with App() as a:
    build(a, "H.nse.json", "H0")
    seq = []
    a.js("()=>{ window.__DIR.__st.faults.close={name:'X',message:'temporary'}; }")
    a.js("()=>{ state.meeting.title='H1'; saveState(); }")
    a.wait(1900); seq.append(("fault", a.badge()["warn"], title_on_disk(a, "H.nse.json")))
    a.js("()=>{ window.__DIR.__st.faults.close=null; }")
    a.js("()=>{ state.meeting.title='H2'; saveState(); }")
    a.wait(2100); seq.append(("recovered, idle", a.badge()["warn"], title_on_disk(a, "H.nse.json")))
    a.wait(1500); seq.append(("still idle", a.badge()["warn"], title_on_disk(a, "H.nse.json")))
    for label, warn, disk in seq:
        print("  %-18s badge-warn=%-5s disk=%r" % (label, warn, disk))
    ok(seq[0][1] is True and seq[1][1] is False and seq[2][1] is False,
       "the badge tracks the disk in both directions")

head("T16f — S5: can a name-keyed baseline still lose data?")
with App() as a:
    a.js(BANNER_HOOK)
    a.attach_folder()
    a.install_idb_stub()
    a.js("()=>{ state.meeting.title='FOLDER ONE'; }")
    a.save_direct("meeting.nse.json")
    a.wait(500)
    one = a.dir_get("meeting.nse.json")
    # switch to a second folder holding a same-named DIFFERENT meeting, then
    # come back to the first folder without ever reopening the file
    a.js("""(t)=>{ window.__ONE = window.__DIR;
        window.__TWO = window.__mkFakeDir({});
        window.__TWO.__set('meeting.nse.json', t);
        window.__DIR = window.__TWO; }""",
         one.replace('"FOLDER ONE"', '"FOLDER TWO"'))
    a.js("()=>pickMeetingFile('__folder')")
    a.wait(700)
    print("  after switching folder, attached:", repr(a.open_file_name()))
    print("  baseline keys:", a.js("()=>Object.keys(baseline)"))
    a.js("()=>{ state.meeting.title='edited against folder two'; saveState(); }")
    a.wait(2100)
    print("  folder TWO file:", title_on_disk(a, "meeting.nse.json"))
    print("  badge:", a.badge(), " dialogs:", a.dialog_log)
    ok(a.dialog_log or a.badge()["warn"] is True
       or title_on_disk(a, "meeting.nse.json") == "FOLDER TWO",
       "folder two's meeting is not silently overwritten via a stale name-keyed baseline")
