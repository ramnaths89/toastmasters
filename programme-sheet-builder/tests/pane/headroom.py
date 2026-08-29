"""How much spare paper is left at the foot of the LAST printed page?

pgprobe answers "does it fit in 2 pages", which is a yes/no a change can pass while
sitting a millimetre from the edge. This answers "by how much", per theme, so
compaction can be aimed at the tightest theme instead of applied blind - and so a
later change can be shown to have BOUGHT headroom rather than merely not lost a page.

Measures the print layout the same way panefit does: buildSheetHTML(false) rendered
in PRINT media into a viewport that is the exact A4 page box.

    python3 tests/pane/headroom.py <file.html> [more.html ...]
"""
import asyncio, os, sys
from playwright.async_api import async_playwright
import panefit as PF

MEASURE = """
() => {
  const page = document.querySelector('.page');
  const main = document.querySelector('main');
  const table = document.querySelector('table');
  const aside = document.querySelector('aside.ref-pane');
  const foot = document.querySelector('footer');
  const body = document.querySelector('.pane-body');
  const pr = page.getBoundingClientRect();
  const last = body && body.children.length ? body.children[body.children.length-1] : null;
  return {
    contentH: Math.max(table ? table.getBoundingClientRect().bottom - pr.top : 0,
                       main ? main.getBoundingClientRect().bottom - pr.top : 0),
    pageH: pr.height,
    footH: foot ? foot.getBoundingClientRect().height : 0,
    paneOver: (aside && last)
      ? last.getBoundingClientRect().bottom - aside.getBoundingClientRect().bottom : null,
    rows: document.querySelectorAll('tbody tr').length,
  };
}
"""


async def main():
    paths = sys.argv[1:] or ["/home/claude/psb/ProgSheetGenV37.html"]
    M = PF.PX_PER_MM
    PAGE_MM = PF.PAGE_H_MM
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={"width": PF.PAGE_W, "height": PF.PAGE_H})
        await ctx.route("http*://**", lambda r: asyncio.ensure_future(r.abort()))
        sheet = await ctx.new_page()
        await sheet.emulate_media(media="print")
        for path in paths:
            print(f"\n=== {os.path.basename(path)}   (one page = {PAGE_MM} mm of content)")
            print(f"  {'load/theme':28s} {'rows':>5} {'agenda mm':>10} {'pages':>6} "
                  f"{'spare on last':>14} {'pane headroom':>14}")
            worst = None
            for lname, script in PF.LOADS:
                page = await ctx.new_page()
                await page.goto("file://" + os.path.abspath(path), wait_until="domcontentloaded")
                await page.wait_for_timeout(800)
                await page.evaluate(script)
                for theme in PF.THEMES:
                    await page.evaluate("t => { state.theme = t; }", theme)
                    html = await page.evaluate("() => buildSheetHTML(false)")
                    await sheet.set_content(html, wait_until="load")
                    await sheet.emulate_media(media="print")
                    await sheet.wait_for_timeout(160)
                    r = await sheet.evaluate(MEASURE)
                    mm = r["contentH"] / M
                    pages = max(1, int(mm // PAGE_MM) + (1 if mm % PAGE_MM else 0))
                    spare = pages * PAGE_MM - mm
                    pane = (-r["paneOver"] / M) if r["paneOver"] is not None else float("nan")
                    flag = "" if pages <= 2 else "   <-- 3 PAGES"
                    key = (pages, -spare)
                    if worst is None or key > worst[0]:
                        worst = (key, f"{lname}/{theme}", spare, pages)
                    print(f"  {lname + '/' + theme:28s} {r['rows']:>5} {mm:>10.1f} {pages:>6} "
                          f"{spare:>11.1f} mm {pane:>11.1f} mm{flag}")
                await page.close()
            print(f"  TIGHTEST: {worst[1]} - {worst[3]} pages, {worst[2]:.1f} mm spare")
        await b.close()

asyncio.run(main())
