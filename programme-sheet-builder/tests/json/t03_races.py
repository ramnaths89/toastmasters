"""Ordering and cross-file races: does the LAST state always win, and does a
payload ever reach the wrong file?"""
from harness import App, head, ok
import json

BANNER_HOOK = """()=>{ window.__BANNERS=[]; const orig=showBanner;
  showBanner=function(m,w){ window.__BANNERS.push([m,!!w]); return orig(m,w); }; }"""


def title_on_disk(a, name):
    t = a.dir_get(name)
    return json.loads(t)["state"]["meeting"]["title"] if t else None


head("T03a — two autosaves in flight: can an OLDER payload land last?")
with App() as a:
    a.attach_folder()
    a.js("()=>{ state.meeting.title='V0'; }")
    a.save_direct("Race.nse.json")
    a.wait(300)
    a.js("()=>{ window.__FSLOG=[]; window.__DIR.__st.latency.close = 3000; }")
    a.js("()=>{ state.meeting.title='EDIT-1'; saveState(); }")   # commits at ~t+4200
    a.wait(1400)                                                 # its close() is in flight
    a.js("()=>{ window.__DIR.__st.latency.close = 10; }")
    a.js("()=>{ state.meeting.title='EDIT-2 (newest)'; saveState(); }")  # commits at ~t+2600
    a.wait(5000)
    final = title_on_disk(a, "Race.nse.json")
    print("  commit order:", [(e["ev"], e["marker"], e["t"]) for e in a.fslog() if e["ev"] == "close"])
    print("  final on disk:", final)
    print("  in the app   :", a.js("()=>state.meeting.title"))
    print("  badge        :", a.badge())
    ok(final == "EDIT-2 (newest)", "the newest edit is what ended up on disk")


head("T03b — same race with Chrome's per-file write lock")
with App() as a:
    a.attach_folder({"lock": True})
    a.js("()=>{ state.meeting.title='V0'; }")
    a.save_direct("Lock.nse.json")
    a.wait(300)
    a.js("()=>{ window.__FSLOG=[]; window.__DIR.__st.latency.close = 3000; }")
    a.js("()=>{ state.meeting.title='EDIT-1'; saveState(); }")
    a.wait(1400)
    a.js("()=>{ window.__DIR.__st.latency.close = 10; }")
    a.js("()=>{ state.meeting.title='EDIT-2 (newest)'; saveState(); }")
    a.wait(5000)
    print("  log:", [(e["ev"], e["marker"]) for e in a.fslog()])
    print("  final on disk:", title_on_disk(a, "Lock.nse.json"))
    print("  badge        :", a.badge())
    ok(title_on_disk(a, "Lock.nse.json") == "EDIT-2 (newest)", "locked case still ends newest")


head("T03c — manual Save landing on top of a queued autosave")
with App() as a:
    a.attach_folder()
    a.js("()=>{ state.meeting.title='V0'; }")
    a.save_direct("Man.nse.json")
    a.wait(300)
    a.js("()=>{ window.__FSLOG=[]; window.__DIR.__st.latency.close = 2500; }")
    a.js("()=>{ state.meeting.title='TYPED-A'; saveState(); }")
    a.wait(1300)                             # autosave's close in flight with TYPED-A
    a.js("()=>{ window.__DIR.__st.latency.close = 5; state.meeting.title='TYPED-B'; }")
    a.save_direct()                          # manual Save writes TYPED-B immediately
    a.wait(4000)
    print("  commits:", [(e["marker"], e["t"]) for e in a.fslog() if e["ev"] == "close"])
    print("  final on disk:", title_on_disk(a, "Man.nse.json"))
    print("  badge        :", a.badge())
    ok(title_on_disk(a, "Man.nse.json") == "TYPED-B",
       "manual Save's content survives the in-flight autosave")


head("T03d — open file B while an edit to file A is still queued")
with App() as a:
    a.attach_folder()
    a.js("()=>{ state.meeting.title='MEETING A'; state.roles.tmod='Alice'; }")
    a.save_direct("A.nse.json")
    a.wait(300)
    a.js("()=>{ fileHandle=null; state.meeting.title='MEETING B'; state.roles.tmod='Bob'; }")
    a.save_direct("B.nse.json")
    a.wait(300)
    # reopen A, edit it, then jump to B inside the 1200ms debounce
    a.js("(v)=>pickMeetingFile('f:A.nse.json')")
    a.wait(400)
    print("  attached:", a.open_file_name(), "title:", a.js("()=>state.meeting.title"))
    a.js("()=>{ state.meeting.title='MEETING A — important late edit'; saveState(); }")
    a.wait(200)                              # well inside the debounce
    a.js("()=>pickMeetingFile('f:B.nse.json')")
    a.wait(2500)
    print("  A on disk:", title_on_disk(a, "A.nse.json"))
    print("  B on disk:", title_on_disk(a, "B.nse.json"))
    print("  badge    :", a.badge())
    ok(title_on_disk(a, "A.nse.json") == "MEETING A — important late edit",
       "A kept the edit made just before switching away")
    ok(title_on_disk(a, "B.nse.json") == "MEETING B", "B was not contaminated by A's payload")


head("T03e — Save As while an autosave is pending (fileHandle nulled mid-flight)")
with App() as a:
    a.js(BANNER_HOOK)
    a.attach_folder()
    a.js("()=>{ state.meeting.title='ORIGINAL'; }")
    a.save_direct("Orig.nse.json")
    a.wait(300)
    # make getFileHandle slow so the Save As create straddles the queued autosave
    a.js("()=>{ window.__DIR.__st.latency.getFileHandle = 2000; window.__BANNERS=[]; }")
    a.js("()=>{ state.meeting.title='EDIT DURING SAVE AS'; saveState(); }")
    a.wait(50)
    a.js("""()=>{ /* what confirmSaveDialog does for Save As */
        state.meeting.fileName='Copy'; fileHandle=null; saveMeetingDirect('Copy.nse.json'); }""")
    a.wait(4000)
    print("  files:", a.dir_list())
    print("  Orig :", title_on_disk(a, "Orig.nse.json"))
    print("  Copy :", title_on_disk(a, "Copy.nse.json"))
    print("  banners:", a.js("()=>window.__BANNERS"))
    print("  pageerrors:", a.pageerrors)
    print("  badge:", a.badge())
    ok(not a.pageerrors, "no unhandled error from the nulled fileHandle")
