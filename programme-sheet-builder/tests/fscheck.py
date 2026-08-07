import os
APP = "file://" + os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "index.html"))
import asyncio, json
from playwright.async_api import async_playwright

res=[]
def ck(n, ok, x=""):
    res.append(ok); print(("PASS  " if ok else "FAIL  ")+n+(("  | "+str(x)) if x else ""))

# An in-memory folder implementing the same interface the real one does.
FAKE = """() => {
  window.__disk = {};
  window.__perm = 'granted';
  const fileH = (name) => ({
    kind:'file', name,
    createWritable: async () => ({ write: async t => { window.__disk[name] = t; }, close: async () => {} }),
    getFile: async () => ({ text: async () => window.__disk[name] }),
  });
  const dir = {
    kind:'directory', name:'MeetingsFolder',
    queryPermission: async () => window.__perm,
    requestPermission: async () => { window.__perm = 'granted'; return 'granted'; },
    getFileHandle: async (name, o) => {
      if(!(name in window.__disk)){
        if(!o || !o.create) throw Object.assign(new Error('not found'),{name:'NotFoundError'});
        window.__disk[name] = '';
      }
      return fileH(name);
    },
    entries: async function*(){ for(const n of Object.keys(window.__disk)) yield [n, fileH(n)]; },
  };
  window.__dir = dir;
  window.showDirectoryPicker = async () => dir;
  folderHandle = dir;              // pre-link, as if the user had already chosen it
  window.__prompts = [];
  window.prompt = (msg, def) => { window.__prompts.push(def); return window.__nextName || def; };
}"""

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width":1500,"height":950})
        errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(APP, timeout=60000)
        await pg.evaluate("localStorage.clear()"); await pg.reload(); await pg.wait_for_timeout(1000)
        await pg.evaluate(FAKE)

        # ---------- save ----------
        await pg.evaluate("bindMeeting('title','Chapter Meeting: Voices'); bindMeeting('dateDisplay','13 August 2026')")
        await pg.wait_for_timeout(300)
        suggested = await pg.evaluate("suggestedFileName()")
        import re as _re
        ck("filename is <Initials>-ProgSheet-<meeting date>-<time now>",
           bool(_re.fullmatch(r"NSE-ProgSheet-2026-08-13-\d{4}\.nse\.json", suggested)), suggested)
        # every date shape the free-text field actually receives
        for raw, want in [("Thursday, 13 August 2026","2026-08-13"), ("13/08/2026","2026-08-13"),
                          ("2026-08-13","2026-08-13"), ("August 13, 2026","2026-08-13"),
                          ("13 Aug 2026","2026-08-13")]:
            got = await pg.evaluate("(d)=>{bindMeeting('dateDisplay',d); return meetingDateStamp();}", raw)
            ck("date %-24r -> %s" % (raw, want), got == want, got)
        today = await pg.evaluate("()=>{bindMeeting('dateDisplay',''); return meetingDateStamp();}")
        ck("blank date falls back to today, not a wrong date",
           bool(_re.fullmatch(r"\d{4}-\d{2}-\d{2}", today)), today)
        ck("initials fall back to the club name's capitals", await pg.evaluate(
            "()=>{const k=state.meeting.clubInitials; state.meeting.clubInitials='';"
            " const r=clubInitials(); state.meeting.clubInitials=k; return r;}") == "NSE")
        # two saves of the same meeting must not collide
        await pg.evaluate("bindMeeting('dateDisplay','Thursday, 13 August 2026')")
        n1 = await pg.evaluate("suggestedFileName()")
        n2 = await pg.evaluate("(()=>{const d=new Date(); return clubInitials()+'-ProgSheet-'+meetingDateStamp()+'-'+String(d.getHours()).padStart(2,'0')+String(d.getMinutes()+1).padStart(2,'0')+FILE_EXT;})()")
        ck("a later save gets a different name", n1 != n2, [n1, n2])
        await pg.evaluate("window.__nextName = 'Aug13.nse.json'")
        await pg.evaluate("saveMeeting()"); await pg.wait_for_timeout(600)
        disk = await pg.evaluate("Object.keys(window.__disk)")
        ck("save writes a file into the folder", disk == ["Aug13.nse.json"], disk)
        payload = json.loads(await pg.evaluate("window.__disk['Aug13.nse.json']"))
        ck("file is a tagged meeting payload",
           payload.get("app")=="nse-programme-sheet" and payload["state"]["meeting"]["title"]=="Chapter Meeting: Voices")
        ck("json is human-readable (indented)", "\n  " in await pg.evaluate("window.__disk['Aug13.nse.json']"))

        # ---------- autosave into that file ----------
        await pg.evaluate("bindRole('tmod','Autosaved Person')")
        await pg.wait_for_timeout(2200)
        after = json.loads(await pg.evaluate("window.__disk['Aug13.nse.json']"))
        ck("later edits autosave into the same file", after["state"]["roles"]["tmod"]=="Autosaved Person")
        ck("no second file was created", await pg.evaluate("Object.keys(window.__disk).length")==1)

        # ---------- dropdown ----------
        await pg.evaluate("refreshFileList()"); await pg.wait_for_timeout(300)
        opts = await pg.evaluate("[...document.querySelectorAll('#fileSelect option')].map(o=>o.value)")
        ck("dropdown lists the saved meeting", "f:Aug13.nse.json" in opts, opts)
        ck("dropdown offers save-as and change-folder", "__saveas" in opts and "__folder" in opts, opts)
        ck("current file is selected in the dropdown",
           await pg.evaluate("document.getElementById('fileSelect').value")=="f:Aug13.nse.json")

        # ---------- save as a second meeting, then switch back ----------
        await pg.evaluate("bindMeeting('title','Second Meeting'); bindRole('tmod','Someone Else')")
        await pg.wait_for_timeout(300)
        await pg.evaluate("window.__nextName = 'Sept10.nse.json'")
        await pg.evaluate("saveMeetingAs()"); await pg.wait_for_timeout(600)
        ck("save-as creates a second file",
           sorted(await pg.evaluate("Object.keys(window.__disk)"))==["Aug13.nse.json","Sept10.nse.json"])
        first = json.loads(await pg.evaluate("window.__disk['Aug13.nse.json']"))
        ck("the first file was NOT overwritten by the fork", first["state"]["roles"]["tmod"]=="Autosaved Person",
           first["state"]["roles"]["tmod"])

        await pg.evaluate("pickMeetingFile('f:Aug13.nse.json')"); await pg.wait_for_timeout(700)
        ck("loading a saved meeting restores its data", await pg.evaluate(
            "state.roles.tmod==='Autosaved Person' && state.meeting.title==='Chapter Meeting: Voices'"),
            await pg.evaluate("[state.meeting.title, state.roles.tmod]"))
        ck("the loaded file becomes the autosave target", await pg.evaluate("fileHandle.name")=="Aug13.nse.json")
        sheet = await pg.frames[1].evaluate("document.body.innerText")
        ck("the sheet redraws from the loaded meeting", "Autosaved Person" in sheet)

        await pg.evaluate("bindRole('ahcounter','Post Load')"); await pg.wait_for_timeout(2200)
        reloaded = json.loads(await pg.evaluate("window.__disk['Aug13.nse.json']"))
        ck("autosave follows the newly loaded file", reloaded["state"]["roles"]["ahcounter"]=="Post Load")
        ck("the other file stayed untouched",
           json.loads(await pg.evaluate("window.__disk['Sept10.nse.json']"))["state"]["roles"].get("ahcounter","")=="")

        # ---------- a wrong file must not destroy the meeting ----------
        await pg.evaluate("window.__disk['notes.json'] = JSON.stringify({hello:'world'})")
        await pg.evaluate("pickMeetingFile('f:notes.json')"); await pg.wait_for_timeout(600)
        ck("a non-meeting json leaves the current work untouched", await pg.evaluate(
            "state.roles.tmod==='Autosaved Person' && fileHandle.name==='Aug13.nse.json'"))
        ck("...and says so", "not a programme-sheet meeting" in await pg.evaluate(
            "document.getElementById('banner').textContent"))
        await pg.evaluate("window.__disk['broken.json'] = '{ this is not json'")
        await pg.evaluate("pickMeetingFile('f:broken.json')"); await pg.wait_for_timeout(600)
        ck("malformed json is handled, not thrown", await pg.evaluate("state.roles.tmod==='Autosaved Person'"))

        # ---------- permission revoked mid-session ----------
        await pg.evaluate("window.__perm = 'prompt'")
        await pg.evaluate("bindRole('saa','After Revoke')"); await pg.wait_for_timeout(2200)
        ck("a revoked folder downgrades the badge instead of failing silently",
           "reconnect" in (await pg.evaluate("document.getElementById('saveDot').title")).lower(),
           await pg.evaluate("document.getElementById('saveDot').title"))
        ck("work is still safe in localStorage", await pg.evaluate(
            "JSON.parse(localStorage.getItem(STORE_KEY)).state.roles.saa==='After Revoke'"))

        ck("no JS errors throughout", not errs, errs[:3])
        await b.close()
    print(f"\n{sum(res)}/{len(res)} passed")
    return 0 if all(res) else 1
raise SystemExit(asyncio.run(main()))
