"""Does REAL browser print also put agenda content under its fixed footer?"""
import asyncio, os, subprocess, sys, tempfile, glob
from playwright.async_api import async_playwright
from PIL import Image
import numpy as np
import panefit as PF, exportprobe as EP

async def main():
    path=sys.argv[1]; load=sys.argv[2]; theme='classic'
    async with async_playwright() as p:
        b=await p.chromium.launch()
        ctx=await b.new_context(viewport={'width':PF.PAGE_W,'height':1000})
        await ctx.route('http*://**', lambda r: asyncio.ensure_future(r.abort()))
        pg=await ctx.new_page()
        await pg.goto('file://'+os.path.abspath(path), wait_until='domcontentloaded')
        await pg.wait_for_timeout(700)
        await pg.evaluate(EP.LOADS[load]); await pg.evaluate("t=>{state.theme=t;}", theme)
        html=await pg.evaluate("() => buildSheetHTML(false)")
        sh=await ctx.new_page(); await sh.set_viewport_size({'width':PF.PAGE_W,'height':1000})
        await sh.set_content(html, wait_until='load'); await sh.emulate_media(media='print')
        await sh.wait_for_timeout(250)
        fd,pdf=tempfile.mkstemp(suffix='.pdf'); os.close(fd)
        await sh.pdf(path=pdf, format='A4', print_background=True,
                     margin={'top':'0','bottom':'0','left':'0','right':'0'})
        await b.close()
    td=tempfile.mkdtemp(); dpi=300; ppmm=dpi/25.4
    subprocess.run(['pdftoppm','-r',str(dpi),'-png',pdf,os.path.join(td,'p')],capture_output=True)
    fs=sorted(glob.glob(os.path.join(td,'p-*.png')))
    print('%s / %s  real print, %d pages' % (load, theme, len(fs)))
    for i,f in enumerate(fs):
        im=np.asarray(Image.open(f).convert('L')).astype(float)
        h,w=im.shape
        # the footer band: 6.5mm above the 10mm bottom margin
        y1=int(h-10*ppmm); y0=int(y1-6.5*ppmm)
        # agenda column only (right of the pane) so we do not count the footer's own text
        x0=int((10+45.6+3)*ppmm); x1=int(w-10*ppmm)
        band=im[y0:y1-int(2.2*ppmm), x0:x1]      # exclude the footer's own text line
        ink=(band<170).mean()*100
        print('   page %d: agenda ink inside the footer band = %.3f%%  %s'
              % (i+1, ink, 'COLLIDES' if ink>0.02 else 'clear'))
asyncio.run(main())
