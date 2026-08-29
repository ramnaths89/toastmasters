"""Page-count probe.

The sheet sits about 4 mm from the two-page boundary, so any change that adds a
line has tipped themes onto a third page before. This renders the CLEAN sheet
(the same buildSheetHTML(false) the exports use) at the print page-box width and
counts PDF pages, for every theme, for a blank template and a filled one.

It is run against two builds and the counts compared, so the check is a
regression test rather than a claim about absolute layout accuracy: headless
print-to-PDF is not a real print preview.

    python3 tests/pgprobe.py <file.html> [more.html ...]
"""
import asyncio, json, os, subprocess, sys, tempfile
from playwright.async_api import async_playwright

THEMES = ['classic', 'zine', 'swiss', 'brutalist', 'neomemphis']
PAGE_W = 718          # 190 mm at 96 dpi: A4 minus the sheet's own 1 cm margins

FILL = """
() => {
  const m = state.meeting;
  m.title = 'Chapter Meeting: Voices of a Nation';
  m.dateDisplay = 'Thursday, 13 August 2026';
  Object.keys(state.roles).forEach((k, i) => { state.roles[k] = 'Member Name ' + (i + 1); });
  state.announcementsText = 'Club anniversary dinner, 20 Sept\\nArea contest briefing after the meeting';
  const sp = state.segments.filter(s => s.isSpeech);
  sp.forEach((s, i) => {
    s.speakerName = 'Speaker Name ' + (i + 1);
    s.speechTitle = 'A Speech Title That Runs Reasonably Long';
    s.pathway = 'DL'; s.pLevel = '1'; s.project = 'Ice Breaker';
  });
  state.segments.filter(s => s.isEvaluation).forEach((s, i) => {
    s.holderOverride = 'Evaluator Name ' + (i + 1);
    s.speakerName = 'Speaker Name ' + (i + 1);
  });
}
"""


async def counts_for(path):
    out = {}
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={'width': PAGE_W, 'height': 1000})
        page = await ctx.new_page()
        await page.goto('file://' + os.path.abspath(path))
        await page.wait_for_timeout(700)
        for filled in (False, True):
            if filled:
                await page.evaluate(FILL)
            for theme in THEMES:
                await page.evaluate("t => { state.theme = t; }", theme)
                html = await page.evaluate("() => buildSheetHTML(false)")
                sheet = await ctx.new_page()
                await sheet.set_viewport_size({'width': PAGE_W, 'height': 1000})
                await sheet.set_content(html, wait_until='load')
                await sheet.emulate_media(media='print')
                await sheet.wait_for_timeout(220)
                fd, pdf = tempfile.mkstemp(suffix='.pdf')
                os.close(fd)
                await sheet.pdf(path=pdf, format='A4', print_background=True,
                                margin={'top': '0', 'bottom': '0', 'left': '0', 'right': '0'})
                await sheet.close()
                info = subprocess.run(['pdfinfo', pdf], capture_output=True, text=True).stdout
                n = next((int(l.split(':')[1]) for l in info.splitlines()
                          if l.startswith('Pages:')), -1)
                os.unlink(pdf)
                out[('filled' if filled else 'blank') + '/' + theme] = n
        await browser.close()
    return out


async def main():
    files = sys.argv[1:]
    if not files:
        sys.exit(__doc__)
    results = {}
    for f in files:
        results[f] = await counts_for(f)
        print(f, json.dumps(results[f]))
    if len(files) > 1:
        base, *rest = files
        bad = 0
        for f in rest:
            for k, v in results[f].items():
                if results[base][k] != v:
                    print('REGRESSION %s %s: %s -> %s' % (f, k, results[base][k], v))
                    bad += 1
        print('page-count regressions:', bad)
        sys.exit(1 if bad else 0)

asyncio.run(main())
