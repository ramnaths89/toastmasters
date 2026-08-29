"""Find what actually overhangs the viewport at desktop widths.

Open item 5 in the handover blames #dlBtn's tooltip and prescribes tip-right.
This measures instead of believing it: at each width, report documentElement
scrollWidth vs clientWidth, then walk every element (and its ::after/::before
boxes, which is where the tooltips live) and list whatever right edge exceeds
the client width.
"""
import asyncio, os, sys
from playwright.async_api import async_playwright

TARGET = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "/home/claude/psb/ProgSheetGenV35.html")
WIDTHS = [1920, 1600, 1440, 1366, 1280, 1100, 1000, 950]

JS = """
() => {
  const de = document.documentElement;
  const cw = de.clientWidth;
  const out = { scrollWidth: de.scrollWidth, clientWidth: cw, over: [] };
  const seen = new Set();
  document.querySelectorAll('*').forEach(el => {
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) return;
    if (r.right > cw + 0.5) {
      out.over.push({ kind:'element', tag: el.tagName.toLowerCase(),
        id: el.id || '', cls: el.className && el.className.baseVal === undefined ? String(el.className) : '',
        right: +r.right.toFixed(2), over: +(r.right - cw).toFixed(2) });
    }
    // pseudo boxes: measure by temporarily giving the pseudo a probe via getComputedStyle
    ['::after','::before'].forEach(p => {
      const cs = getComputedStyle(el, p);
      if (!cs || cs.content === 'none' || cs.display === 'none') return;
      const w = parseFloat(cs.width) || 0;
      if (!w) return;
      // reconstruct the pseudo's viewport box from the host box + its offsets
      const left = cs.left, right = cs.right, tf = cs.transform;
      let x0;
      if (left !== 'auto') x0 = r.left + parseFloat(left);
      else if (right !== 'auto') x0 = r.right - parseFloat(right) - w;
      else x0 = r.left;
      // apply translateX from the matrix if present
      if (tf && tf !== 'none') {
        const m = tf.match(/matrix\\(([^)]+)\\)/);
        if (m) x0 += parseFloat(m[1].split(',')[4]) || 0;
      }
      const rr = x0 + w;
      if (rr > cw + 0.5) {
        out.over.push({ kind:p, tag: el.tagName.toLowerCase(), id: el.id || '',
          cls: String(el.className || ''), width: +w.toFixed(2),
          right: +rr.toFixed(2), over: +(rr - cw).toFixed(2) });
      }
    });
  });
  out.over.sort((a,b)=> b.over - a.over);
  return out;
}
"""

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={"width": 1440, "height": 900})
        await ctx.route("http*://**", lambda r: asyncio.ensure_future(r.abort()))
        pg = await ctx.new_page()
        await pg.goto("file://" + TARGET)
        await pg.wait_for_timeout(900)
        print("TARGET:", TARGET)
        for w in WIDTHS:
            await pg.set_viewport_size({"width": w, "height": 900})
            await pg.wait_for_timeout(250)
            r = await pg.evaluate(JS)
            flag = "SCROLL" if r["scrollWidth"] > r["clientWidth"] else "ok    "
            print(f"\n[{flag}] width={w:5d}  scrollWidth={r['scrollWidth']}  clientWidth={r['clientWidth']}"
                  f"  delta={r['scrollWidth']-r['clientWidth']}")
            for o in r["over"][:8]:
                print("        ", o)
        await b.close()

asyncio.run(main())
