"""Sweep candidate override CSS against one load/theme without rebuilding."""
import asyncio, os, sys, json
from playwright.async_api import async_playwright
import panefit as PF

VARIANTS = json.load(open(sys.argv[4]))

async def main():
    path, load, theme = sys.argv[1], sys.argv[2], sys.argv[3]
    script = dict(PF.LOADS)[load]
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={'width': PF.PAGE_W, 'height': PF.PAGE_H})
        await ctx.route('http*://**', lambda r: asyncio.ensure_future(r.abort()))
        sheet = await ctx.new_page(); await sheet.emulate_media(media='print')
        page = await ctx.new_page()
        await page.goto('file://'+os.path.abspath(path), wait_until='domcontentloaded')
        await page.wait_for_timeout(700)
        await page.evaluate(script)
        await page.evaluate("t => { state.theme=t; }", theme)
        html = await page.evaluate("() => buildSheetHTML(false)")
        for name, css in VARIANTS.items():
            await sheet.set_content(html, wait_until='load')
            await sheet.emulate_media(media='print')
            if css:
                await sheet.add_style_tag(content='@media print{' + css + '}')
            await sheet.wait_for_timeout(150)
            r = await sheet.evaluate(PF.MEASURE)
            w = await sheet.evaluate("() => { const b=document.querySelector('.pane-body'); const cs=getComputedStyle(b); return {inner:b.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight), pl:cs.paddingLeft, pr:cs.paddingRight, lines:document.querySelectorAll('.announce-line').length}; }")
            print('  %-38s over %+7.1f mm   text col %.1f mm  (pad L %s R %s)'
                  % (name, r['overflowPx']/PF.PX_PER_MM, w['inner']/PF.PX_PER_MM, w['pl'], w['pr']))
        await b.close()
asyncio.run(main())
