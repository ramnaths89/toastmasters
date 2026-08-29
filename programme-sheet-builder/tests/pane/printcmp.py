"""In-page PDF vs real browser print: page count and where the break lands.

For the in-page PDF the break is read off the staged export DOM (the canvas is a
JPEG, so there is no text to extract). For real print it is read from Chrome's
own print-to-PDF with pdftotext, per page.
"""
import asyncio, os, subprocess, sys, tempfile, re
from playwright.async_api import async_playwright
import panefit as PF, exportprobe as EP

BREAKS = """
() => {
  const PX=96/25.4, PAGE=277*PX;
  const fr=Array.from(document.querySelectorAll('iframe[data-kept]')).pop();
  const d=fr.contentDocument, page=d.querySelector('.page');
  const pt=page.getBoundingClientRect().top, H=page.getBoundingClientRect().height;
  const pages=Math.max(1,Math.round(H/PAGE));
  const rows=Array.from(d.querySelectorAll('tbody tr')).filter(r=>!r.classList.contains('pg-spacer'));
  const out=[];
  for(let i=1;i<pages;i++){
    const B=i*PAGE;
    const first=rows.find(r=>(r.getBoundingClientRect().top-pt)>=B-0.5);
    out.push(first ? (first.querySelector('td')||{}).textContent.trim() : '(no row)');
  }
  return {pages, firstRowOfEachPage: out};
}
"""

async def realprint(path, load, theme):
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
    info=subprocess.run(['pdfinfo',pdf],capture_output=True,text=True).stdout
    n=int([l for l in info.splitlines() if l.startswith('Pages:')][0].split(':')[1])
    firsts=[]
    for i in range(2,n+1):
        txt=subprocess.run(['pdftotext','-layout','-f',str(i),'-l',str(i),pdf,'-'],
                           capture_output=True,text=True).stdout
        m=re.search(r'(\d{1,2}:\d{2}\s*[AP]M)', txt)
        firsts.append(m.group(1) if m else '(none)')
    return n, firsts, pdf

async def main():
    path=sys.argv[1]; theme=sys.argv[3] if len(sys.argv)>3 else 'classic'
    for load in sys.argv[2].split(','):
        r=await EP.run(path, load, theme)
        # re-open to read break info is not possible; recompute from same run is,
        # so EP.run is extended below via a second evaluate in the same session.
        n_real, firsts_real, _ = await realprint(path, load, theme)
        print('%-12s %-11s  in-page PDF: %s pages   real print: %s pages   %s'
              % (load, theme, r['pdfPages'] if r.get('pdfPages') else EP.pdfpages(r['pdfPath']),
                 n_real, 'MATCH' if (EP.pdfpages(r['pdfPath'])==n_real) else '*** DIFFER ***'))
        print('              real print, first agenda time on pages 2..n: %s' % firsts_real)
        print('              in-page break rows: %s' % (r.get('breaks')))
asyncio.run(main())
