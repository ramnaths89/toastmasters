"""Load each legacy fixture into V35 and diff every field, including keys whose
value became `undefined` (JSON.stringify would hide those)."""
from harness import App, head, ok
import json, pathlib

HERE = pathlib.Path(__file__).resolve().parent
FIX = HERE / "fixtures"

# JSON.stringify drops undefined properties, so mark them instead.
DUMP = """()=>JSON.stringify(state, (k,v)=> v===undefined ? '<<undefined>>' : v)"""


def diff(a, b, path=""):
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a: out.append((path + "." + k, "<absent>", b[k]))
            elif k not in b: out.append((path + "." + k, a[k], "<absent>"))
            else: out += diff(a[k], b[k], path + "." + k)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append((path + ".length", len(a), len(b)))
        for i in range(min(len(a), len(b))):
            out += diff(a[i], b[i], "%s[%d]" % (path, i))
    elif a != b:
        out.append((path, a, b))
    return out


head("T06 — legacy meetings loading in V35 (field by field)")
files = ["v29.nse.json", "v30.nse.json", "v31.nse.json", "v32.nse.json",
         "v33.nse.json", "v34.nse.json", "v35.nse.json"]
with App() as a:
    a.js("""()=>{ window.__BANNERS=[]; const orig=showBanner;
        showBanner=function(m,w){ window.__BANNERS.push([m,!!w]); return orig(m,w); }; }""")
    for fn in files:
        text = (FIX / fn).read_text()
        want = json.loads(text)["state"]
        a.js("()=>{ window.__BANNERS=[]; }")
        okload = a.js("(t)=>applyMeetingText(t,'fixture')", text)
        got = json.loads(a.js(DUMP))
        d = diff(want, got, "")
        print("\n  --- %s  loaded=%s  repairs=%s  banners=%s"
              % (fn, okload, a.js("()=>lastAdoptRepairs"), a.js("()=>window.__BANNERS")))
        if not d:
            print("      IDENTICAL — every field survived")
        for p, x, y in d:
            print("      %-40s file=%-30r loaded=%r" % (p, x, y))
        ok(okload, "%s loads" % fn)
        # the fields the owner called out
        for probe, label in [
            ("state.segments.length", "segments"),
            ("Object.keys(state.roles).length", "roles"),
            ("state.customRoles.length", "customRoles"),
            ("JSON.stringify(state.meeting.voting)", "voting"),
            ("state.segments.filter(s=>s.isSpeech).map(s=>[s.signalMin,s.signalMid,s.signalMax,s.signalSpan]).join('|')",
             "timing lights"),
        ]:
            print("        %-14s %s" % (label, a.js("()=>" + probe)))

head("T06b — round trip in V35: load, save, reopen, compare")
with App() as a:
    a.attach_folder()
    for fn in files:
        text = (FIX / fn).read_text()
        a.js("(t)=>applyMeetingText(t,'fixture')", text)
        s1 = json.loads(a.js(DUMP))
        a.js("()=>{ fileHandle=null; }")
        a.save_direct("rt-" + fn)
        a.wait(400)
        again = a.dir_get("rt-" + fn)
        a.js("(t)=>applyMeetingText(t,'rt')", again)
        s2 = json.loads(a.js(DUMP))
        d = diff(s1, s2, "")
        print("  %-16s round-trip diffs: %d" % (fn, len(d)))
        for p, x, y in d[:20]:
            print("      %-40s before=%-24r after=%r" % (p, x, y))
        ok(not d, "%s survives save->reopen unchanged" % fn)
