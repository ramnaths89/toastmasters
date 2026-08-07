"""Combined theme regression: DOM geometry + real-PDF checks, in parallel.

Replaces geo.py + panecheck.py. Three things make it fast:
  1. All 18 sheet variants are generated in TWO evaluate() round-trips instead
     of 18 - buildSheetHTML() is a pure function of state, so there is nothing
     to wait for after setting the theme.
  2. Renders run concurrently across N Chromium pages in ONE browser, instead
     of sequentially.
  3. Each sheet is loaded ONCE and yields both the DOM metrics and the PDF;
     the old scripts opened every sheet twice and regenerated them again.
All the fixed wait_for_timeout() sleeps are gone - they were dead time.
"""
import os
APP = "file://" + os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "index.html"))
import asyncio, os, subprocess, re, sys, time, json
from playwright.async_api import async_playwright

FILL   = open("fill_snippet.js").read()
ANN    = "\n".join(f"Announcement {i} - filler so the pane is tall." for i in range(1,7))
PT_MM  = 72/25.4
HEAD_MM, MARGIN_MM, PANE_MM, PAGE_W_PT = 33, 10, 45.6, 595.28
PAGEBOX_PX = 718  # A4 content width (190mm @96dpi). Real Chrome print lays out at THIS width,
                  # not the emulated viewport - see the pagebox probe in main().
CONC   = int(os.environ.get("CONC", "8"))

GEN = """(keys) => {
  const out = {};
  for (const k of keys) { state.theme = k; out[k] = buildSheetHTML(false); }
  return out;
}"""

def pdf_boxes(pdf, page):
    out = subprocess.run(["pdftotext","-bbox","-f",str(page),"-l",str(page),pdf,"-"],
                         capture_output=True, text=True).stdout
    return re.findall(r'xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">([^<]*)<', out)

def find(pdf, page, word):
    hits=[(float(x),float(y)) for x,y,_,_,w in pdf_boxes(pdf,page) if w.strip().upper()==word]
    return min(hits, key=lambda t:t[1]) if hits else None

def pane_top(pdf, page, pane_right):
    """Topmost text inside the pane column, found GEOMETRICALLY.

    This used to hunt for the literal word "EXECUTIVE". Handmade renders pane
    headings in small-caps, which the renderer emits as several text runs
    ("E" + "xecutive" at two sizes), so the exact-word match found nothing and
    two real checks failed on a theme that was fine. Position is what these
    checks are actually about, and it holds for any theme's typography."""
    ys=[float(y) for x,y,_,_,w in pdf_boxes(pdf,page)
        if w.strip() and float(x) < pane_right - 4]
    return min(ys) if ys else None

def pdf_pages(pdf):
    return int(subprocess.run(["pdfinfo",pdf],capture_output=True,text=True)
               .stdout.split("Pages:")[1].split()[0])

