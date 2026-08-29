"""Log every html2canvas fill() whose path is a tall thin rectangle, so the pane's
column rule can be identified by its draw call rather than inferred from pixels.

    python3 tests/fillprobe.py [file.html]
"""
import asyncio, json, os, sys
from playwright.async_api import async_playwright

TARGET = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "/home/claude/psb/ProgSheetGenV37.html")
RAMA = open("/tmp/rama.json").read()

PROBE = r"""
async () => {
  const P = CanvasRenderingContext2D.prototype;
  const log = [];
  const st = new WeakMap();
  const box = (c) => { let b = st.get(c); if(!b){ b={x0:1e9,y0:1e9,x1:-1e9,y1:-1e9}; st.set(c,b);} return b; };
  const note = (c,x,y) => { const b=box(c); b.x0=Math.min(b.x0,x); b.y0=Math.min(b.y0,y);
                            b.x1=Math.max(b.x1,x); b.y1=Math.max(b.y1,y); };
  const wrap = (name, fn) => { const o = P[name]; P[name] = function(...a){ fn(this,a); return o.apply(this,a); }; return o; };
  wrap('beginPath', (c)=>{ st.set(c,{x0:1e9,y0:1e9,x1:-1e9,y1:-1e9}); });
  wrap('moveTo', (c,a)=>note(c,a[0],a[1]));
  wrap('lineTo', (c,a)=>note(c,a[0],a[1]));
  wrap('rect', (c,a)=>{ note(c,a[0],a[1]); note(c,a[0]+a[2],a[1]+a[3]); });
  wrap('bezierCurveTo', (c,a)=>{ note(c,a[0],a[1]); note(c,a[2],a[3]); note(c,a[4],a[5]); });
  const of_ = P.fill;
  P.fill = function(...a){
    const b = st.get(this);
    if (b && isFinite(b.x0)) {
      const w = b.x1-b.x0, h = b.y1-b.y0;
      if (w < 4 && h > 400) log.push({x0:+b.x0.toFixed(2), x1:+b.x1.toFixed(2),
        y0:+b.y0.toFixed(2), y1:+b.y1.toFixed(2), style:String(this.fillStyle),
        cw:this.canvas.width, ch:this.canvas.height});
    }
    return of_.apply(this,a);
  };
  try { await renderSheetParts({paginate:true}); } catch(e){ return {err:String(e), log}; }
  return {err:null, log};
}
"""


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={"width": 1440, "height": 900})
        pg = await ctx.new_page()
        pg.on("pageerror", lambda e: print("PAGEERROR:", e))
        await pg.goto("file://" + TARGET)
        await pg.wait_for_function("() => typeof state !== 'undefined'", timeout=20000)
        await pg.wait_for_timeout(2000)
        await pg.evaluate("(t) => applyMeetingText(t, 'rama.json')", RAMA)
        await pg.wait_for_timeout(1500)
        out = await pg.evaluate(PROBE)
        print("err", out["err"])
        for r in out["log"]:
            print(" ", json.dumps(r))
        await b.close()

asyncio.run(main())
