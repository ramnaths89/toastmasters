"""Which structural feature of Rama's sheet produces the vertical seam?

His export has a full-height translucent line at 49.3% of the content width on
every page; a fully-filled synthetic sheet does not. This runs the app's real PDF
export over several variants and reports the full-height rules in each, so the
difference is identified rather than guessed at.

    python3 tests/seamvariants.py [file.html]
"""
import asyncio, base64, os, subprocess, sys, tempfile
import numpy as np
from PIL import Image
from playwright.async_api import async_playwright

TARGET = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "/home/claude/psb/ProgSheetGenV36.html")

BASE = """
  const m = state.meeting;
  m.title = 'National Day: Voices of a Nation';
  m.dateDisplay = 'Thursday, 13/08/2026';
  m.location = 'Nee Soon East Community Club, 1 Yishun Ave 9, #04-01 (Culinary Studio), Singapore 768893';
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
"""

VARIANTS = [
    ("all roles filled", BASE + """
  Object.keys(state.roles).forEach((k, i) => { state.roles[k] = 'Member Name ' + (i + 1); });
"""),
    ("two roles left open (TBD chips + still-open notice)", BASE + """
  Object.keys(state.roles).forEach((k, i) => { state.roles[k] = 'Member Name ' + (i + 1); });
  state.roles.saa = ''; state.roles.photographer = '';
  Object.keys(state.roles).forEach(k => { if(/photo|saa|sergeant/i.test(k)) state.roles[k] = ''; });
"""),
    ("no roles filled at all", BASE + """
  Object.keys(state.roles).forEach(k => { state.roles[k] = ''; });
"""),
    ("blank template, nothing typed", "  /* defaults only */"),
]

CAPTURE = """
async () => {
  const blobs = [];
  const realSave = saveBlob;
  saveBlob = (blob, name) => { blobs.push({blob, name}); };
  try { await downloadPdfImage(); } finally { saveBlob = realSave; }
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


def rules(png):
    a = np.asarray(Image.open(png).convert("RGB")).astype(int)
    H, W, _ = a.shape
    l, r = np.roll(a, 1, axis=1), np.roll(a, -1, axis=1)
    d = (np.abs(a - l).sum(2) > 8) & (np.abs(a - r).sum(2) > 8)
    d[:, 0] = d[:, -1] = False
    c = d.sum(0)
    hits = [x for x in range(1, W - 1) if c[x] > H * 0.5]
    groups = []
    for x in hits:
        if groups and x - groups[-1][-1] <= 2:
            groups[-1].append(x)
        else:
            groups.append([x])
    return [round(float(np.mean(g)) / W * 100, 2) for g in groups]


async def main():
    out = tempfile.mkdtemp(prefix="variants-")
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={"width": 1440, "height": 900})
        for i, (label, js) in enumerate(VARIANTS):
            pg = await ctx.new_page()
            await pg.goto("file://" + TARGET)
            await pg.wait_for_function("() => typeof state !== 'undefined'", timeout=20000)
            await pg.wait_for_timeout(2500)
            await pg.evaluate("() => { resetToDefaults && 0; }")
            await pg.evaluate("() => {" + js + " renderPreviewNow(); }")
            await pg.wait_for_timeout(900)
            got = await pg.evaluate(CAPTURE)
            print(f"\n== {label}")
            for g in got:
                path = os.path.join(out, f"v{i}.pdf")
                open(path, "wb").write(base64.b64decode(g["b64"]))
                subprocess.run(["pdftoppm", "-r", "150", "-png", path,
                                os.path.join(out, f"v{i}")], check=True)
                for f in sorted(os.listdir(out)):
                    if f.startswith(f"v{i}-") and f.endswith(".png"):
                        print(f"   {f}: full-height rules at {rules(os.path.join(out, f))}%")
            await pg.close()
        await b.close()
    print("\nartefacts in", out)

asyncio.run(main())
