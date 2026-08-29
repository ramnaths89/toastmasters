"""Page-count probe, extended with the Language Evaluator loads.

Same idea as tests/pgprobe.py — render buildSheetHTML(false) at the print
page-box width, print to PDF, count pages with pdfinfo — but over four loads
rather than two, because the extra 3-minute Language Evaluator row is the one
that tips the sheet onto a third page.

    python3 pg.py <file.html> [more.html ...]
"""
import asyncio, json, os, subprocess, sys, tempfile
from playwright.async_api import async_playwright

THEMES = ['classic', 'zine', 'swiss', 'brutalist', 'neomemphis']
PAGE_W = 718

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


async def counts_for(path):
    out = {}
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={'width': PAGE_W, 'height': 1000})
        await ctx.route('http*://**', lambda route: asyncio.ensure_future(route.abort()))
        ctx.set_default_navigation_timeout(180000)
        ctx.set_default_timeout(180000)
        sheet = await ctx.new_page()
        for load in ('blank', 'blank+LE', 'filled', 'filled+LE'):
            page = await ctx.new_page()
            await page.goto('file://' + os.path.abspath(path), wait_until='domcontentloaded')
            await page.wait_for_timeout(600)
            if load.startswith('filled'):
                await page.evaluate(FILL)
            if load.endswith('+LE'):
                await page.evaluate(LANGEVAL)
            for theme in THEMES:
                await page.evaluate("t => { state.theme = t; }", theme)
                html = await page.evaluate("() => buildSheetHTML(false)")
                await sheet.set_content(html, wait_until='load')
                await sheet.emulate_media(media='print')
                await sheet.wait_for_timeout(200)
                fd, pdf = tempfile.mkstemp(suffix='.pdf')
                os.close(fd)
                await sheet.pdf(path=pdf, format='A4', print_background=True,
                                margin={'top': '0', 'bottom': '0', 'left': '0', 'right': '0'})
                info = subprocess.run(['pdfinfo', pdf], capture_output=True, text=True).stdout
                n = next((int(l.split(':')[1]) for l in info.splitlines()
                          if l.startswith('Pages:')), -1)
                os.unlink(pdf)
                out[load + '/' + theme] = n
                print('   ', load, theme, n, flush=True)
            await page.close()
        await browser.close()
    return out


async def main():
    files = sys.argv[1:]
    if not files:
        sys.exit(__doc__)
    for f in files:
        r = await counts_for(f)
        print(f, json.dumps(r))
        bad = {k: v for k, v in r.items() if v != 2}
        print('  NOT-2-PAGES:', json.dumps(bad) if bad else 'none')

asyncio.run(main())
