"""FEASIBILITY ONLY - can the PRINT pane height be measured from a live, screen-media page?

Nothing here is proposed for the app. This exists to turn "I think a hidden iframe
would work" into a measured accuracy figure, by computing the pane overflow two ways
and differencing them:

  ground truth : panefit.py's method - emulate_media(media='print'), page-box viewport
  candidate    : NO print emulation anywhere. A hidden iframe sized to the print page
                 box, srcdoc = buildSheetHTML(false), with every @media print rule in
                 the sheet's own stylesheet flipped to media='all' via CSSOM.

If the candidate reproduces ground truth, a builder warning is achievable.
"""
import asyncio, os, sys
from playwright.async_api import async_playwright
import panefit as PF

# The candidate, written as it would be written in the app. Runs on the LIVE page.
CANDIDATE = """
async () => {
  const PX_PER_MM = 96 / 25.4;
  const BOX_W = 190 * PX_PER_MM;      // A4 content width  (210 - 2x10mm margin)
  const BOX_H = 277 * PX_PER_MM;      // A4 content height (297 - 2x10mm margin)

  const frame = document.createElement('iframe');
  frame.setAttribute('aria-hidden', 'true');
  frame.style.cssText = 'position:fixed;left:-10000px;top:0;border:0;visibility:hidden;'
    + 'width:' + BOX_W + 'px;height:' + BOX_H + 'px;';
  document.body.appendChild(frame);
  await new Promise((res, rej) => {
    frame.onload = res; frame.onerror = () => rej(new Error('frame'));
    frame.srcdoc = buildSheetHTML(false);
  });
  const idoc = frame.contentDocument;

  // Force the sheet's OWN print rules to apply on screen. No re-declaration of
  // any value: the same CSSMediaRule objects, retargeted.
  let flipped = 0;
  for (const ss of idoc.styleSheets) {
    let rules; try { rules = ss.cssRules; } catch (e) { continue; }
    for (const r of rules) {
      if (r.type === CSSRule.MEDIA_RULE && /print/.test(r.conditionText)) {
        r.media.mediaText = 'all'; flipped++;
      }
    }
  }
  if (idoc.fonts && idoc.fonts.ready) {
    await Promise.race([idoc.fonts.ready, new Promise(r => setTimeout(r, 4000))]);
  }
  await new Promise(r => setTimeout(r, 120));

  const aside = idoc.querySelector('aside.ref-pane');
  const body  = idoc.querySelector('.pane-body');
  const kids  = Array.from(body.children);
  const last  = kids[kids.length - 1];
  const out = {
    flippedBlocks: flipped,
    position: idoc.defaultView.getComputedStyle(aside).position,
    asideH: aside.getBoundingClientRect().height,
    overflowPx: last.getBoundingClientRect().bottom - aside.getBoundingClientRect().bottom,
    pxPerMm: PX_PER_MM,
  };
  frame.remove();
  return out;
}
"""

TRUTH_VIEWPORT = {'width': PF.PAGE_W, 'height': PF.PAGE_H}


async def main():
    path = sys.argv[1]
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport=TRUTH_VIEWPORT)
        await ctx.route('http*://**', lambda r: asyncio.ensure_future(r.abort()))
        truth_sheet = await ctx.new_page()
        await truth_sheet.emulate_media(media='print')

        print('  %-26s %10s %10s %9s' % ('load/theme', 'truth mm', 'cand mm', 'delta mm'))
        worst = 0.0
        for lname, script in PF.LOADS:
            page = await ctx.new_page()          # live builder page: SCREEN media
            await page.goto('file://' + os.path.abspath(path), wait_until='domcontentloaded')
            await page.wait_for_timeout(700)
            await page.evaluate(script)
            for theme in PF.THEMES:
                await page.evaluate("t => { state.theme = t; }", theme)
                # --- candidate, measured from the live screen-media page
                c = await page.evaluate(CANDIDATE)
                cand = c['overflowPx'] / c['pxPerMm']
                # --- ground truth, via real print emulation
                html = await page.evaluate("() => buildSheetHTML(false)")
                await truth_sheet.set_content(html, wait_until='load')
                await truth_sheet.emulate_media(media='print')
                await truth_sheet.wait_for_timeout(180)
                t = await truth_sheet.evaluate(PF.MEASURE)
                truth = t['overflowPx'] / PF.PX_PER_MM
                d = cand - truth
                worst = max(worst, abs(d))
                print('  %-26s %10.2f %10.2f %9.2f%s'
                      % (lname + '/' + theme, truth, cand, d,
                         '' if abs(d) < 0.5 else '   <-- DISAGREES'))
            await page.close()
        print('  candidate media blocks flipped per run:', c['flippedBlocks'],
              ' pane position:', c['position'], ' pane box: %.1f mm' % (c['asideH']/c['pxPerMm']))
        print('  WORST |delta| = %.2f mm' % worst)
        await b.close()

asyncio.run(main())
