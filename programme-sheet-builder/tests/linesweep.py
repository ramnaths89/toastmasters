"""Sweep export conditions (webfonts on/off, GPU flags, dsf, title on/off) and
report where the pane's column rule lands in the exported page 1.

Correct: a dark 1px rule at image x ~358 (CSS 171.8).  Rama's defect: no rule
there and a light rule at image x ~740 (CSS 354.6).
"""
import asyncio, base64, itertools, os, subprocess, sys, tempfile
import numpy as np
from PIL import Image
from playwright.async_api import async_playwright

TARGET = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "/home/claude/psb/ProgSheetGenV37.html")
RAMA = open("/tmp/rama.json").read()
PROXY = os.environ.get("HTTPS_PROXY")

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


def verticals(path):
    a = np.asarray(Image.open(path).convert("RGB")).astype(float).mean(2)
    H, W = a.shape
    ref = (np.roll(a, 4, 1) + np.roll(a, -4, 1)) / 2
    m = np.median(a - ref, axis=0)
    hits = [(x, round(float(m[x]), 1)) for x in range(4, W - 4) if abs(m[x]) > 8]
    return W, H, hits


async def run(pw, label, launch_args, dsf, fonts, title, outdir):
    kw = dict(args=launch_args)
    if fonts and PROXY:
        kw["proxy"] = {"server": PROXY}
    b = await pw.chromium.launch(**kw)
    ctx = await b.new_context(viewport={"width": 1440, "height": 900},
                              device_scale_factor=dsf, ignore_https_errors=True)
    if not fonts:
        await ctx.route("**fonts.googleapis.com**", lambda r: asyncio.ensure_future(r.abort()))
        await ctx.route("**fonts.gstatic.com**", lambda r: asyncio.ensure_future(r.abort()))
    pg = await ctx.new_page()
    await pg.goto("file://" + TARGET)
    await pg.wait_for_function("() => typeof state !== 'undefined'", timeout=20000)
    await pg.wait_for_timeout(2500)
    await pg.evaluate("(t) => applyMeetingText(t, 'rama.json')", RAMA)
    if not title:
        await pg.evaluate("() => { state.meeting.title=''; renderPreviewNow(); }")
    await pg.wait_for_timeout(2500)
    got = await pg.evaluate(CAPTURE, "pdf")
    tag = label.replace(" ", "_")
    res = "no blob"
    for g in got:
        p = os.path.join(outdir, tag + ".pdf")
        open(p, "wb").write(base64.b64decode(g["b64"]))
        subprocess.run(["pdfimages", "-j", p, os.path.join(outdir, tag)], check=True)
        f = os.path.join(outdir, tag + "-000.jpg")
        if os.path.exists(f):
            W, H, hits = verticals(f)
            near358 = [h for h in hits if 350 <= h[0] <= 366]
            near740 = [h for h in hits if 730 <= h[0] <= 752]
            res = f"{W}x{H} rule@358={near358} rule@740={near740}"
    fam = await pg.evaluate("() => document.fonts.check('12px Montserrat')")
    print(f"  {label}: montserrat={fam} -> {res}", flush=True)
    await b.close()


async def main():
    outdir = tempfile.mkdtemp(prefix="sweep-")
    print("out", outdir)
    gpu = ["--use-gl=angle", "--use-angle=swiftshader", "--enable-gpu-rasterization",
           "--enable-accelerated-2d-canvas", "--ignore-gpu-blocklist"]
    async with async_playwright() as pw:
        for fonts in (False, True):
            for args, an in ((["--disable-gpu"], "swraster"), (gpu, "gpu")):
                for dsf in (1, 1.5):
                    for title in (True,):
                        await run(pw, f"fonts{int(fonts)}_{an}_dsf{dsf}_t{int(title)}",
                                  args, dsf, fonts, title, outdir)

asyncio.run(main())
