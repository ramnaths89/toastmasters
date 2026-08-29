"""Find the vertical seam Rama sees down the middle of the PDF and JPG exports.

Drives the app's OWN export path (downloadPdfImage / the JPG ladder), captures the
bytes, renders them, and looks for a thin vertical column that differs from both of
its neighbours down most of the page. Reports the x position as a FRACTION of the
sheet's content width, which is what makes it comparable with Rama's printout.

    python3 tests/seamprobe.py <file.html> [theme]
"""
import asyncio, base64, os, subprocess, sys, tempfile
import numpy as np
from PIL import Image
from playwright.async_api import async_playwright

TARGET = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "/home/claude/psb/ProgSheetGenV36.html")
THEME = sys.argv[2] if len(sys.argv) > 2 else "classic"

FILL = """
() => {
  const m = state.meeting;
  m.title = 'National Day: Voices of a Nation';
  m.dateDisplay = 'Thursday, 13/08/2026';
  Object.keys(state.roles).forEach((k, i) => { state.roles[k] = 'Member Name ' + (i + 1); });
  state.announcementsText = '24/09/2026 - Nee Soon East Table Topics and Evaluations Contest. '
    + 'If you are interested to contest or support in the organisation of the contest, please '
    + 'approach the Contest Chair or any of the Exco members to get more information.';
  state.segments.filter(s => s.isSpeech).forEach((s, i) => {
    s.speakerName = 'Speaker Name ' + (i + 1);
    s.speechTitle = 'A Speech Title';
    s.pathway = 'PM'; s.pLevel = '1'; s.project = 'Ice Breaker';
  });
  state.segments.filter(s => s.isEvaluation).forEach((s, i) => {
    s.holderOverride = 'Evaluator Name ' + (i + 1);
    s.speakerName = 'Speaker Name ' + (i + 1);
  });
  renderPreviewNow();
}
"""

CAPTURE = """
async (kind) => {
  /* saveBlob is called and NOT awaited by the export path, so the capture has to
     take the blob SYNCHRONOUSLY and serialise afterwards. An async replacement
     that awaited arrayBuffer() inside itself returned an empty list every time:
     pickDownload had already resolved. */
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


def seams(png_path, label):
    im = Image.open(png_path).convert("RGB")
    a = np.asarray(im).astype(int)
    H, W, _ = a.shape
    left, right = np.roll(a, 1, axis=1), np.roll(a, -1, axis=1)
    d = (np.abs(a - left).sum(2) > 8) & (np.abs(a - right).sum(2) > 8)
    d[:, 0] = d[:, -1] = False
    counts = d.sum(0)
    # The content box: A4 less 10mm margins each side.
    box0, box1 = round(W * 10 / 210), round(W * 200 / 210)
    hits = [(x, counts[x]) for x in range(box0 + 2, box1 - 2) if counts[x] > H * 0.45]
    print(f"  {label}: {W}x{H}")
    for x, c in hits:
        frac = (x - box0) / (box1 - box0)
        print(f"     x={x:5d}  {c/H*100:5.1f}% of height   {frac*100:5.1f}% across the sheet")
    if not hits:
        print("     no vertical seam")
    return hits


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={"width": 1440, "height": 900})
        await ctx.route("http*://**", lambda r: asyncio.ensure_future(r.abort()))
        pg = await ctx.new_page()
        pg.on("pageerror", lambda e: print("  PAGEERROR:", e))
        await pg.goto("file://" + TARGET)
        await pg.wait_for_function("() => typeof state !== 'undefined'", timeout=20000)
        await pg.wait_for_timeout(900)
        await pg.evaluate("t => { state.theme = t; }", THEME)
        await pg.evaluate(FILL)
        await pg.wait_for_timeout(500)

        out = tempfile.mkdtemp(prefix="seam-")
        for kind in ("pdf", "jpg"):
            got = await pg.evaluate(CAPTURE, kind)
            if not got:
                print(f"  {kind}: nothing captured")
                continue
            for g in got:
                path = os.path.join(out, g["name"])
                open(path, "wb").write(base64.b64decode(g["b64"]))
                print(f"\n== {g['name']} ({os.path.getsize(path)} bytes)")
                if path.lower().endswith(".pdf"):
                    subprocess.run(["pdftoppm", "-r", "150", "-png", path,
                                    os.path.join(out, "pg")], check=True)
                    for f in sorted(os.listdir(out)):
                        if f.startswith("pg-") and f.endswith(".png"):
                            seams(os.path.join(out, f), f)
                else:
                    seams(path, g["name"])
        print("\nartefacts in", out)
        await b.close()

asyncio.run(main())
