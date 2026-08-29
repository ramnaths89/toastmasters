"""Where does the hidden-iframe measurement spend its time?"""
import asyncio, os, sys
from playwright.async_api import async_playwright
import panefit as PF

PROBE = """
async (stripFonts) => {
  const PX = 96/25.4; const t = {}; let t0 = performance.now();
  let html = buildSheetHTML(false);
  if (stripFonts) html = html.replace(/<link[^>]*fonts\\.(googleapis|gstatic)[^>]*>/g, '');
  t.build = performance.now()-t0; t0 = performance.now();
  const frame = document.createElement('iframe');
  frame.setAttribute('aria-hidden','true');
  frame.style.cssText='position:fixed;left:-10000px;top:0;border:0;visibility:hidden;width:'+(190*PX)+'px;height:'+(277*PX)+'px;';
  document.body.appendChild(frame);
  await new Promise((res,rej)=>{ frame.onload=res; frame.onerror=()=>rej(new Error('f')); frame.srcdoc = html; });
  t.frameLoad = performance.now()-t0; t0 = performance.now();
  const idoc = frame.contentDocument;
  for (const ss of idoc.styleSheets){ let R; try{R=ss.cssRules}catch(e){continue}
    for (const r of R) if(r.type===CSSRule.MEDIA_RULE && /print/.test(r.conditionText)) r.media.mediaText='all'; }
  t.flip = performance.now()-t0; t0 = performance.now();
  if (idoc.fonts && idoc.fonts.ready) await Promise.race([idoc.fonts.ready, new Promise(r=>setTimeout(r,4000))]);
  t.fonts = performance.now()-t0; t0 = performance.now();
  const aside = idoc.querySelector('aside.ref-pane');
  const last  = [...idoc.querySelector('.pane-body').children].pop();
  const over = (last.getBoundingClientRect().bottom - aside.getBoundingClientRect().bottom)/PX;
  t.measure = performance.now()-t0;
  frame.remove();
  return {t, over};
}
"""
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={'width': PF.PAGE_W, 'height': PF.PAGE_H})
        await ctx.route('http*://**', lambda r: asyncio.ensure_future(r.abort()))
        page = await ctx.new_page()
        await page.goto('file://'+os.path.abspath(sys.argv[1]), wait_until='domcontentloaded')
        await page.wait_for_timeout(700)
        await page.evaluate(dict(PF.LOADS)['stress'])
        for strip in (False, True):
            for i in range(3):
                r = await page.evaluate(PROBE, strip)
                t = r['t']
                print('  fonts-link %-7s run%d  build %.0f  frameLoad %6.0f  flip %.1f  fontsReady %6.0f  measure %.1f  = %6.0f ms   (over %+.2f mm)'
                      % ('KEPT' if not strip else 'STRIPPED', i, t['build'], t['frameLoad'], t['flip'], t['fonts'], t['measure'],
                         sum(t.values()), r['over']))
        await b.close()
asyncio.run(main())
