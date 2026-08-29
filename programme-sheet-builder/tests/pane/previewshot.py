"""Screenshot the BUILDER's live preview iframe (buildSheetHTML(true), screen media)."""
import asyncio, hashlib, os, sys
from playwright.async_api import async_playwright
import panefit as PF
async def main():
    tag, path = sys.argv[1], sys.argv[2]
    async with async_playwright() as p:
        b=await p.chromium.launch()
        ctx=await b.new_context(viewport={'width':1600,'height':1100}, device_scale_factor=2)
        await ctx.route('http*://**', lambda r: asyncio.ensure_future(r.abort()))
        pg=await ctx.new_page()
        await pg.goto('file://'+os.path.abspath(path), wait_until='domcontentloaded')
        await pg.wait_for_timeout(900)
        await pg.evaluate(dict(PF.LOADS)['full-night'])
        for theme in ('classic','zine'):
            await pg.evaluate("t=>{state.theme=t; renderPreviewNow();}", theme)
            await pg.wait_for_timeout(500)
            fr = pg.frame_locator('#previewFrame')
            el = fr.locator('aside.ref-pane')
            png = await el.screenshot()
            open('prev-%s-%s.png'%(theme,tag),'wb').write(png)
            print('preview pane %-8s %s sha1=%s bytes=%d' % (theme, tag, hashlib.sha1(png).hexdigest()[:16], len(png)))
        await b.close()
asyncio.run(main())
