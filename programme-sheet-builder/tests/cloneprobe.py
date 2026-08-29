"""Compare the LIVE export iframe geometry with the geometry html2canvas sees in
its CLONE, for the elements that carry the pane's column rule.

    python3 tests/cloneprobe.py [file.html]
"""
import asyncio, json, os, sys
from playwright.async_api import async_playwright

TARGET = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "/home/claude/psb/ProgSheetGenV37.html")
RAMA = open("/tmp/rama.json").read()

PROBE = r"""
async () => {
  const out = {live: null, clone: null, fonts: null, err: null};
  const real = window.html2canvas;
  const dump = (doc, tag) => {
    const sel = ['.page','aside.ref-pane','.pane-brand','.pane-body','header','main','footer','table','.body-grid'];
    const o = {};
    const page = doc.querySelector('.page');
    const pr = page.getBoundingClientRect();
    for (const s of sel) {
      const e = doc.querySelector(s);
      if (!e) { o[s] = null; continue; }
      const r = e.getBoundingClientRect();
      const cs = doc.defaultView.getComputedStyle(e);
      o[s] = {L:+(r.left-pr.left).toFixed(2), R:+(r.right-pr.left).toFixed(2),
              T:+(r.top-pr.top).toFixed(2), B:+(r.bottom-pr.top).toFixed(2),
              w:+r.width.toFixed(2), h:+r.height.toFixed(2),
              br:cs.borderRightWidth, brc:cs.borderRightColor,
              bt:cs.borderTopWidth, btc:cs.borderTopColor,
              pos:cs.position, ov:cs.overflow, bg:cs.backgroundColor,
              zi:cs.zIndex, minh:cs.minHeight, hgt:cs.height, wid:cs.width,
              font:cs.fontFamily};
    }
    o['__doc'] = {w: doc.documentElement.clientWidth, h: doc.documentElement.clientHeight,
                  sw: doc.documentElement.scrollWidth, sh: doc.documentElement.scrollHeight,
                  sheets: doc.styleSheets.length,
                  ruleCounts: Array.from(doc.styleSheets).map(s=>{try{return s.cssRules.length}catch(e){return -1}})};
    return o;
  };
  window.html2canvas = async (el, opts) => {
    if (!out.live) out.live = dump(el.ownerDocument, 'live');
    const o2 = Object.assign({}, opts, {onclone: (doc, cloned) => {
      try { if (!out.clone) out.clone = dump(doc, 'clone'); }
      catch(e){ out.err = String(e); }
    }});
    return real(el, o2);
  };
  try { await renderSheetParts({paginate:true}); }
  catch(e){ out.err = String(e); }
  finally { window.html2canvas = real; }
  return out;
}
"""


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={"width": 1440, "height": 900})
        pg = await ctx.new_page()
        pg.on("pageerror", lambda e: print("PAGEERROR:", e))
        await pg.goto("file://" + TARGET)
        await pg.wait_for_function("() => typeof state !== 'undefined'", timeout=20000)
        await pg.wait_for_timeout(2000)
        await pg.evaluate("(t) => applyMeetingText(t, 'rama.json')", RAMA)
        await pg.wait_for_timeout(1500)
        out = await pg.evaluate(PROBE)
        for tag in ("live", "clone"):
            print("=====", tag)
            d = out[tag]
            if not d:
                print("  none"); continue
            for k, v in d.items():
                print(" ", k, json.dumps(v))
        print("err", out["err"])
        await b.close()

asyncio.run(main())
