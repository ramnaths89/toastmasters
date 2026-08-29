"""Page-count probe for the V43 CONTEST sheet.

pgprobe.py covers the chapter meeting. A contest is a different document with a
different failure mode: two contest blocks each carrying a numbered list, and a
club that fields ten contestants in both adds twenty lines to a sheet that sits
about 4 mm from the two-page boundary to begin with.

Four fills, worst case last:
  empty   - the shipped template, no contestants entered yet
  typical - 6 + 6, which is what a club contest actually looks like
  full    - 10 + 10, the Toastmasters maximum per contest
  brutal  - 10 + 10 with long names, every appointment filled and three
            announcements, i.e. nothing left to grow

Run against one build; it reports counts and fails only if the TYPICAL case
needs more than two pages. Full and brutal are reported, not asserted: a contest
with twenty contestants legitimately needs a third page, and pretending
otherwise would mean compacting the one list on the sheet that people read a
name at a time.

    python3 tests/pgcontest.py <file.html>
"""
import asyncio, json, os, subprocess, sys, tempfile
from playwright.async_api import async_playwright

THEMES = ['classic', 'zine', 'swiss', 'brutalist', 'neomemphis']
PAGE_W = 718          # 190 mm at 96 dpi: A4 minus the sheet's own 1 cm margins

BASE = """
() => {
  setMeetingMode('contest');
  const m = state.meeting;
  m.title = 'Table Topics & Evaluations Contest';
  m.dateDisplay = 'Thursday, 24 September 2026';
}
"""

def fill(n1, n2, long_names=False, everything=False):
    name = ("Contestant With A Fairly Long Name " if long_names else "Name ")
    return """
    (a) => {
      const [n1, n2, nm, every] = a;
      const blocks = state.segments.filter(s => s.isContestants);
      blocks[0].contestants = Array.from({length:n1}, (_,i)=> nm + (i+1));
      if(blocks[1]) blocks[1].contestants = Array.from({length:n2}, (_,i)=> nm + (i+1));
      if(every){
        Object.keys(CONTEST_ROLE_LABELS).forEach((k,i)=>{
          state.roles[k] = 'Appointment Holder Name ' + (i+1);
        });
        state.announcementsText =
          'Area contest briefing for all contestants at 6:30 PM\\n'
          + 'Division contest is on 8 October, same venue\\n'
          + 'Certificates are collected from the Contest Chair after the results';
      }
    }
    """, [n1, n2, name, everything]


CASES = [
    ('empty',   fill(0, 0)),
    ('typical', fill(6, 6)),
    ('full',    fill(10, 10)),
    ('brutal',  fill(10, 10, long_names=True, everything=True)),
]


async def counts_for(path):
    out = {}
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={'width': PAGE_W, 'height': 1000})
        for label, (js, args) in CASES:
            page = await ctx.new_page()
            await page.goto('file://' + os.path.abspath(path))
            await page.wait_for_timeout(700)
            await page.evaluate(BASE)
            await page.wait_for_timeout(250)
            await page.evaluate(js, args)
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
                out[label + '/' + theme] = n
            await page.close()
        await browser.close()
    return out


async def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    res = await counts_for(sys.argv[1])
    for label, _ in CASES:
        row = {t: res[label + '/' + t] for t in THEMES}
        print(f"{label:8s} {json.dumps(row)}")
    bad = [k for k, v in res.items() if k.startswith(('empty', 'typical')) and v > 2]
    print('over two pages in the asserted cases:', bad if bad else 'none')
    sys.exit(1 if bad else 0)

asyncio.run(main())
