"""Verify the six V35 fixes actually hold."""
from harness import App, head, ok
import json

head("T01 — do the six claimed fixes hold?")

# ---- fix 1: resetToDefaults detaches before replacing state -----------------
with App() as a:
    a.attach_folder()
    a.js("()=>{ state.meeting.title='Real Meeting'; state.roles.tmod='Rama'; }")
    a.save_direct("Real.nse.json")
    a.wait(300)
    before = a.dir_get("Real.nse.json")
    a.js("()=>resetToDefaults()")      # confirm() auto-accepted
    a.wait(200)
    ok(a.open_file_name() == "", "fix1: reset detaches the file (openFileName empty)")
    a.set_title("typing after reset")
    a.wait(1800)
    after = a.dir_get("Real.nse.json")
    ok(before == after, "fix1: post-reset keystrokes do NOT overwrite the saved meeting")
    p = json.loads(after)
    ok(p["state"]["roles"]["tmod"] == "Rama", "fix1: roster still on disk")

# ---- fix 2: queueFileSave refuses empty segments ---------------------------
with App() as a:
    a.attach_folder()
    a.js("()=>{ state.meeting.title='Has Segments'; }")
    a.save_direct("Seg.nse.json")
    a.wait(300)
    good = a.dir_get("Seg.nse.json")
    a.js("()=>{ state.segments = []; saveState(); }")
    a.wait(1800)
    ok(a.dir_get("Seg.nse.json") == good, "fix2: empty segments not autosaved over the file")
    print("       badge:", a.badge())
    # but does the MANUAL save refuse?
    a.save_direct()
    a.wait(400)
    now = json.loads(a.dir_get("Seg.nse.json"))
    ok(len(now["state"]["segments"]) > 0,
       "fix2b: manual Save also refuses to write an empty running order")

# ---- fix 3: writeHandle detects a short write ------------------------------
with App() as a:
    a.attach_folder({"afterClose": None})
    a.js("()=>{ window.__DIR.__st.afterClose = (n,t)=> t.slice(0, 50); }")
    a.js("()=>{ state.meeting.title='Truncated'; }")
    a.save_direct("Trunc.nse.json")
    a.wait(500)
    ok(len(a.dir_get("Trunc.nse.json")) == 50, "fix3: fake truncation applied")
    b = a.badge()
    print("       badge after truncated manual save:", b)
    ok(b["warn"] is True or "Could not save" in (b["title"] or ""),
       "fix3: truncated manual save surfaces as a warning")
    # now the autosave path
    a.js("()=>{ state.meeting.title='Truncated2'; saveState(); }")
    a.wait(1800)
    b2 = a.badge()
    print("       badge after truncated AUTOsave:", b2)
    ok(b2["warn"] is True, "fix3b: truncated autosave shows the warning glyph")

# ---- fix 4: flushFileSave on visibilitychange ------------------------------
with App() as a:
    a.attach_folder()
    a.js("()=>{ state.meeting.title='Before'; }")
    a.save_direct("Flush.nse.json")
    a.wait(300)
    a.js("()=>{ state.meeting.title='Last Edit Before Close'; saveState(); }")
    a.wait(100)   # inside the 1200ms debounce
    a.js("()=>{ Object.defineProperty(document,'hidden',{configurable:true,get:()=>true}); document.dispatchEvent(new Event('visibilitychange')); }")
    a.wait(400)
    p = json.loads(a.dir_get("Flush.nse.json"))
    ok(p["state"]["meeting"]["title"] == "Last Edit Before Close",
       "fix4: visibilitychange flushed the pending edit")

# ---- fix 5: adoptState sanitises ------------------------------------------
with App() as a:
    payload = {
        "app": "nse-programme-sheet", "v": 35,
        "state": {
            "meeting": {"title": "Dirty"},
            "segments": [
                "junk", 42, None,
                {"id": "s1", "presetKey": "speech", "durMin": "abc", "title": "A"},
                {"id": "s1", "presetKey": "no-such-preset", "durMin": -5, "title": "B"},
            ],
            "execText": {"nope": 1},
            "theme": 99, "paneWidth": 9999,
        },
    }
    a.js("(t)=>applyMeetingText(t,'dirty.json')", json.dumps(payload))
    s = a.state()
    ok(len(s["segments"]) == 2, "fix5: non-object segments dropped (got %d)" % len(s["segments"]))
    ok(s["segments"][1]["presetKey"] == "custom", "fix5: unknown presetKey -> custom")
    ok(s["segments"][0]["durMin"] == 0, "fix5: 'abc' durMin -> 0")
    ok(s["segments"][0]["id"] != s["segments"][1]["id"], "fix5: duplicate ids re-keyed")
    ok(isinstance(s["execText"], str), "fix5: execText forced to string")
    ok(s["theme"] == "classic", "fix5: numeric theme -> classic")
    ok(s["paneWidth"] == 80, "fix5: paneWidth clamped")
    print("       repairs:", a.js("()=>lastAdoptRepairs"))

# ---- fix 6: newer payload version warns ------------------------------------
with App() as a:
    a.js("""()=>{ window.__BANNERS=[]; const orig=showBanner;
        window.showBanner=function(m,w){ window.__BANNERS.push([m,!!w]); return orig(m,w); }; }""")
    fut = {"app": "nse-programme-sheet", "v": 99,
           "state": {"meeting": {"title": "From The Future"}, "segments": [{"id": "x", "presetKey": "speech"}]}}
    a.js("(t)=>applyMeetingText(t,'future.json')", json.dumps(fut))
    b = a.js("()=>window.__BANNERS")
    print("       banners:", b)
    ok(any("newer version" in m for m, w in b), "fix6: newer-version warning shown")
