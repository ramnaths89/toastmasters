import asyncio, sys, os
from playwright.async_api import async_playwright
import panefit as PF, exportprobe as EP

Q = """
() => {
  const PX=96/25.4, PAGE=277*PX;
  const fr=Array.from(document.querySelectorAll('iframe[data-kept]')).pop();
  const d=fr.contentDocument, page=d.querySelector('.page');
  const pt=page.getBoundingClientRect().top;
  const foot=d.querySelector('footer');
  const footH=foot?foot.getBoundingClientRect().height:0;
  const rows=Array.from(d.querySelectorAll('tbody tr')).filter(r=>!r.classList.contains('pg-spacer'));
  const out=[];
  const H=page.getBoundingClientRect().height, pages=Math.max(1,Math.round(H/PAGE));
  for(let i=1;i<pages;i++){
    const B=i*PAGE;
    const above=rows.filter(r=>(r.getBoundingClientRect().bottom-pt)<=B+0.5);
    const last=above[above.length-1];
    const first=rows.find(r=>(r.getBoundingClientRect().top-pt)>=B-0.5);
    out.push({
      edge:i,
      lastRowOnPage: last?last.querySelector('td').textContent.trim():null,
      lastRowBottomFromEdge: last? +(B-(last.getBoundingClientRect().bottom-pt)).toFixed(1):null,
      footBand: +footH.toFixed(1),
      firstRowNextPage: first?first.querySelector('td').textContent.trim():null,
      spacerBefore: first && first.previousElementSibling && first.previousElementSibling.classList.contains('pg-spacer')
        ? +first.previousElementSibling.getBoundingClientRect().height.toFixed(1) : 0,
    });
  }
  return out;
}
"""
async def main():
    r = await EP.run(sys.argv[1], sys.argv[2], 'classic')
    print(r['breaks'])
asyncio.run(main())
