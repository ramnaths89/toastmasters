"""V36 end to end: the OneDrive scenarios the writeId, the last-good copy and the
advisory lock were built for.

Everything here drives the real save chain through the fake directory handle, so
the checks are about what lands on disk and what the badge says afterwards, not
about the helpers in isolation (those are pinned in tests/features/suite 12).

    python3 tests/json/t17_v36.py
"""
import json
import os
import pathlib

from harness import App, head, ok

BUILD = os.environ.get("PSB_BUILD") or os.environ.get("V36") or str(pathlib.Path(__file__).resolve().parents[2] / "ProgSheetGenV36.html")
FAILED = []


def check(cond, msg):
    if not ok(cond, msg):
        FAILED.append(msg)
    return cond


def payload(text):
    return json.loads(text)


head("T17 — V36 write provenance, recovery and the advisory lock")

# ---------------------------------------------------------------- writeId ----
with App(BUILD) as a:
    a.attach_folder()
    a.js("()=>{ state.meeting.title='One'; }")
    a.save_direct("W.nse.json"); a.wait(400)
    first = payload(a.dir_get("W.nse.json"))
    check(first["writeId"] == 1, "writeId starts at 1 on a fresh file (got %r)" % first.get("writeId"))
    check(isinstance(first.get("writer"), str) and first["writer"].startswith("tab-"),
          "the payload names the writing tab")
    check(first["v"] == 36, "PAYLOAD_VERSION is 36 (got %r)" % first.get("v"))

    a.js("()=>{ state.meeting.title='Two'; saveState(); }"); a.wait(1800)
    second = payload(a.dir_get("W.nse.json"))
    check(second["writeId"] == 2, "the autosave advances it (got %r)" % second.get("writeId"))
    check(second["writer"] == first["writer"], "same tab, same writer id")

    # A meeting whose TEXT contains the field must not derail the stamp.
    a.js("""()=>{ state.announcementsText = 'the "writeId": 999 field'; saveState(); }""")
    a.wait(1800)
    third = payload(a.dir_get("W.nse.json"))
    check(third["writeId"] == 3, "hostile announcement text does not misstamp (got %r)" % third.get("writeId"))
    check('"writeId": 999' in third["state"]["announcementsText"], "and the text survives intact")

# ------------------------------------------------- a failed write burns its id
with App(BUILD) as a:
    a.attach_folder()
    a.save_direct("B.nse.json"); a.wait(400)
    check(payload(a.dir_get("B.nse.json"))["writeId"] == 1, "id 1 landed")
    # Truncate the next commit so writeHandle's read-back rejects it.
    a.js("()=>{ window.__DIR.__st.afterClose = (n,t)=> t.slice(0, 40); }")
    a.js("()=>{ state.meeting.title='Doomed'; saveState(); }"); a.wait(1800)
    a.js("()=>{ window.__DIR.__st.afterClose = null; }")
    a.js("()=>{ state.meeting.title='Recovered'; saveState(); }"); a.wait(2200)
    txt = a.dir_get("B.nse.json")
    got = payload(txt)["writeId"]
    check(got >= 3, "the failed write burned its number, so the next one is >= 3 (got %r)" % got)

# ------------------------------------------ our own write, arriving late -----
# OneDrive pauses mid-commit: the write throws, resyncBaseline captures the torn
# text, the sync finishes and the disk holds OUR bytes. V35 called that "changed
# outside this tab" and refused every autosave for the rest of the session.
with App(BUILD) as a:
    a.attach_folder()
    a.js("()=>{ state.meeting.title='Live'; }")
    a.save_direct("L.nse.json"); a.wait(400)
    verdict = a.js("""()=>{
      const name = 'L.nse.json';
      const body = window.__DIR.__get(name);
      const meta = JSON.parse(body);
      /* Pretend the id we can see was allocated but never verified. */
      writeIdByFile[name] = meta.writeId - 1;
      writeIdNext[name]   = meta.writeId;
      baseline[name] = 'the torn bytes the failed write left behind';
      return classifyDisk(body, name);
    }""")
    check(verdict == "ours-late", "our own late write is recognised (got %r)" % verdict)
    before = a.dir_get("L.nse.json")
    a.js("()=>{ state.meeting.title='Typed after the stall'; saveState(); }")
    a.wait(2200)
    after = a.dir_get("L.nse.json")
    badge = a.badge()
    check(after != before, "the autosave PROCEEDS instead of jamming")
    check(payload(after)["state"]["meeting"]["title"] == "Typed after the stall",
          "and the edit is what landed")
    check(badge["warn"] is False, "no sticky warning left behind (badge %r)" % badge)

