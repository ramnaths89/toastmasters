"""Dump every vertical edge in the EXPORT layout (the iframe renderSheetParts
builds) by stubbing html2canvas, with and without the meeting title.

    python3 tests/edgeprobe.py [file.html]
"""
import asyncio, json, os, sys
from playwright.async_api import async_playwright

TARGET = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "/home/claude/psb/ProgSheetGenV37.html")
RAMA = open("/tmp/rama.json").read()

PROBE = r"""
async (want) => {
  const dumps = [];
  const real = window.html2canvas;
  window.html2canvas = async (el, opts) => {
    const doc = el.ownerDocument;
    const pr = el.getBoundingClientRect();
    const rows = [];
    const all = doc.querySelectorAll('*');
    for (const e of all) {
      const r = e.getBoundingClientRect();
      if (!r.width && !r.height) continue;
      const cs = doc.defaultView.getComputedStyle(e);
      rows.push({
        tag: e.tagName.toLowerCase(),
        cls: (e.className && e.className.baseVal !== undefined ? e.className.baseVal : e.className) || '',
        L: +(r.left - pr.left).toFixed(2), R: +(r.right - pr.left).toFixed(2),
        T: +(r.top - pr.top).toFixed(2), B: +(r.bottom - pr.top).toFixed(2),
        bl: cs.borderLeftWidth, br: cs.borderRightWidth,
        blc: cs.borderLeftColor, brc: cs.borderRightColor,
        ov: cs.overflow, pos: cs.position, tr: cs.transform,
        z: cs.zIndex, op: cs.opacity, bg: cs.backgroundColor,
        sw: e.scrollWidth, cw: e.clientWidth, sh: e.scrollHeight, ch: e.clientHeight,
      });
    }
    dumps.push({pageW: pr.width, pageH: pr.height, optW: opts.width, optH: opts.height,
                scale: opts.scale, canvasW: opts.canvas && opts.canvas.width,
                canvasH: opts.canvas && opts.canvas.height, rows});
    const c = doc.defaultView.parent.document.createElement('canvas');
    c.width = Math.floor(opts.width * opts.scale); c.height = Math.floor(opts.height * opts.scale);
    return c;
  };
  try {
    await renderSheetParts({paginate: true});
  } finally { window.html2canvas = real; }
  return dumps;
}
"""


def report(d, label):
    W = d["pageW"]
    print(f"\n===== {label}: page {W} x {d['pageH']}, h2c {d['optW']}x{d['optH']} "
          f"scale {d['scale']} canvas {d['canvasW']}x{d['canvasH']}")
    tgt = W * 0.4927
    print(f"  target x = {tgt:.2f} px  (49.27% of {W})")
    near = []
    for r in d["rows"]:
        for nm, x in (("L", r["L"]), ("R", r["R"])):
            if abs(x - tgt) < 6:
                near.append((abs(x - tgt), nm, x, r))
    near.sort(key=lambda t: t[0])
    seen = set()
    for dist, nm, x, r in near:
        k = (r["tag"], r["cls"], nm, round(x, 1))
        if k in seen:
            continue
        seen.add(k)
        print(f"   {x:8.2f} {nm} d={dist:5.2f} <{r['tag']}.{r['cls']}> "
              f"T={r['T']:.0f} B={r['B']:.0f} bl={r['bl']} br={r['br']} "
              f"pos={r['pos']} ov={r['ov']} tr={r['tr'][:24]}")
    # tall elements
    print("  --- elements taller than 80% of page ---")
    for r in d["rows"]:
        if r["B"] - r["T"] > d["pageH"] * 0.8:
            print(f"   <{r['tag']}.{r['cls']}> L={r['L']} R={r['R']} T={r['T']:.0f} B={r['B']:.0f} "
                  f"bl={r['bl']} br={r['br']} ov={r['ov']} pos={r['pos']} sw={r['sw']} cw={r['cw']}")
    # overflowing elements (scrollWidth > clientWidth) - clip candidates
    print("  --- scrollWidth > clientWidth ---")
    for r in d["rows"]:
        if r["sw"] > r["cw"] + 1:
            print(f"   <{r['tag']}.{r['cls']}> sw={r['sw']} cw={r['cw']} L={r['L']} R={r['R']} ov={r['ov']}")


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={"width": 1440, "height": 900})
        pg = await ctx.new_page()
        pg.on("pageerror", lambda e: print("PAGEERROR:", e))
        pg.on("console", lambda m: print("CONSOLE:", m.type, m.text) if m.type == "error" else None)
        await pg.goto("file://" + TARGET)
        await pg.wait_for_function("() => typeof state !== 'undefined'", timeout=20000)
        await pg.wait_for_timeout(2000)
        await pg.evaluate("(t) => applyMeetingText(t, 'rama.json')", RAMA)
        await pg.wait_for_timeout(1200)
        title = await pg.evaluate("() => state.meeting.title")
        print("title =", repr(title))
        d = (await pg.evaluate(PROBE, "with"))[0]
        report(d, "WITH TITLE")
        json.dump(d, open("/tmp/edge_with.json", "w"))

        await pg.evaluate("() => { state.meeting.title=''; renderPreviewNow(); }")
        await pg.wait_for_timeout(600)
        d2 = (await pg.evaluate(PROBE, "without"))[0]
        report(d2, "NO TITLE")
        json.dump(d2, open("/tmp/edge_without.json", "w"))
        await b.close()

asyncio.run(main())
