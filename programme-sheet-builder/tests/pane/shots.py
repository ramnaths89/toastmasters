"""Print page-1 screenshots (classic, zine) plus a SCREEN-media pixel check.

The image/PDF exports rasterise the SCREEN layout, so the screen sheet must come
out byte-identical unless the change was meant to touch it.
"""
import asyncio, hashlib, os, sys
from playwright.async_api import async_playwright
import panefit as PF

async def main():
    tag, path = sys.argv[1], sys.argv[2]
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={'width': PF.PAGE_W, 'height': PF.PAGE_H},
                                  device_scale_factor=2)
        await ctx.route('http*://**', lambda r: asyncio.ensure_future(r.abort()))
        page = await ctx.new_page()
        await page.goto('file://' + os.path.abspath(path), wait_until='domcontentloaded')
        await page.wait_for_timeout(700)
        await page.evaluate(dict(PF.LOADS)['full-night'])
        for theme in ('classic', 'zine'):
            await page.evaluate("t => { state.theme = t; }", theme)
            html = await page.evaluate("() => buildSheetHTML(false)")
            sheet = await ctx.new_page()
            await sheet.set_viewport_size({'width': PF.PAGE_W, 'height': PF.PAGE_H})
            # ---- PRINT page 1
            await sheet.set_content(html, wait_until='load')
            await sheet.emulate_media(media='print')
            await sheet.wait_for_timeout(220)
            await sheet.screenshot(path='shot-print-%s-%s.png' % (theme, tag),
                                   clip={'x': 0, 'y': 0, 'width': PF.PAGE_W, 'height': PF.PAGE_H})
            # ---- SCREEN full sheet (what the JPG/PDF exporter rasterises)
            await sheet.emulate_media(media='screen')
            await sheet.wait_for_timeout(220)
            png = await sheet.screenshot(full_page=True)
            print('screen %-6s %s  sha1=%s  bytes=%d'
                  % (theme, tag, hashlib.sha1(png).hexdigest()[:16], len(png)))
            open('shot-screen-%s-%s.png' % (theme, tag), 'wb').write(png)
            await sheet.close()
        await b.close()
asyncio.run(main())
