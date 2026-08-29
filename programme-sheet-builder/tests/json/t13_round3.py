"""Round 3: the value-captured chain, the confirm dismiss paths, the shared
lastWritten baseline, chain recovery, and the pagehide flush."""
from harness import App, head, ok
import json, time

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


head("T13a — DISMISS the external-change confirm on a manual Save")
with App(dialogs="dismiss") as a:
    setup(a, "Shared.nse.json", "MINE")
    a.dir_set("Shared.nse.json", a.dir_get("Shared.nse.json").replace('"MINE"', '"THEIRS"'))
    a.js("()=>{ state.meeting.title='MINE v2'; saveState(); }")
    a.wait(1700)
    a.js("()=>saveMeetingDirect()")
    a.wait(900)
    print("  dialogs seen:", a.dialog_log)
    print("  disk:", title_on_disk(a, "Shared.nse.json"), " badge:", a.badge())
    ok(any("changed outside this tab" in m for _, m in a.dialog_log),
       "the user is asked before replacing an externally changed file")
    ok(title_on_disk(a, "Shared.nse.json") == "THEIRS",
       "saying No leaves the other version intact")

head("T13b — DISMISS the overwrite confirm on Save As (F6/N11)")
with App(dialogs="dismiss") as a:
    setup(a, "Clash.nse.json", "MEETING ONE - do not lose me")
    a.js("()=>{ fileHandle=null; lastWritten=''; state.meeting.title='MEETING TWO'; }")
    a.save_direct("Clash.nse.json")
    a.wait(900)
    print("  dialogs seen:", a.dialog_log)
    print("  disk:", title_on_disk(a, "Clash.nse.json"))
    ok(any("already exists" in m for _, m in a.dialog_log), "the overwrite confirm fires")
    ok(title_on_disk(a, "Clash.nse.json") == "MEETING ONE - do not lose me",
       "saying No leaves the existing meeting untouched")
    print("  badge:", a.badge(), " attached:", repr(a.open_file_name()))

head("T13c — TOCTOU: can the other tab's work die with NO prompt?")
with App() as a:
    setup(a, "Race.nse.json", "MINE")
    # the other tab writes AFTER our guard read but BEFORE our commit
    a.js("""()=>{ const d = window.__DIR;
        const real = d.getFileHandle.bind(d);
        window.__theirs = null;
        d.getFileHandle = async function(n, o){
            const h = await real(n, o);
            const gf = h.getFile.bind(h);
            h.getFile = async function(){
                const f = await gf();
                /* the instant we hand the guard its snapshot, the other tab writes */
                if(!window.__theirs){
                    window.__theirs = d.__get(n).replace('"MINE"','"THEIRS - unsaved work"');
                    d.__set(n, window.__theirs);
                }
                return f;
            };
            return h; };
        }""")
    a.js("()=>{ state.meeting.title='MINE v2'; saveState(); }")
    a.wait(2000)
    print("  dialogs:", a.dialog_log)
    print("  disk   :", title_on_disk(a, "Race.nse.json"))
    print("  badge  :", a.badge())
    ok(title_on_disk(a, "Race.nse.json") != "MINE v2" or a.dialog_log,
       "the other tab's write is not silently overwritten")

head("T13d — the shared lastWritten baseline poisoned by a write to ANOTHER file")
with App() as a:
    a.attach_folder()
    a.install_idb_stub()
    a.js("()=>{ state.meeting.title='MEETING A'; }")
    a.save_direct("A.nse.json")
    a.wait(500)
    a.js("()=>{ fileHandle=null; lastWritten=''; state.meeting.title='MEETING B'; }")
    a.save_direct("B.nse.json")
    a.wait(500)
    a.js("()=>pickMeetingFile('f:A.nse.json')")
    a.wait(600)
    a.js("()=>{ state.meeting.title='A edited'; saveState(); }")
    a.wait(150)                       # inside the debounce -> pickMeetingFile will flush
    a.js("()=>pickMeetingFile('f:B.nse.json')")
    a.wait(1200)
    print("  attached:", a.open_file_name())
    print("  baseline(B) starts:", a.js("()=>getBaseline(fileHandle).slice(0,90)").replace("\n", " "))
    a.js("()=>{ state.meeting.title='B edited after switching'; saveState(); }")
    a.wait(2000)
    print("  A on disk:", title_on_disk(a, "A.nse.json"))
    print("  B on disk:", title_on_disk(a, "B.nse.json"))
    print("  badge:", a.badge())
    ok(title_on_disk(a, "B.nse.json") == "B edited after switching",
       "editing B after switching from A still autosaves into B")