# ------------------------------------------------------- a genuine rollback --
with App(BUILD) as a:
    a.attach_folder()
    a.js("()=>{ state.meeting.title='Good Meeting'; }")
    a.save_direct("R.nse.json"); a.wait(400)
    a.js("()=>{ state.meeting.title='Good Meeting v2'; saveState(); }"); a.wait(1800)
    good = a.dir_get("R.nse.json")
    # A sync agent puts an older copy back.
    old = json.loads(good)
    old["writeId"] = 1
    old["state"]["meeting"]["title"] = "An Older Copy"
    a.dir_set("R.nse.json", json.dumps(old, indent=2))
    a.js("()=>{ state.meeting.title='Still typing'; saveState(); }"); a.wait(2200)
    on_disk = a.dir_get("R.nse.json")
    bar = a.js("""()=>{ const el=document.getElementById('recoverBar');
        return {hidden: el.hidden, text: el.textContent}; }""")
    check(json.loads(on_disk)["state"]["meeting"]["title"] == "An Older Copy",
          "the rolled-back file is NOT overwritten")
    check(bar["hidden"] is False, "the recovery bar is offered")
    check("BACKWARDS" in bar["text"], "and it says what happened: %r" % bar["text"][:90])
    check(a.badge()["warn"] is True, "the badge warns too")

    # Restoring puts the good meeting back on screen and writes it out.
    a.js("()=>acceptRecovery()"); a.wait(2600)
    check(a.js("()=>state.meeting.title") == "Good Meeting v2",
          "restore brings back the last verified copy")
    check(json.loads(a.dir_get("R.nse.json"))["state"]["meeting"]["title"] == "Good Meeting v2",
          "and it is written back to the file")
    undo = a.js("""()=>{ const el=document.getElementById('recoverBar');
        return {hidden: el.hidden, text: el.textContent}; }""")
    check(undo["hidden"] is False and "put back" in undo["text"].lower(),
          "a real way back is offered, not a sentence about Undo: %r" % undo["text"][:90])

# ---------------------------------------------- a damaged file, then repair --
with App(BUILD) as a:
    a.attach_folder()
    a.js("()=>{ state.meeting.title='Intact'; }")
    a.save_direct("D.nse.json"); a.wait(400)
    a.dir_set("D.nse.json", '{"app":"nse-programme-sheet", "v":36, "state": {trunca')
    a.js("()=>{ state.meeting.title='typing on'; saveState(); }"); a.wait(2200)
    bar = a.js("()=>document.getElementById('recoverBar').hidden")
    check(bar is False, "a torn file raises the bar")
    check('{"app":"nse-programme-sheet", "v":36, "state": {trunca' == a.dir_get("D.nse.json"),
          "and nothing is written over it")
    # Dismissing must stick across the next autosave tick.
    a.js("()=>dismissRecovery()")
    a.js("()=>{ state.meeting.title='typing on more'; saveState(); }"); a.wait(2200)
    check(a.js("()=>document.getElementById('recoverBar').hidden") is True,
          "'Leave it' survives the next autosave debounce")

