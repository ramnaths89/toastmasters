"""meetingPayload() fidelity for exotic content, and filename handling."""
from harness import App, head, ok
import json

EXOTIC = {
    "newlines": "line one\nline two\r\nline three\ttabbed",
    "quotes": 'He said "yes" and \'no\'',
    "backslash": "C:\\Users\\Rama\\meeting\\file",
    "emoji": "Speech 🎤 by Rama 👏🏽 — 家族 ok",
    "rtl": "الاجتماع الأسبوعي — עברית",
    "script": "</script><script>alert(1)</script>",
    "combining": "e\u0301\u0301\u0301 zalgo",
    "nul": "before\u0000after",
    "lonesurrogate": "bad \ud800 end",
    "u2028": "para\u2028sep\u2029here",
    "bom": "\ufeffleading bom",
}

head("T08a — exotic strings survive a save/reopen byte for byte")
with App() as a:
    a.attach_folder()
    a.js("""(ex)=>{
        state.meeting.title = ex.emoji + ' ' + ex.rtl;
        state.meeting.location = ex.script;
        state.meeting.clubName = ex.quotes;
        state.meeting.footerNote = ex.backslash;
        state.announcementsText = Object.values(ex).join('\\n');
        state.segments[0].sub = ex.newlines;
        state.segments[1].speakerName = ex.lonesurrogate;
        state.segments[2].title = ex.u2028 + ex.nul;
        state.segments[3].speechTitle = ex.combining + ex.bom;
    }""", EXOTIC)
    before = a.state()
    a.save_direct("Exotic.nse.json")
    a.wait(500)
    raw = a.dir_get("Exotic.nse.json")
    try:
        json.loads(raw)
        print("  python json.loads: OK, %d bytes" % len(raw))
        parseok = True
    except Exception as e:
        print("  python json.loads FAILED:", e); parseok = False
    ok(parseok, "the written file is valid JSON to an outside reader")
    a.js("(t)=>applyMeetingText(t,'x')", raw)
    after = a.state()
    fields = [("meeting", "title"), ("meeting", "location"), ("meeting", "clubName"),
              ("meeting", "footerNote")]
    for grp, k in fields:
        same = before[grp][k] == after[grp][k]
        ok(same, "meeting.%s round-trips" % k)
        if not same:
            print("      before=%r\n      after =%r" % (before[grp][k], after[grp][k]))
    ok(before["announcementsText"] == after["announcementsText"], "announcementsText round-trips")
    for i in range(4):
        d = [k for k in before["segments"][i]
             if before["segments"][i][k] != after["segments"][i].get(k)]
        ok(not d, "segment[%d] round-trips (%s)" % (i, d))

head("T08b — a 50,000 character announcement and 200 segments")
with App() as a:
    a.attach_folder()
    info = a.js("""()=>{
        state.announcementsText = 'x'.repeat(50000);
        while(state.segments.length < 200){
          const s = JSON.parse(JSON.stringify(state.segments[5]));
          s.id = 'big' + state.segments.length;
          s.speakerName = 'Speaker ' + state.segments.length;
          state.segments.push(s);
        }
        return {segs: state.segments.length, ann: state.announcementsText.length};
    }""")
    print("  built:", info)
    a.save_direct("Big.nse.json")
    a.wait(1500)
    raw = a.dir_get("Big.nse.json")
    print("  file bytes:", len(raw) if raw else None)
    ok(raw is not None, "big meeting written")
    p = json.loads(raw)
    ok(len(p["state"]["segments"]) == 200, "200 segments on disk")
    ok(len(p["state"]["announcementsText"]) == 50000, "50k announcement intact")
    a.js("(t)=>applyMeetingText(t,'big')", raw)
    ok(a.js("()=>state.segments.length") == 200, "200 segments reload")
    print("  badge:", a.badge())

head("T08c — filenames")
with App() as a:
    a.attach_folder()
    a.js("()=>{ state.meeting.title='MEETING ONE — do not lose me'; }")
    a.save_direct("Clash.nse.json")
    a.wait(400)
    one = json.loads(a.dir_get("Clash.nse.json"))["state"]["meeting"]["title"]
    # a completely different meeting, saved As over the same name
    a.js("()=>{ fileHandle=null; state.meeting.title='MEETING TWO'; }")
    a.js("()=>{ confirmSaveDialogTest = 1; }")
    a.save_direct("Clash.nse.json")
    a.wait(400)
    now = json.loads(a.dir_get("Clash.nse.json"))["state"]["meeting"]["title"]
    print("  before=%r after=%r  files=%s" % (one, now, a.dir_list()))
    ok(now == one, "Save As onto an existing name does not silently overwrite it")

    for nm in ["CON", "PRN", "NUL", "aux", "COM1", "x" * 300, "Nse-Sheet", "NSE-SHEET",
               "  ....  ", "////", ".hidden", "a/b:c*d?e", "name.", "träumen 🎤"]:
        res = a.js("""(n)=>{ try{ return {stem: tidyStem(n), file: tidyFileName(n)}; }
                            catch(e){ return {err:String(e)}; } }""", nm)
        print("   %-14r -> %r" % (nm, res))
    a.js("()=>{ fileHandle=null; }")
    a.save_direct("CON.nse.json")
    a.wait(300)
    a.js("()=>{ fileHandle=null; }")
    a.save_direct(("y" * 300) + ".nse.json")
    a.wait(300)
    print("  folder:", [n[:40] + ("..." if len(n) > 40 else "") for n in a.dir_list()])
    print("  banners: n/a  badge:", a.badge())

head("T08d — case-only difference")
with App() as a:
    a.attach_folder()
    a.js("()=>{ state.meeting.title='lower'; }")
    a.save_direct("meeting.nse.json")
    a.wait(300)
    a.js("()=>{ fileHandle=null; state.meeting.title='UPPER'; }")
    a.save_direct("MEETING.nse.json")
    a.wait(300)
    print("  folder:", a.dir_list())
    print("  NOTE: the fake FS is case-SENSITIVE; a real Windows/macOS volume is not,")
    print("        so these two entries would be one file there.")