head("T13e — does the write chain recover after a task throws mid-chain?")
with App() as a:
    setup(a, title="C0")
    a.js("()=>{ window.__DIR.__st.faults.write={name:'InvalidStateError',message:'boom'}; }")
    a.js("()=>{ state.meeting.title='C1'; saveState(); }")
    a.wait(1700)
    print("  after the throwing write: badge=", a.badge()["warn"], " disk=", title_on_disk(a, "E.nse.json"))
    a.js("()=>{ window.__DIR.__st.faults.write=null; }")
    a.js("()=>{ state.meeting.title='C2'; saveState(); }")
    a.wait(1800)
    print("  after recovery:", title_on_disk(a, "E.nse.json"), a.badge())
    ok(title_on_disk(a, "E.nse.json") == "C2", "the chain keeps working after a rejected write")
    print("  writeSeq:", a.js("()=>writeSeq"))

head("T13f — reattachFile seeding lastWritten from an UNREADABLE file")
with App() as a:
    setup(a, "Bad.nse.json", "B0")
    files = {n: a.dir_get(n) for n in a.dir_list()}
    files["Bad.nse.json"] = "{ this is not json at all"      # corrupted between sessions
    a.reload_with_folder(files)
    print("  attached:", repr(a.open_file_name()), " badge:", a.badge())
    print("  baseline:", repr(a.js("()=>getBaseline(fileHandle)")[:60]))
    print("  app title (from localStorage):", a.js("()=>state.meeting.title"))
    a.js("()=>{ state.meeting.title='repairing the file'; saveState(); }")
    a.wait(1900)
    print("  disk after typing:", title_on_disk(a, "Bad.nse.json"), " badge:", a.badge())
    ok(title_on_disk(a, "Bad.nse.json") == "repairing the file",
       "a corrupt file on disk is repaired by the next autosave")

head("T13g — flushFileSave on pagehide: is the write even started?")
with App() as a:
    setup(a, "Hide.nse.json", "H0")
    a.js("()=>{ window.__DIR.__st.latency.getFile = 0; window.__FSLOG=[]; }")
    a.js("""()=>{ const d=window.__DIR; const q=d.queryPermission.bind(d);
        d.queryPermission = async function(){ await new Promise(r=>setTimeout(r,120)); return q(); }; }""")
    a.js("()=>{ state.meeting.title='LAST EDIT BEFORE CLOSE'; saveState(); }")
    a.wait(150)
    a.js("()=>{ window.__T0 = performance.now(); window.dispatchEvent(new Event('pagehide')); }")
    imm = a.js("()=>window.__FSLOG.filter(e=>e.ev==='createWritable').length")
    print("  writes started synchronously with pagehide:", imm)
    a.wait(1200)
    started = a.js("()=>window.__FSLOG.filter(e=>e.ev==='createWritable').map(e=>Math.round(e.t-window.__T0))")
    print("  createWritable started at +%s ms after pagehide" % started)
    print("  disk:", title_on_disk(a, "Hide.nse.json"))
    ok(imm > 0, "the final flush write starts synchronously with pagehide")

head("T13h — two autosave reads per keystroke: how much latency on 200 segments?")
with App() as a:
    a.attach_folder()
    a.install_idb_stub()
    a.js("""()=>{ while(state.segments.length < 200){
        const s = JSON.parse(JSON.stringify(state.segments[5]));
        s.id='big'+state.segments.length; state.segments.push(s); } }""")
    a.save_direct("Big.nse.json")
    a.wait(1200)
    res = a.js("""async ()=>{
        const t0 = performance.now();
        for(let i=0;i<5;i++){
            const g0 = performance.now();
            const seen = await (await fileHandle.getFile()).text();
            const g1 = performance.now();
            await writeHandle(fileHandle, meetingPayload());
            const g2 = performance.now();
            window.__last = [g1-g0, g2-g1];
        }
        return {payload: meetingPayload().length, guardRead: window.__last[0], write: window.__last[1],
                total: (performance.now()-t0)/5}; }""")
    print("  payload %d bytes | guard read %.1f ms | write+verify %.1f ms | total %.1f ms per autosave"
          % (res["payload"], res["guardRead"], res["write"], res["total"]))
    print("  (in-memory fake FS — a real folder adds the actual I/O on top of this,")
    print("   three round trips per keystroke: guard read, write, verify read)")
