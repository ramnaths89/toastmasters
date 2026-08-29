"""Does the Exco list group? Compare within-entry and between-entry baseline steps."""
import asyncio, os, sys
from playwright.async_api import async_playwright
import panefit as PF
MEAS = """
() => {
  const items = Array.from(document.querySelectorAll('.exco-block .exco-item')).slice(0,8);
  const within = [], between = [];
  items.forEach((it, i) => {
    const role = it.querySelector('.exco-role').getBoundingClientRect();
    const name = it.querySelector('.exco-name').getBoundingClientRect();
    within.push(name.top - role.top);
    if (i < items.length-1){
      const nrole = items[i+1].querySelector('.exco-role').getBoundingClientRect();
      between.push(nrole.top - name.top);
    }
  });
  const avg = a => a.reduce((x,y)=>x+y,0)/a.length;
  return {within: +avg(within).toFixed(2), between: +avg(between).toFixed(2)};
}
"""
async def main():
    path=sys.argv[1]; theme=sys.argv[2] if len(sys.argv)>2 else 'classic'
    async with async_playwright() as p:
        b=await p.chromium.launch()
        ctx=await b.new_context(viewport={'width':PF.PAGE_W,'height':PF.PAGE_H})
        await ctx.route('http*://**', lambda r: asyncio.ensure_future(r.abort()))
        sh=await ctx.new_page(); await sh.emulate_media(media='print')
        pg=await ctx.new_page()
        await pg.goto('file://'+os.path.abspath(path), wait_until='domcontentloaded')
        await pg.wait_for_timeout(700)
        await pg.evaluate(dict(PF.LOADS)['full-night']); await pg.evaluate("t=>{state.theme=t;}", theme)
        html=await pg.evaluate("() => buildSheetHTML(false)")
        await sh.set_content(html, wait_until='load'); await sh.emulate_media(media='print')
        await sh.wait_for_timeout(200)
        r=await sh.evaluate(MEAS)
        print('  %-28s within-entry %.2f px   between-entry %.2f px   ratio %.2f'
              % (os.path.basename(path)+'/'+theme, r['within'], r['between'], r['between']/r['within']))
        await b.close()
asyncio.run(main())
