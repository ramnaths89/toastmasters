"""Two tabs of the builder open at once (file:// shares one localStorage)."""
from harness import App, head, ok
import json

head("T11 — a second tab silently clobbers the first tab's work")
with App() as a:
    a.js("()=>{ state.meeting.title='TAB ONE WORK'; state.roles.tmod='Alice'; saveState(); }")
    a.wait(600)
    p2 = a.ctx.new_page()
    p2.route("http*://**", lambda r: r.abort())
    p2.goto(a.build.as_uri(), wait_until="domcontentloaded", timeout=90000)
    p2.wait_for_timeout(1200)
    print("  tab2 restored title:", p2.evaluate("()=>state.meeting.title"))
    p2.evaluate("()=>{ state.meeting.title='TAB TWO WORK'; state.roles.tmod='Bob'; saveState(); }")
    p2.wait_for_timeout(600)
    # tab 1 knows nothing; one more keystroke there and tab 2's work is gone
    a.js("()=>{ state.meeting.footerNote='tab one keeps typing'; saveState(); }")
    a.wait(600)
    stored = a.js("()=>JSON.parse(localStorage.getItem('nse-programme-builder-v6')).state.meeting.title")
    print("  localStorage now holds:", stored)
    print("  tab1 shows:", a.js("()=>state.meeting.title"), "| tab2 shows:", p2.evaluate("()=>state.meeting.title"))
    ok(stored == "TAB TWO WORK", "the newest tab's work is what survives")
    p2.close()
