"""Fast iteration probe: filled+LE only (the worst load), all six themes.

Reports spare mm on the two-page budget, plus a header-overflow check (the
banner is a fixed --print-head box with overflow:hidden, so trimming it can
silently clip the cadence line) and a per-block breakdown for one theme.

    python3 fast.py <file.html> [more.html ...]
"""
import asyncio, json, os, sys
from playwright.async_api import async_playwright

THEMES = ['classic', 'zine', 'swiss', 'brutalist', 'neomemphis']
PAGE_W = 718
PX_PER_MM = PAGE_W / 190.0
BUDGET_MM = (297 - 20) * 2

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

BLOCKS = """
() => {
  const q = s => document.querySelector(s);
  const h = e => e ? Math.round(e.getBoundingClientRect().height) : -1;
  const hdr = q('header');
  const rows = [...document.querySelectorAll('tbody tr')];
  return {
    header: h(hdr),
    headerScroll: hdr ? hdr.scrollHeight : -1,
    headerClip: hdr ? Math.max(0, hdr.scrollHeight - Math.round(hdr.getBoundingClientRect().height)) : -1,
    strip: h(q('.theme-strip')),
    thead: h(q('thead')),
    tbody: h(q('tbody')),
    nrows: rows.length,
    rowMin: Math.min(...rows.map(h)),
    rowMed: rows.map(h).sort((a, b) => a - b)[Math.floor(rows.length / 2)],
    total: h(q('.page')),
  };
}
"""


async def run(path):
    out, blocks = {}, {}
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={'width': PAGE_W, 'height': 1000})
        await ctx.route('http*://**', lambda route: asyncio.ensure_future(route.abort()))
        sheet = await ctx.new_page()
        page = await ctx.new_page()
        await page.goto('file://' + os.path.abspath(path), wait_until='domcontentloaded')
        await page.wait_for_timeout(600)
        await page.evaluate(FILL)
        await page.evaluate(LANGEVAL)
        for theme in THEMES:
            await page.evaluate("t => { state.theme = t; }", theme)
            html = await page.evaluate("() => buildSheetHTML(false)")
            await sheet.set_content(html, wait_until='load')
            await sheet.emulate_media(media='print')
            await sheet.wait_for_timeout(160)
            b = await sheet.evaluate(BLOCKS)
            blocks[theme] = b
            out[theme] = round(BUDGET_MM - b['total'] / PX_PER_MM, 1)
        await browser.close()
    return out, blocks


async def main():
    for f in sys.argv[1:]:
        out, blocks = await run(f)
        print(f)
        for k, v in out.items():
            print('  filled+LE/%-12s spare %7.1f mm   %s' % (k, v, json.dumps(blocks[k])))
        print(json.dumps(out))

asyncio.run(main())