# -------------------------------------------- the offer retires when it heals
with App(BUILD) as a:
    a.attach_folder()
    a.save_direct("H.nse.json"); a.wait(400)
    a.dir_set("H.nse.json", "{ torn")
    a.js("()=>{ state.meeting.title='one'; saveState(); }"); a.wait(2200)
    check(a.js("()=>document.getElementById('recoverBar').hidden") is False, "bar raised")
    # The sync completes and the file is readable again, matching our baseline.
    a.js("()=>{ const n='H.nse.json'; window.__DIR.__set(n, getBaselineByName(n) || window.__DIR.__get(n)); }")
    a.js("()=>{ const n='H.nse.json'; window.__DIR.__set(n, baseline[n]); }")
    a.js("()=>{ state.meeting.title='two'; saveState(); }"); a.wait(2400)
    check(a.js("()=>document.getElementById('recoverBar').hidden") is True,
          "a healed file takes the bar down, so no stale 'discard my work' button")

# ------------------------------------------------------------ the lock -------
with App(BUILD) as a:
    a.attach_folder()
    a.save_direct("K.nse.json"); a.wait(400)
    st = a.js("""()=>({key: lockedKey, name: lockedName,
        stored: JSON.parse(localStorage.getItem(lockedKey) || 'null')})""")
    check(st["name"] == "K.nse.json", "the lock is claimed on attach")
    check(st["stored"] and st["stored"]["tab"], "and written to localStorage")
    check("/" in st["key"], "the key names the folder as well as the file: %r" % st["key"])

    # A heartbeat from another tab must warn ONCE, not once every five seconds.
    fired = a.js("""()=>{
      let n = 0;
      const real = showBanner;
      window.showBanner = function(m, w){ if(/Another tab/.test(m)) n++; return real.apply(this, arguments); };
      for (let i = 0; i < 6; i++){
        window.dispatchEvent(Object.assign(new Event('storage'), {
          key: lockedKey, newValue: JSON.stringify({tab:'tab-theother', at: Date.now()})}));
      }
      window.showBanner = real;
      return n;
    }""")
    check(fired == 1, "six heartbeats from one other tab raise the alarm once (got %r)" % fired)

    # A DIFFERENT tab is news again.
    fired2 = a.js("""()=>{
      let n = 0;
      const real = showBanner;
      window.showBanner = function(m, w){ if(/Another tab/.test(m)) n++; return real.apply(this, arguments); };
      window.dispatchEvent(Object.assign(new Event('storage'), {
        key: lockedKey, newValue: JSON.stringify({tab:'tab-athird', at: Date.now()})}));
      window.showBanner = real;
      return n;
    }""")
    check(fired2 == 1, "a third tab is news again (got %r)" % fired2)

    # Detaching gives the claim back.
    a.js("()=>detachFile()"); a.wait(200)
    check(a.js("()=>lockedName") == "", "detach releases the claim")

# --------------------------------------------- Save As leaves nothing behind -
with App(BUILD) as a:
    a.attach_folder()
    a.js("()=>{ state.meeting.title='Original'; }")
    a.save_direct("S1.nse.json"); a.wait(400)
    # Damage S1 so an offer is standing, then Save As to S2.
    a.dir_set("S1.nse.json", "{ torn")
    a.js("()=>{ state.meeting.title='Original edited'; saveState(); }"); a.wait(2200)
    check(a.js("()=>document.getElementById('recoverBar').hidden") is False, "offer standing on S1")
    a.js("()=>{ fileHandle = null; releaseLock(); hideRecovery(); recoverDeclined=''; }")
    a.save_direct("S2.nse.json"); a.wait(600)
    check(a.js("()=>document.getElementById('recoverBar').hidden") is True,
          "the offer about S1 does not follow us to S2")
    a.js("()=>{ state.meeting.title='Now editing S2'; saveState(); }"); a.wait(2200)
    check(json.loads(a.dir_get("S2.nse.json"))["state"]["meeting"]["title"] == "Now editing S2",
          "S2 holds the meeting that is actually on screen")
    check(a.dir_get("S1.nse.json") == "{ torn", "S1 is left exactly as it was")

print("\n" + "=" * 78)
if FAILED:
    print("T17: %d FAILED" % len(FAILED))
    for f in FAILED:
        print("   -", f)
else:
    print("T17: all checks passed")
print("=" * 78)
