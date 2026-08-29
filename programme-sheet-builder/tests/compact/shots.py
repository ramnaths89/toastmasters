"""Page images of the printed sheet, so the density change can be judged by eye.

Prints the sheet to PDF exactly as pgprobe does, then rasterises every page, so
what you look at is the real paginated output rather than a scrolled screenshot.

    python3 shots.py <file.html> <tag> [theme ...]
"""
import asyncio, os, subprocess, sys, tempfile
from playwright.async_api import async_playwright

PAGE_W = 718
OUT = os.path.dirname(os.path.abspath(__file__))

FILL = open(os.path.join(OUT, 'h.py')).read().split('FILL = """')[1].split('"""')[0]
LANGEVAL = """
() => {
  state.roleActive.langeval = true;
  state.roles.langeval = 'Language Evaluator Name';
  syncLanguageEvaluatorSegment();
  syncRoleSegments();
}
"""
THEMETEXT = "() => { state.meeting.theme = 'Bridges We Build'; }"


async def main():
    path, tag = sys.argv[1], sys.argv[2]
    themes = sys.argv[3:] or ['classic', 'zine']
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={'width': PAGE_W, 'height': 1000})
        await ctx.route('http*://**', lambda route: asyncio.ensure_future(route.abort()))
        ctx.set_default_navigation_timeout(180000)
        page = await ctx.new_page()
        await page.goto('file://' + os.path.abspath(path), wait_until='domcontentloaded')
        await page.wait_for_timeout(700)
        await page.evaluate(FILL)
        try:
            await page.evaluate(THEMETEXT)
        except Exception as e:
            print('theme text skipped:', e)
        await page.evaluate(LANGEVAL)
        sheet = await ctx.new_page()
        for theme in themes:
            await page.evaluate("t => { state.theme = t; }", theme)
            html = await page.evaluate("() => buildSheetHTML(false)")
            await sheet.set_content(html, wait_until='load')
            await sheet.emulate_media(media='print')
            await sheet.wait_for_timeout(250)
            fd, pdf = tempfile.mkstemp(suffix='.pdf')
            os.close(fd)
            await sheet.pdf(path=pdf, format='A4', print_background=True,
                            margin={'top': '0', 'bottom': '0', 'left': '0', 'right': '0'})
            info = subprocess.run(['pdfinfo', pdf], capture_output=True, text=True).stdout
            n = next((int(l.split(':')[1]) for l in info.splitlines() if l.startswith('Pages:')), -1)
            stem = os.path.join(OUT, 'shots', '%s-%s' % (tag, theme))
            os.makedirs(os.path.dirname(stem), exist_ok=True)
            subprocess.run(['pdftoppm', '-png', '-r', '110', pdf, stem], check=True)
            os.unlink(pdf)
            print(tag, theme, 'pages', n)
        await browser.close()

asyncio.run(main())
