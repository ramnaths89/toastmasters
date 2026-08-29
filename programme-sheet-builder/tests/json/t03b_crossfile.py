"""T03d/e split out: cross-file races."""
from harness import App, head, ok
import json

BANNER_HOOK = """()=>{ window.__BANNERS=[]; const orig=showBanner;
  showBanner=function(m,w){ window.__BANNERS.push([m,!!w]); return orig(m,w); }; }"""


def title_on_disk(a, name):
    t = a.dir_get(name)
    return json.loads(t)["state"]["meeting"]["title"] if t else None


head("T03d — open file B while an edit to file A is still queued")
with App() as a:
    a.attach_folder()
    a.js("()=>{ state.meeting.title='MEETING A'; state.roles.tmod='Alice'; }")
    a.save_direct("A.nse.json")
    a.wait(400)
    a.js("()=>{ fileHandle=null; state.meeting.title='MEETING B'; state.roles.tmod='Bob'; }")
    a.save_direct("B.nse.json")
    a.wait(400)
    a.js("()=>pickMeetingFile('f:A.nse.json')")
    a.wait(500)
    print("  attached:", a.open_file_name(), "| title:", a.js("()=>state.meeting.title"))
    a.js("()=>{ state.meeting.title='MEETING A - important late edit'; saveState(); }")
    a.wait(200)
    a.js("()=>pickMeetingFile('f:B.nse.json')")
    a.wait(2500)
    print("  A on disk:", title_on_disk(a, "A.nse.json"))
    print("  B on disk:", title_on_disk(a, "B.nse.json"))
    print("  attached now:", a.open_file_name())
    print("  badge    :", a.badge())
    ok(title_on_disk(a, "A.nse.json") == "MEETING A - important late edit",
       "A kept the edit made just before switching away")
    ok(title_on_disk(a, "B.nse.json") == "MEETING B", "B not contaminated by A's payload")


head("T03d2 — same, but the switch happens while A's write is genuinely in flight")
with App() as a:
    a.attach_folder()
    a.js("()=>{ state.meeting.title='A0'; }")
    a.save_direct("A.nse.json")
    a.wait(400)
    a.js("()=>{ fileHandle=null; state.meeting.title='B0'; }")
    a.save_direct("B.nse.json")
    a.wait(400)
    a.js("()=>pickMeetingFile('f:A.nse.json')")
    a.wait(500)
    a.js("()=>{ window.__FSLOG=[]; window.__DIR.__st.latency.close=2500; }")
    a.js("()=>{ state.meeting.title='A-LATE'; saveState(); }")
    a.wait(1300)                                  # A's close in flight
    a.js("()=>{ window.__DIR.__st.latency.close=5; }")
    a.js("()=>pickMeetingFile('f:B.nse.json')")   # loads B, attaches B
    a.wait(500)
    a.js("()=>{ state.meeting.title='B-EDITED'; saveState(); }")
    a.wait(4000)
    print("  commits:", [(e["file"], e["marker"], e["t"]) for e in a.fslog() if e["ev"] == "close"])
    print("  A on disk:", title_on_disk(a, "A.nse.json"))
    print("  B on disk:", title_on_disk(a, "B.nse.json"))
    ok(title_on_disk(a, "B.nse.json") == "B-EDITED", "B holds B's newest content")
    ok(title_on_disk(a, "A.nse.json") == "A-LATE", "A holds A's newest content")


head("T03e — Save As while an autosave is pending (fileHandle nulled mid-flight)")
with App() as a:
    a.js(BANNER_HOOK)
    a.attach_folder()
    a.js("()=>{ state.meeting.title='ORIGINAL'; }")
    a.save_direct("Orig.nse.json")
    a.wait(400)
    a.js("()=>{ window.__DIR.__st.latency.getFileHandle = 2000; window.__BANNERS=[]; window.__FSLOG=[]; }")
    a.js("()=>{ state.meeting.title='EDIT DURING SAVE AS'; saveState(); }")
    a.wait(50)
    a.js("""()=>{ state.meeting.fileName='Copy'; fileHandle=null;
                  window.__saveAsP = saveMeetingDirect('Copy.nse.json'); }""")
    a.wait(5000)
    print("  files:", a.dir_list())
    print("  Orig :", title_on_disk(a, "Orig.nse.json"))
    print("  Copy :", title_on_disk(a, "Copy.nse.json"))
    print("  banners:", a.js("()=>window.__BANNERS"))
    print("  console errors:", [c for c in a.console if c.startswith("error")][-5:])
    print("  pageerrors:", a.pageerrors)
    print("  badge:", a.badge())
    ok(not a.pageerrors, "no unhandled error from the nulled fileHandle")
    ok(title_on_disk(a, "Orig.nse.json") == "ORIGINAL",
       "the original file is untouched by a Save As")
