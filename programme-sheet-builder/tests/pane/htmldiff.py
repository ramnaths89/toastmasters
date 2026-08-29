import asyncio, os, sys, difflib
from playwright.async_api import async_playwright
import panefit as PF
async def grab(path):
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={'width':PF.PAGE_W,'height':PF.PAGE_H})
        await ctx.route('http*://**', lambda r: asyncio.ensure_future(r.abort()))
        pg = await ctx.new_page()
        await pg.goto('file://'+os.path.abspath(path), wait_until='domcontentloaded')
        await pg.wait_for_timeout(700)
        await pg.evaluate(dict(PF.LOADS)['full-night'])
        await pg.evaluate("() => { state.theme='classic'; }")
        h = await pg.evaluate("() => buildSheetHTML(false)")
        css = await pg.evaluate("() => SHEET_CSS")
        await b.close()
        return h, css
async def main():
    a,ca = await grab(sys.argv[1]); b,cb = await grab(sys.argv[2])
    import re
    a2 = re.sub(r'data:image/png;base64,[A-Za-z0-9+/=]+','LOGO',a)
    b2 = re.sub(r'data:image/png;base64,[A-Za-z0-9+/=]+','LOGO',b)
    print('SHEET_CSS identical:', ca==cb)
    print('--- buildSheetHTML diff ---')
    n=0
    for line in difflib.unified_diff(a2.split('\n'), b2.split('\n'), 'V31','V32', lineterm='', n=1):
        print(line[:400]); n+=1
        if n>60: print('...'); break
asyncio.run(main())
