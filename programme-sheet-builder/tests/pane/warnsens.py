"""Sensitivity + cost of the hidden-iframe measurement. Feasibility evidence only."""
import asyncio, os, sys
from playwright.async_api import async_playwright
import panefit as PF

PROBE = """
async ([boxWmm, boxHmm, footOverride]) => {
  const PX = 96 / 25.4;
  const t0 = performance.now();
  const frame = document.createElement('iframe');
  frame.setAttribute('aria-hidden','true');
  frame.style.cssText = 'position:fixed;left:-10000px;top:0;border:0;visibility:hidden;'
    + 'width:' + (boxWmm*PX) + 'px;height:' + (boxHmm*PX) + 'px;';
  document.body.appendChild(frame);
  await new Promise((res,rej)=>{ frame.onload=res; frame.onerror=()=>rej(new Error('f')); frame.srcdoc = buildSheetHTML(false); });
  const idoc = frame.contentDocument;
  for (const ss of idoc.styleSheets){
    let rules; try{ rules = ss.cssRules; }catch(e){ continue; }
    for (const r of rules) if (r.type === CSSRule.MEDIA_RULE && /print/.test(r.conditionText)) r.media.mediaText='all';
  }
  if (idoc.fonts && idoc.fonts.ready) await Promise.race([idoc.fonts.ready, new Promise(r=>setTimeout(r,4000))]);
  await new Promise(r=>setTimeout(r,120));
  const aside = idoc.querySelector('aside.ref-pane');
  const last  = [...idoc.querySelector('.pane-body').children].pop();
  const cs = idoc.defaultView.getComputedStyle(idoc.documentElement);
  const out = {
    ms: performance.now() - t0,
    foot: cs.getPropertyValue('--print-foot').trim(),
    head: cs.getPropertyValue('--print-head').trim(),
    paneW: cs.getPropertyValue('--print-pane').trim(),
    boxMm: aside.getBoundingClientRect().height / PX,
    overMm: (last.getBoundingClientRect().bottom - aside.getBoundingClientRect().bottom) / PX,
  };
  frame.remove();
  return out;
}
"""

CASES = [
    ('A4      190 x 277 mm', 190, 277),
    ('Letter  196 x 259.4mm', 196, 259.4),   # 216x279.4 less 10mm margins
    ('A4, driver forces 15mm margin', 180, 267),
]

async def main():
    path = sys.argv[1]
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={'width': PF.PAGE_W, 'height': PF.PAGE_H})
        await ctx.route('http*://**', lambda r: asyncio.ensure_future(r.abort()))
        page = await ctx.new_page()
        await page.goto('file://'+os.path.abspath(path), wait_until='domcontentloaded')
        await page.wait_for_timeout(700)
        for load in ('stress', 'heavy'):
            await page.evaluate(dict(PF.LOADS)[load])
            await page.evaluate("() => { state.theme='classic'; }")
            print(' ', load)
            for name, w, h in CASES:
                r = await page.evaluate(PROBE, [w, h, None])
                print('    %-32s box %6.1f mm   overflow %+7.2f mm   %4.0f ms'
                      % (name, r['boxMm'], r['overMm'], r['ms']))
            print('    CSS vars read from the sheet: --print-foot=%s --print-head=%s --print-pane=%s'
                  % (r['foot'], r['head'], r['paneW']))
        # cost of repeated runs (what a keystroke-triggered check would pay)
        ts = []
        for _ in range(5):
            r = await page.evaluate(PROBE, [190, 277, None]); ts.append(r['ms'])
        print('  repeat cost ms:', ' '.join('%.0f' % t for t in ts))
        await b.close()
asyncio.run(main())
