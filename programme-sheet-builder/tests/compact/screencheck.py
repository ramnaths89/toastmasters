"""Screen-layout guard.

Every edit here is meant to live inside @media print. The image/PDF exports
rasterise the SCREEN layout, so this renders the same sheet in SCREEN media and
records the height of the page and of a few blocks the print edits touch. Two
builds must agree exactly.

    python3 screencheck.py <a.html> <b.html>
"""
import asyncio, json, os, sys
from playwright.async_api import async_playwright

THEMES = ['classic', 'zine', 'swiss', 'brutalist', 'neomemphis']
FILL = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'h.py')).read()
FILL = FILL.split('FILL = """')[1].split('"""')[0]
LANGEVAL = """
() => {
  state.roleActive.langeval = true;
  state.roles.langeval = 'Language Evaluator Name';
  syncLanguageEvaluatorSegment();
  syncRoleSegments();
}
"""
PROBE = """
() => {
  const h = s => { const e = document.querySelector(s);
    return e ? Math.round(e.getBoundingClientRect().height * 100) / 100 : -1; };
  return [h('.page'), h('header'), h('thead'), h('tbody'),
          h('tbody tr'), h('.poetts'), h('.theme-strip')];
}
"""


async def run(path):
    out = {}
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={'width': 1100, 'height': 1000})
        await ctx.route('http*://**', lambda r: asyncio.ensure_future(r.abort()))
        ctx.set_default_navigation_timeout(180000)
        sheet = await ctx.new_page()
        page = await ctx.new_page()
        await page.goto('file://' + os.path.abspath(path), wait_until='domcontentloaded')
        await page.wait_for_timeout(600)
        await page.evaluate(FILL)
        await page.evaluate(LANGEVAL)
        for t in THEMES:
            await page.evaluate("t => { state.theme = t; }", t)
            html = await page.evaluate("() => buildSheetHTML(false)")
            await sheet.set_content(html, wait_until='load')
            await sheet.emulate_media(media='screen')
            await sheet.wait_for_timeout(150)
            out[t] = await sheet.evaluate(PROBE)
        await b.close()
    return out


async def main():
    a, bfile = sys.argv[1], sys.argv[2]
    ra, rb = await run(a), await run(bfile)
    same = ra == rb
    for t in THEMES:
        print('%-12s %s %s %s' % (t, ra[t], rb[t], '' if ra[t] == rb[t] else '<-- DIFFERS'))
    print('screen layout identical:', same)
    sys.exit(0 if same else 1)

asyncio.run(main())
