"""How tall does the banner have to get before the brand-box logo distorts?

Replicates ONLY the staging geometry of renderSheetParts (iframe at the print box,
printRulesText(), the same fix stylesheet, the same header/brand equalisation).
Two points are cross-checked against the REAL export path.
"""
import asyncio, os, sys
from playwright.async_api import async_playwright
import panefit as PF

STAGE = """
async (mut) => {
  eval('(' + mut + ')')();
  const PX=96/25.4, W=Math.round(190*PX), H=277*PX;
  const f=document.createElement('iframe');
  f.style.cssText='position:fixed;left:-10000px;top:0;border:0;visibility:hidden;width:'+W+'px;height:'+Math.ceil(H)+'px;';
  document.body.appendChild(f);
  await new Promise((r,j)=>{ f.onload=r; f.onerror=()=>j(new Error('f')); f.srcdoc=buildSheetHTML(false); });
  const d=f.contentDocument;
  const pc=d.createElement('style'); pc.textContent=printRulesText(d); d.head.appendChild(pc);
  const fx=d.createElement('style');
  fx.textContent='html,body{background:#fff!important;margin:0!important;padding:0!important}'
    +'.page-wrap{padding:0!important;display:block!important}'
    +'.page{box-shadow:none!important;border-radius:0!important;max-width:none!important;width:100%!important;position:relative!important;overflow:visible!important}'
    +'aside.ref-pane{position:absolute!important;top:0!important;left:0!important;right:auto!important;height:auto!important;overflow:visible!important}'
    +'footer{position:absolute!important;left:0!important;right:0!important;bottom:0!important;top:auto!important}'
    +'.pane-body{height:auto!important;min-height:calc(100% - var(--print-head))!important}'
    +'.pane-brand img{height:auto!important;width:auto!important;max-height:calc(100% - 10px)!important;max-width:100%!important}'
    +'.print-fab{display:none!important}.schedule-note{display:none!important}';
  d.head.appendChild(fx);
  if(d.fonts&&d.fonts.ready) await Promise.race([d.fonts.ready,new Promise(r=>setTimeout(r,4000))]);
  await new Promise(r=>setTimeout(r,120));
  const hdr=d.querySelector('header'), brand=d.querySelector('.pane-brand'), img=brand.querySelector('img');
  hdr.style.height='auto'; hdr.style.overflow='visible'; brand.style.height='auto';
  await new Promise(r=>setTimeout(r,30));
  const hh=Math.ceil(hdr.getBoundingClientRect().height)+1;
  hdr.style.height=hh+'px'; brand.style.height=hh+'px';
  await new Promise(r=>setTimeout(r,30));
  const ir=img.getBoundingClientRect();
  const out={hh, imgW:+ir.width.toFixed(1), imgH:+ir.height.toFixed(1),
             aspect:+(ir.width/ir.height).toFixed(4), nat:+(img.naturalWidth/img.naturalHeight).toFixed(4)};
  f.remove();
  return out;
}
"""

CASES = [
  ('defaults (blank template)', "() => {}"),
  ('normal night', "() => { state.meeting.title='Chapter Meeting: Voices of a Nation'; state.meeting.dateDisplay='Thursday, 13 August 2026'; }"),
  ('+ longer title', "() => { state.meeting.title='Chapter Meeting: Voices of a Nation and the Stories We Carry'; state.meeting.dateDisplay='Thursday, 13 August 2026'; }"),
  ('+ real venue, one extra clause', "() => { state.meeting.title='Chapter Meeting: Voices of a Nation'; state.meeting.dateDisplay='Thursday, 13 August 2026'; state.meeting.location='Nee Soon East Community Club, 1 Yishun Ave 9, #04-01 (Culinary Studio), Singapore 768893 - enter from the carpark'; }"),
  ('venue wraps to 2 lines', "() => { state.meeting.title='Chapter Meeting: Voices of a Nation'; state.meeting.dateDisplay='Thursday, 13 August 2026'; state.meeting.location='Nee Soon East Community Club, 1 Yishun Avenue 9, #04-01 (Culinary Studio), Singapore 768893, entrance via the side door facing the carpark'; }"),
  ('venue wraps to 3 lines', "() => { state.meeting.title='Chapter Meeting: Voices of a Nation'; state.meeting.dateDisplay='Thursday, 13 August 2026'; state.meeting.location='Nee Soon East Community Club, 1 Yishun Avenue 9, #04-01 (Culinary Studio), Singapore 768893, entrance via the side door facing the carpark, ask the SAA at the lift lobby if you are lost'; }"),
  ('cadence + venue both long', "() => { state.meeting.title='Chapter Meeting: Voices of a Nation'; state.meeting.dateDisplay='Thursday, 13 August 2026'; state.meeting.cadence='We meet every 2nd and 4th Thursday of the month from 7:00PM to 9:30PM, and on the 5th Thursday when the calendar allows it'; state.meeting.location='Nee Soon East Community Club, 1 Yishun Avenue 9, #04-01 (Culinary Studio), Singapore 768893, entrance via the side door facing the carpark'; }"),
  ('extreme venue (235px banner)', "() => { state.meeting.title='Chapter Meeting: Voices of a Nation ' + 'and Other Very Long Titles '.repeat(3); state.meeting.location=('Nee Soon East Community Club, 1 Yishun Avenue 9, #04-01 Culinary Studio, entrance via the side door facing the carpark, Nee Soon East Constituency, Singapore 768893').repeat(4); }"),
]

async def main():
    path = sys.argv[1]; theme = sys.argv[2] if len(sys.argv)>2 else 'classic'
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={'width':PF.PAGE_W,'height':1000})
        await ctx.route('http*://**', lambda r: asyncio.ensure_future(r.abort()))
        print('  %-34s %7s %8s %8s %9s' % ('case','banner','logo w','logo h','aspect'))
        for name, mut in CASES:
            pg = await ctx.new_page()
            await pg.goto('file://'+os.path.abspath(path), wait_until='domcontentloaded')
            await pg.wait_for_timeout(700)
            await pg.evaluate("t => { state.theme=t; }", theme)
            r = await pg.evaluate(STAGE, mut)
            bad = abs(r['aspect']-r['nat'])>0.02
            print('  %-34s %6dpx %7.1f %8.1f %9.4f %s'
                  % (name, r['hh'], r['imgW'], r['imgH'], r['aspect'],
                     'DISTORTED %.0f%% narrow' % ((1-r['aspect']/r['nat'])*100) if bad else 'ok'))
            await pg.close()
        await b.close()
asyncio.run(main())
