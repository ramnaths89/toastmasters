"""Export rama.json through the real path and dump page-1 vertical-rule x positions."""
import asyncio, base64, os, subprocess, sys, tempfile
import numpy as np
from PIL import Image
from playwright.async_api import async_playwright

TARGET = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "/home/claude/psb/ProgSheetGenV37.html")
RAMA = open("/tmp/rama.json").read()
OUT = sys.argv[2] if len(sys.argv) > 2 else tempfile.mkdtemp(prefix="ramaexp-")
os.makedirs(OUT, exist_ok=True)

CAPTURE = """
async (kind) => {
  const blobs = [];
  const realSave = saveBlob;
  saveBlob = (blob, name) => { blobs.push({blob, name}); };
  try { await pickDownload(kind); } finally { saveBlob = realSave; }
  const out = [];
  for (const b of blobs) {
    const u = new Uint8Array(await b.blob.arrayBuffer());
    let s = '';
    for (let i = 0; i < u.length; i += 8192)
      s += String.fromCharCode.apply(null, u.subarray(i, i + 8192));
    out.push({name: b.name, b64: btoa(s)});
  }
  return out;
}
"""


def rules(png, label):
    a = np.asarray(Image.open(png).convert("RGB")).astype(int)
    H, W, _ = a.shape
    l, r = np.roll(a, 1, axis=1), np.roll(a, -1, axis=1)
    d = (np.abs(a - l).sum(2) > 10) & (np.abs(a - r).sum(2) > 10)
    c = d.sum(0)
    print(f"  {label}: {W}x{H}")
    for x in range(1, W - 1):
        if c[x] > H * 0.35:
            print(f"    x={x} rows={c[x]} {100*x/W:.2f}%")


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
        print("theme =", await pg.evaluate("() => document.body.className + ' | ' + (state.theme||'')"))
        got = await pg.evaluate(CAPTURE, "pdf")
        for g in got:
            path = os.path.join(OUT, "mine.pdf")
            open(path, "wb").write(base64.b64decode(g["b64"]))
            subprocess.run(["pdfimages", "-j", path, os.path.join(OUT, "mine")], check=True)
        for f in sorted(os.listdir(OUT)):
            if f.startswith("mine-"):
                rules(os.path.join(OUT, f), f)
        await b.close()
    print("artefacts in", OUT)

asyncio.run(main())
