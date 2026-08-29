"""Does the printed reference pane fit on ONE page?

The pane is position:fixed with overflow:hidden and bottom:var(--print-foot), so
it repeats identically on every printed page and anything past one page height is
silently CLIPPED - no page 3, no warning, the Announcements block just vanishes.

This renders buildSheetHTML(false) in PRINT media into a viewport sized to the
exact A4 page BOX (190 x 277 mm at 96 dpi, i.e. A4 less the sheet's own 1cm
margins), so position:fixed resolves against the same box the printer gives it.
It then measures the bottom of the LAST child of .pane-body against the bottom
edge of the aside.

    overflow > 0  -> that many mm are being cut off
    overflow < 0  -> that much headroom

    python3 tests/pane/panefit.py <file.html> [more.html ...]
"""
import asyncio, json, os, sys
from playwright.async_api import async_playwright

THEMES = ['classic', 'zine', 'swiss', 'brutalist', 'neomemphis']
PAGE_W = 718                       # 190 mm of A4 content width at 96 dpi
PX_PER_MM = PAGE_W / 190.0
PAGE_H_MM = 297 - 20               # A4 less the sheet's own 1 cm top and bottom
PAGE_H = round(PAGE_H_MM * PX_PER_MM)

ANN4 = ('Club anniversary dinner is on 20 September, Culinary Studio\\n'
        'Area contest briefing straight after the meeting tonight\\n'
        'Subscription renewals close on the last day of the month\\n'
        'Bring a guest in October and your next meal is on the club')
ANN6 = ANN4 + ('\\nCommittee handover rehearsal, Saturday 3pm in the annexe\\n'
               'Humorous Speech contest sign-up sheet is with the SAA tonight')

# The defaults, untouched: 8 Exco lines, 2 District Officers, 2 Links, no
# announcements. This is what the pane looks like straight out of a Reset.
DEFAULTS = "() => {}"

# A realistic full night: the roster filled, four announcement lines, and every
# prepared speech carrying a pathway/level/project.
FULL = """
() => {
  const m = state.meeting;
  m.title = 'Chapter Meeting: Voices of a Nation';
  m.dateDisplay = 'Thursday, 13 August 2026';
  Object.keys(state.roles).forEach((k, i) => { state.roles[k] = 'Member Name ' + (i + 1); });
  state.announcementsText = 'ANN4';
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
""".replace('ANN4', ANN4)

# Stress: a fifth speech, six announcements, and a venue address long enough to
# wrap twice in the banner.
STRESS = """
() => {
  const m = state.meeting;
  m.title = 'Chapter Meeting: Voices of a Nation, and Other Long Titles';
  m.dateDisplay = 'Thursday, 13 August 2026';
  m.location = 'Nee Soon East Community Club, 1 Yishun Avenue 9, #04-01 Culinary Studio, Nee Soon East Constituency, Singapore 768893 (enter via the Yishun Ave 9 side door)';
  setSpeechCount(5);
  Object.keys(state.roles).forEach((k, i) => { state.roles[k] = 'Member Name ' + (i + 1); });
  state.announcementsText = 'ANN6';
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
""".replace('ANN6', ANN6)

