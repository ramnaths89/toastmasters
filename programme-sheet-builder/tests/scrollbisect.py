"""Bisect the horizontal overflow by hiding elements, not by reasoning about CSS.

For every element in the document, set display:none, re-read documentElement
scrollWidth, restore. Anything whose removal drops the scrollWidth is a real
contributor. Deepest contributors are the culprits.
"""
import asyncio, os, sys
from playwright.async_api import async_playwright

TARGET = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "/home/claude/psb/ProgSheetGenV35.html")
WIDTH = int(sys.argv[2]) if len(sys.argv) > 2 else 1440

JS = """
() => {
  const de = document.documentElement;
  const base = de.scrollWidth, cw = de.clientWidth;
  const hits = [];
  const all = Array.from(document.querySelectorAll('body *'));
  for (const el of all) {
    const prev = el.style.display;
    el.style.display = 'none';
    const now = de.scrollWidth;
    el.style.display = prev;
    if (now < base) {
      let depth = 0, n = el;
      while ((n = n.parentElement)) depth++;
      hits.push({ depth, tag: el.tagName.toLowerCase(), id: el.id || '',
                  cls: String(el.className || '').slice(0,70),
                  drops_to: now, saves: base - now });
    }
  }
  hits.sort((a,b)=> b.depth - a.depth);
  return { base, cw, hits };
}
"""

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={"width": WIDTH, "height": 900})
        await ctx.route("http*://**", lambda r: asyncio.ensure_future(r.abort()))
        pg = await ctx.new_page()
        await pg.goto("file://" + TARGET)
        await pg.wait_for_timeout(900)
        r = await pg.evaluate(JS)
        print(f"{TARGET}\nwidth={WIDTH} scrollWidth={r['base']} clientWidth={r['cw']} delta={r['base']-r['cw']}")
        print(f"{len(r['hits'])} contributing elements, deepest first:\n")
        for h in r["hits"][:25]:
            print(f"  depth={h['depth']:3d} <{h['tag']}> id={h['id']!r} class={h['cls']!r}"
                  f"  -> {h['drops_to']} (saves {h['saves']})")
        await b.close()

asyncio.run(main())