async def check_one(browser, sem, variant, key, html):
    async with sem:
        f = f"ca_{variant}_{key}.html"; open(f,"w").write(html)
        url = "file://" + os.path.abspath(f)
        PROBE = """()=>{
              const h=document.querySelector('header').getBoundingClientRect();
              const a=document.querySelector('aside').getBoundingClientRect();
              const t=document.querySelector('.head-text');
              const brand=document.querySelector('aside .pane-brand');
              const cs=getComputedStyle(document.querySelector('aside'));
              const inner=[...t.children].reduce((y,el)=>Math.max(y,el.getBoundingClientRect().bottom),0);
              return {tLeft:t.getBoundingClientRect().left, aTop:a.top, aWidth:a.width,
                      brandTop: brand ? brand.getBoundingClientRect().top : null,
                      brandH: brand ? brand.getBoundingClientRect().height : null,
                      brandBot: brand ? brand.getBoundingClientRect().bottom : null,
                      asideBorderTop: parseFloat(cs.borderTopWidth)||0,
                      hTop:h.top, hBot:h.bottom,
                      contentBot: inner, hClipBot: h.bottom};
            }"""
        pg = await browser.new_page()
        try:
            await pg.goto(url)
            await pg.emulate_media(media="print")
            await pg.set_viewport_size({"width":794,"height":1123})   # A4 sheet width at 96dpi
            m = await pg.evaluate(PROBE)
            # Real Chrome print lays out at the PAGE BOX width (190mm = 718px), not the
            # viewport. An unscoped width media query therefore fires on paper but not in
            # headless page.pdf(). Measuring at both widths and demanding they agree is what
            # catches that whole class of bug - it is how the V14-V19 grey line was found.
            await pg.set_viewport_size({"width":PAGEBOX_PX,"height":1123})
            mp = await pg.evaluate(PROBE)
            await pg.emulate_media(media=None)
            pdf = f[:-5] + ".pdf"
            await pg.pdf(path=pdf, format="A4", print_background=True)
        finally:
            await pg.close()

        pages = await asyncio.to_thread(pdf_pages, pdf)
        brand_bot  = (MARGIN_MM+HEAD_MM)*PT_MM
        pane_right = (MARGIN_MM + PANE_MM)*PT_MM
        e1 = await asyncio.to_thread(pane_top, pdf, 1, pane_right)
        e2 = await asyncio.to_thread(pane_top, pdf, 2, pane_right) if pages >= 2 else None
        club = await asyncio.to_thread(find, pdf, 1, "NEE")
        checks = {
            "2 pages":        pages == 2,
            "pane at top":    m["aTop"] <= 0.6,
            "brand flush":    m["brandTop"] is not None and m["brandTop"] <= 2,
            "brand=head":     m["brandH"] is not None and abs(m["brandH"] - HEAD_MM/25.4*96) <= 2,
            "banner indent":  m["tLeft"] >= m["aWidth"] - 0.6,
            "banner fits":    m["contentBot"] <= m["hClipBot"] + 0.6,
            "no p2 gap":      bool(e1 and e2 and abs(e1-e2) <= 2),
            "pane below brand": bool(e1 and e1 >= brand_bot - 6),
            "club right of pane": bool(club and club[0] >= pane_right - 4),
            # --- top band integrity, at BOTH the viewport and page-box widths ---
            "no pane top border":  m["asideBorderTop"] == 0 and mp["asideBorderTop"] == 0,
            "brand top = banner top": abs(m["brandTop"]-m["hTop"]) <= 0.6
                                      and abs(mp["brandTop"]-mp["hTop"]) <= 0.6,
            "brand bot = banner bot": abs(m["brandBot"]-m["hBot"]) <= 0.6
                                      and abs(mp["brandBot"]-mp["hBot"]) <= 0.6,
            "print width-invariant":  abs(m["brandTop"]-mp["brandTop"]) <= 0.6
                                      and abs(m["brandH"]-mp["brandH"]) <= 0.6,
        }
        bad = [n for n,v in checks.items() if not v]
        return (variant, key, bad, pages)

async def main():
    t0 = time.time()
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        pg = await browser.new_page()
        await pg.goto(APP)
        await pg.evaluate("localStorage.clear()")
        await pg.reload()
        await pg.wait_for_function("typeof buildSheetHTML === 'function' && !!state")
        keys = await pg.evaluate("THEMES.map(t=>t.key)")
        blank  = await pg.evaluate(GEN, keys)                       # 1 round-trip, 9 sheets
        await pg.evaluate(FILL)
        await pg.evaluate("t => bindText('announcementsText', t)", ANN)
        filled = await pg.evaluate(GEN, keys)                       # 1 round-trip, 9 sheets
        await pg.close()

        sem = asyncio.Semaphore(CONC)
        tasks = ([check_one(browser, sem, "blank", k, blank[k]) for k in keys]
               + [check_one(browser, sem, "filled", k, filled[k]) for k in keys])
        results = await asyncio.gather(*tasks)
        await browser.close()

    fails = [r for r in results if r[2]]
    for variant, key, bad, pages in sorted(results, key=lambda r:(r[0],r[1])):
        print(("PASS  " if not bad else "FAIL  ") + f"{variant:6s} {key:11s} pages={pages}"
              + ("" if not bad else "  <- " + ", ".join(bad)))
    print(f"\n{len(results)-len(fails)}/{len(results)} clean   ({time.time()-t0:.0f}s, concurrency {CONC})")
    return 1 if fails else 0
raise SystemExit(asyncio.run(main()))
