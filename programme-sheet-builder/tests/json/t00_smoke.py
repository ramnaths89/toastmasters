"""Smoke: does the app load, is FS_SUPPORTED true, are the globals reachable,
does a plain save land in the fake folder."""
from harness import App, head, ok
import json

head("T00 smoke")
with App() as a:
    print("  FS_SUPPORTED =", a.js("()=>FS_SUPPORTED"))
    print("  PAYLOAD_VERSION =", a.js("()=>PAYLOAD_VERSION"))
    print("  segments =", a.js("()=>state.segments.length"))
    print("  pageerrors:", a.pageerrors)
    a.attach_folder()
    a.js("()=>{ state.meeting.title='Smoke Test'; }")
    a.save_direct("Smoke.nse.json")
    a.wait(400)
    print("  files:", a.dir_list())
    txt = a.dir_get("Smoke.nse.json")
    ok(txt is not None, "file created")
    p = json.loads(txt)
    ok(p["app"] == "nse-programme-sheet", "app tag")
    ok(p["v"] == 36, "version 36")
    ok(p["state"]["meeting"]["title"] == "Smoke Test", "title round-trips")
    print("  openFileName:", a.open_file_name())
    print("  badge:", a.badge())
    # autosave path
    a.set_title("Second Edit")
    a.wait(1600)
    p2 = json.loads(a.dir_get("Smoke.nse.json"))
    ok(p2["state"]["meeting"]["title"] == "Second Edit", "autosave reached the file")
    print("  fslog:", a.fslog())
    print("  pageerrors:", a.pageerrors)