# What "sometimes slips beyond one page" actually looks like. Nothing exotic:
# the full D80 officer set instead of two, the four links a club actually hands
# out, and eight announcements - contest season, AGM season, dues season. Every
# one of these fields is free text the club edits, so none of it is capped.
HEAVY = """
() => {
  state.execText = [
    'President|Alex Tan',
    'VP Education|Jordan Lee',
    'VP Membership|Sam Ong',
    'VP Public Relations|<VP Public Relations Name>',
    'Secretary|<Secretary Name>',
    'Treasurer|Amir Hassan',
    'Sergeant at Arms|Amir Hassan',
    'Immediate Past President|Kim Wong'
  ].join('\\n');
  state.districtText = [
    'Division Director|<Division Director Name>|<Their Club>',
    'Area Director|Pat Chen|<Their Club>',
    'Club Growth Director|Priyanka Balasubramanian|District 80',
    'Program Quality Director|Wong Mei Ling|District 80'
  ].join('\\n');
  state.linksText = [
    'Toastmasters Intl.|https://www.toastmasters.org|www.toastmasters.org',
    'Our Club|https://www.facebook.com/groups/neesooneast|facebook.com/groups/neesooneast',
    'Pathways Portal|https://www.toastmasters.org/pathways|toastmasters.org/pathways',
    'District 80|https://www.d80toastmasters.org|d80toastmasters.org'
  ].join('\\n');
  state.announcementsText = 'ANN8';
  setSpeechCount(5);
  Object.keys(state.roles).forEach((k, i) => { state.roles[k] = 'Member Name ' + (i + 1); });
  state.segments.filter(s => s.isSpeech).forEach((s, i) => {
    s.speakerName = 'Speaker Name ' + (i + 1);
    s.speechTitle = 'A Speech Title That Runs Reasonably Long';
    s.pathway = 'DL'; s.pLevel = '1'; s.project = 'Ice Breaker';
  });
}
""".replace('ANN8', ANN6 + ('\\nAnnual General Meeting and officer handover is on 12 December\\n'
                            'Club Officer Training round two closes at the end of next week'))

LOADS = [('defaults', DEFAULTS), ('full-night', FULL), ('stress', STRESS), ('heavy', HEAVY)]

MEASURE = """
() => {
  const aside = document.querySelector('aside.ref-pane');
  const body  = document.querySelector('.pane-body');
  const kids  = Array.from(body.children);
  const last  = kids[kids.length - 1];
  const ar = aside.getBoundingClientRect();
  const lr = last.getBoundingClientRect();
  return {
    fixed:      getComputedStyle(aside).position,
    asideTop:   ar.top,
    asideH:     ar.height,
    asideScroll: aside.scrollHeight,
    asideClient: aside.clientHeight,
    lastClass:  last.className,
    lastBottom: lr.bottom,
    asideBottom: ar.bottom,
    overflowPx: lr.bottom - ar.bottom,
  };
}
"""


async def fits_for(path):
    out = {}
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={'width': PAGE_W, 'height': PAGE_H})
        await ctx.route('http*://**', lambda route: asyncio.ensure_future(route.abort()))
        sheet = await ctx.new_page()
        await sheet.emulate_media(media='print')
        for lname, script in LOADS:
            page = await ctx.new_page()
            await page.goto('file://' + os.path.abspath(path), wait_until='domcontentloaded')
            await page.wait_for_timeout(700)
            await page.evaluate(script)
            for theme in THEMES:
                await page.evaluate("t => { state.theme = t; }", theme)
                html = await page.evaluate("() => buildSheetHTML(false)")
                await sheet.set_content(html, wait_until='load')
                await sheet.emulate_media(media='print')
                await sheet.wait_for_timeout(180)
                r = await sheet.evaluate(MEASURE)
                assert r['fixed'] == 'fixed', 'pane not fixed in print: ' + r['fixed']
                out[lname + '/' + theme] = {
                    'overflow_mm': round(r['overflowPx'] / PX_PER_MM, 1),
                    'aside_mm': round(r['asideH'] / PX_PER_MM, 1),
                    'scroll_mm': round(r['asideScroll'] / PX_PER_MM, 1),
                    'client_mm': round(r['asideClient'] / PX_PER_MM, 1),
                    'last': r['lastClass'],
                }
            await page.close()
        await browser.close()
    return out


async def main():
    files = sys.argv[1:]
    if not files:
        sys.exit(__doc__)
    allr = {}
    for f in files:
        r = await fits_for(f)
        allr[f] = r
        print('==', f)
        print('  %-26s %10s %10s  %s' % ('load/theme', 'over mm', 'scroll mm', 'last block'))
        for k, v in r.items():
            flag = 'CLIPPED' if v['overflow_mm'] > 0 else 'ok  %+.1f mm headroom' % (-v['overflow_mm'])
            print('  %-26s %10.1f %10.1f  %-16s %s'
                  % (k, v['overflow_mm'], v['scroll_mm'], v['last'], flag))
        print('  pane box: %.1f mm' % list(r.values())[0]['client_mm'])
    print(json.dumps({f: {k: v['overflow_mm'] for k, v in r.items()} for f, r in allr.items()}))

if __name__ == '__main__':
    asyncio.run(main())
