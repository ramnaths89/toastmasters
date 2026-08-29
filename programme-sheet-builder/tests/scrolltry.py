"""Try candidate fixes for the horizontal scroll live in the page and measure."""
import asyncio, os, sys
from playwright.async_api import async_playwright

TARGET = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "/home/claude/psb/ProgSheetGenV35.html")
WIDTHS = [1920, 1600, 1440, 1366, 1280, 1100, 1000, 950, 899, 700, 420]

TRIALS = [
    ("baseline", []),
    ("dlBtn tip-right", ["#dlBtn"]),
    ("dlBtn + saveBtn tip-right", ["#dlBtn", "#saveBtn"]),
]

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={"width": 1440, "height": 900})
        await ctx.route("http*://**", lambda r: asyncio.ensure_future(r.abort()))
        pg = await ctx.new_page()
        await pg.goto("file://" + TARGET)
        await pg.wait_for_timeout(900)
        for label, sels in TRIALS:
            await pg.evaluate(
                "sels => { document.querySelectorAll('.btn').forEach(b=>b.classList.remove('__t'));"
                "  document.querySelectorAll('#dlBtn,#saveBtn').forEach(b=>b.classList.remove('tip-right'));"
                "  sels.forEach(s => { const e = document.querySelector(s); if(e) e.classList.add('tip-right'); }); }",
                sels)
            row = []
            for w in WIDTHS:
                await pg.set_viewport_size({"width": w, "height": 900})
                await pg.wait_for_timeout(120)
                d = await pg.evaluate("() => document.documentElement.scrollWidth - document.documentElement.clientWidth")
                row.append(f"{w}:{d:+d}")
            print(f"{label:28s} " + "  ".join(row))
        await b.close()

asyncio.run(main())
