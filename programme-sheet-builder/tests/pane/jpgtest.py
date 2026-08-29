import asyncio, os, sys
from playwright.async_api import async_playwright
import panefit as PF, exportprobe as EP
async def main():
    path, load = sys.argv[1], sys.argv[2]
    async with async_playwright() as p:
        b=await p.chromium.launch()
        ctx=await b.new_context(viewport={'width':PF.PAGE_W,'height':1000})
        await ctx.route('http*://**', lambda r: asyncio.ensure_future(r.abort()))
        pg=await ctx.new_page()
        await pg.goto('file://'+os.path.abspath(path), wait_until='domcontentloaded')
        await pg.wait_for_timeout(700)
        await pg.evaluate(EP.SETUP); await pg.evaluate(EP.LOADS[load])
        try:
            await asyncio.wait_for(pg.evaluate("() => downloadImage()"), timeout=300)
        except asyncio.TimeoutError:
            print('TIMEOUT')
        cap=await pg.evaluate("() => window.__cap")
        print('%s -> JPG banner: %s' % (load, cap.get('banners')))
        await b.close()
asyncio.run(main())
