"""Where does the pane's height actually go? Per-block mm, classic, print media."""
import asyncio, os, sys
from playwright.async_api import async_playwright
import panefit as PF

MEAS = """
() => {
  const body = document.querySelector('.pane-body');
  const out = [];
  for (const el of body.children){
    const cs = getComputedStyle(el);
    out.push({c: el.className, h: el.getBoundingClientRect().height,
              mb: parseFloat(cs.marginBottom), n: el.querySelectorAll('.exco-item,.announce-line,div').length});
  }
  const h3 = body.querySelector('h3');
  const h3r = h3.getBoundingClientRect();
  const item = body.querySelector('.exco-item');
  return {blocks: out, h3h: h3r.height, itemh: item ? item.getBoundingClientRect().height : 0,
          paneBodyH: body.getBoundingClientRect().height};
}
"""

async def main():
    path = sys.argv[1]; load = sys.argv[2] if len(sys.argv)>2 else 'stress'
    script = dict(PF.LOADS)[load]
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={'width': PF.PAGE_W, 'height': PF.PAGE_H})
        await ctx.route('http*://**', lambda r: asyncio.ensure_future(r.abort()))
        sheet = await ctx.new_page(); await sheet.emulate_media(media='print')
        page = await ctx.new_page()
        await page.goto('file://'+os.path.abspath(path), wait_until='domcontentloaded')
        await page.wait_for_timeout(700)
        await page.evaluate(script)
        await page.evaluate("() => { state.theme='classic'; }")
        html = await page.evaluate("() => buildSheetHTML(false)")
        await sheet.set_content(html, wait_until='load')
        await sheet.emulate_media(media='print'); await sheet.wait_for_timeout(200)
        r = await sheet.evaluate(MEAS)
        M = PF.PX_PER_MM
        print('%s / %s   pane-body %.1f mm' % (path, load, r['paneBodyH']/M))
        tot=0
        for x in r['blocks']:
            print('  %-34s %6.1f mm  +mb %.1f' % (x['c'], x['h']/M, x['mb']/M))
            tot += x['h']/M + x['mb']/M
        print('  %-34s %6.1f mm' % ('TOTAL incl margins', tot))
        print('  h3 %.2f mm   exco-item %.2f mm' % (r['h3h']/M, r['itemh']/M))
        await b.close()
asyncio.run(main())
