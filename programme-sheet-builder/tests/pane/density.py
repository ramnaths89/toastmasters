"""Vertical density per pane block: printed height divided by rendered text lines.

An even column has roughly the same px-per-line in every block. A column that is
airy at the top and cramped at the bottom shows a falling gradient.
"""
import asyncio, os, sys
from playwright.async_api import async_playwright
import panefit as PF

MEAS = """
() => {
  const body = document.querySelector('.pane-body');
  const out = [];
  for (const blk of body.children){
    const r = blk.getBoundingClientRect();
    // count rendered LINE BOXES via Range client rects on every text node
    const tops = new Set();
    const walk = document.createTreeWalker(blk, NodeFilter.SHOW_TEXT);
    let n;
    while ((n = walk.nextNode())){
      if (!n.nodeValue.trim()) continue;
      const rg = document.createRange(); rg.selectNodeContents(n);
      for (const cr of rg.getClientRects()) tops.add(Math.round(cr.top * 2) / 2);
    }
    const lines = tops.size;
    const cs = getComputedStyle(blk);
    out.push({cls: blk.className.replace('exco-block','').trim() || 'exco',
              h: r.height + parseFloat(cs.marginBottom), lines});
  }
  return out;
}
"""

async def main():
    path = sys.argv[1]; theme = sys.argv[2] if len(sys.argv)>2 else 'classic'
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={'width': PF.PAGE_W, 'height': PF.PAGE_H})
        await ctx.route('http*://**', lambda r: asyncio.ensure_future(r.abort()))
        sheet = await ctx.new_page(); await sheet.emulate_media(media='print')
        pg = await ctx.new_page()
        await pg.goto('file://'+os.path.abspath(path), wait_until='domcontentloaded')
        await pg.wait_for_timeout(700)
        await pg.evaluate(dict(PF.LOADS)['full-night'])
        await pg.evaluate("t=>{state.theme=t;}", theme)
        html = await pg.evaluate("() => buildSheetHTML(false)")
        await sheet.set_content(html, wait_until='load')
        await sheet.emulate_media(media='print'); await sheet.wait_for_timeout(200)
        r = await sheet.evaluate(MEAS)
        print('  %-16s %8s %7s %11s' % ('block','height','lines','px per line'))
        for x in r:
            ppl = x['h']/x['lines'] if x['lines'] else 0
            print('  %-16s %7.1f %7d %10.2f' % (x['cls'][:16], x['h'], x['lines'], ppl))
        vals=[x['h']/x['lines'] for x in r if x['lines']]
        print('  spread: min %.2f  max %.2f  ratio %.2f' % (min(vals), max(vals), max(vals)/min(vals)))
        await b.close()
asyncio.run(main())
