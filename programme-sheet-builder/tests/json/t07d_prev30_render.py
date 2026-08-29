from harness import App, head, ok
import json, pathlib
FIX = pathlib.Path('/home/claude/psb/tests/json/fixtures')
head("T07d — what a pre-V30 file looks like on the printed sheet")
with App() as a:
    a.js("(t)=>applyMeetingText(t,'v29')", (FIX/"v29.nse.json").read_text())
    txt = a.js("()=>{const p=document.querySelector('#previewPane, .sheet, #sheet'); return (p||document.body).innerText;}")
    print("  'undefined' in sheet:", 'undefined' in txt)
    for line in txt.splitlines():
        if 'undefined' in line or 'District' in line or 'meet every' in line:
            print("   >", line[:120])
    a.attach_folder()
    a.save_direct("resaved29.nse.json")
    a.wait(400)
    out = json.loads(a.dir_get("resaved29.nse.json"))["state"]["meeting"]
    print("  meeting keys re-written to disk:", sorted(out.keys()))
    ok('cadence' in out and 'orgLine' in out and 'clubInitials' in out,
       "re-saving a pre-V30 file restores the club constants into the file")
