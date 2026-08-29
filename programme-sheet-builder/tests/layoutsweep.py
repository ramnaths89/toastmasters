"""Sweep the builder's width and report which layout is actually in force.

There are two independent breakpoints - a 980px block in the CSS that stacks the
panes into a column, and the 900px block (NARROW_PX) that hides the splitter and
brings up the Edit/Preview tabs. Between them the builder is in a state nobody
designed. This prints one row per width so the band is visible rather than argued
about.

    python3 tests/layoutsweep.py <file.html>
"""
import asyncio, os, sys
from playwright.async_api import async_playwright

TARGET = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "/home/claude/psb/ProgSheetGenV37.html")
WIDTHS = [1200, 1024, 1000, 981, 980, 960, 940, 920, 901, 900, 899, 860, 800, 700, 480, 400]

PROBE = """
() => {
  const cs = el => el ? getComputedStyle(el) : null;
  const body = document.querySelector('.builder-body');
  const form = document.querySelector('.form-pane');
  const prev = document.querySelector('.preview-pane');
  const spl  = document.getElementById('splitter');
  const tabs = document.querySelector('.view-tabs');
  const r = el => el ? el.getBoundingClientRect() : {width:0, height:0};
  return {
    disp:      cs(body).display,
    dir:       cs(body).flexDirection,
    splitter:  cs(spl).display,
    splitterW: Math.round(r(spl).width),
    splitterH: Math.round(r(spl).height),
    tabs:      cs(tabs).display,
    formW:     Math.round(r(form).width),
    formH:     Math.round(r(form).height),
    formBasis: form.style.flexBasis || '(none)',
    prevDisp:  cs(prev).display,
    prevW:     Math.round(r(prev).width),
    narrow:    isNarrow(),
    scroll:    document.documentElement.scrollWidth - document.documentElement.clientWidth,
  };
}
"""


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={"width": 1200, "height": 900})
        await ctx.route("http*://**", lambda r: asyncio.ensure_future(r.abort()))
        pg = await ctx.new_page()
        await pg.goto("file://" + TARGET)
        await pg.wait_for_function("() => typeof state !== 'undefined'", timeout=20000)
        await pg.wait_for_timeout(900)
        print(f"{'width':>6} {'display':>8} {'flex-dir':>9} {'splitter':>9} {'splW':>5} {'splH':>5} "
              f"{'tabs':>6} {'formW':>6} {'basis':>7} {'preview':>8} {'prevW':>6} "
              f"{'isNarrow':>9} {'hscroll':>8}   verdict")
        for w in WIDTHS:
            await pg.set_viewport_size({"width": w, "height": 900})
            await pg.wait_for_timeout(160)
            r = await pg.evaluate(PROBE)
            # flex-direction is meaningless on a display:block container - the
            # one-pane view stacks with display:block, and reading flexDirection
            # there reported "row" for a layout that is plainly a column.
            side_by_side = r["disp"] == "flex" and r["dir"] == "row"
            split_live = r["splitter"] != "none"
            tabs_live = r["tabs"] != "none"
            if side_by_side and split_live and not tabs_live:
                v = "ok - desktop split"
            elif not side_by_side and not split_live and tabs_live and r["prevDisp"] == "none":
                v = "ok - one pane + tabs"
            elif not side_by_side and split_live:
                v = "BROKEN - stacked, but the splitter is still there"
            else:
                v = "BROKEN - " + f"dir={r['dir']} split={r['splitter']} tabs={r['tabs']}"
            print(f"{w:>6} {r['disp']:>8} {r['dir']:>9} {r['splitter']:>9} {r['splitterW']:>5} {r['splitterH']:>5} "
                  f"{r['tabs']:>6} {r['formW']:>6} {r['formBasis']:>7} {r['prevDisp']:>8} "
                  f"{r['prevW']:>6} {str(r['narrow']):>9} {r['scroll']:>8}   {v}")
        await b.close()

asyncio.run(main())
