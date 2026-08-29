"""How close is the printed sheet to the two-page boundary?

Renders the clean sheet in PRINT media at the print page-box width and reports the
sheet height in mm against the two-page budget, for every theme and for four
loads: blank, blank + Language Evaluator, filled, filled + Language Evaluator.

Positive 'spare' means it still fits on two pages. Negative means page 3.

    python3 tests/heights.py <file.html> [more.html ...]
"""
import asyncio, json, os, sys
from playwright.async_api import async_playwright

THEMES = ['classic', 'zine', 'swiss', 'brutalist', 'neomemphis']
PAGE_W = 718                      # 190 mm content width at 96 dpi
PX_PER_MM = PAGE_W / 190.0
PAGE_H_MM = 297 - 20              # A4 less the sheet's own 1 cm top and bottom
BUDGET_MM = PAGE_H_MM * 2

FILL = """
() => {
  const m = state.meeting;
  m.title = 'Chapter Meeting: Voices of a Nation';
  m.dateDisplay = 'Thursday, 13 August 2026';
  Object.keys(state.roles).forEach((k, i) => { state.roles[k] = 'Member Name ' + (i + 1); });
  state.announcementsText = 'Club anniversary dinner, 20 Sept\\nArea contest briefing after the meeting';
  state.segments.filter(s => s.isSpeech).forEach((s, i) => {
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
LANGEVAL = """
() => {
  state.roleActive.langeval = true;
  state.roles.langeval = 'Language Evaluator Name';
  syncLanguageEvaluatorSegment();
  syncRoleSegments();
}
"""


async def heights_for(path):
    out = {}
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={'width': PAGE_W, 'height': 1000})
        await ctx.route('http*://**', lambda route: asyncio.ensure_future(route.abort()))
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
                await sheet.wait_for_timeout(160)
                px = await sheet.evaluate(
                    "() => document.querySelector('.page').getBoundingClientRect().height")
                mm = px / PX_PER_MM
                out[load + '/' + theme] = round(BUDGET_MM - mm, 1)
            await page.close()
        await browser.close()
    return out


async def main():
    for f in sys.argv[1:]:
        r = await heights_for(f)
        print(f)
        for k, v in r.items():
            flag = 'PAGE 3' if v < 0 else ''
            print('  %-24s spare %7.1f mm  %s' % (k, v, flag))
        print(json.dumps(r))

asyncio.run(main())
