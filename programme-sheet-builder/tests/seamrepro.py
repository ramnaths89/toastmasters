"""Reproduce Rama's 13 Aug 2026 sheet field-for-field and look for the seam.

Every name, title, project and TBD is read off the PDF he sent. If the line
appears here it can be bisected; if it does not, the cause is on his machine and
the next step is his .nse.json rather than more guessing.

    python3 tests/seamrepro.py [file.html]
"""
import asyncio, base64, os, subprocess, sys, tempfile
import numpy as np
from PIL import Image
from playwright.async_api import async_playwright

TARGET = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "/home/claude/psb/ProgSheetGenV36.html")

SHEET = r"""
() => {
  const m = state.meeting;
  m.title = 'National Day: Voices of a Nation';
  m.dateDisplay = 'Thursday, 13/08/2026';
  m.startTime = '19:00'; m.endTime = '21:30';
  m.location = 'Nee Soon East Community Club, 1 Yishun Ave 9, #04-01 (Culinary Studio), Singapore 768893';
  m.cadence = 'We meet every 2nd and 4th Thursday of the month from 7:00PM to 9:30PM';

  /* Roles as printed, including the two left open. */
  const want = {
    tme: 'Tharaka Madhusanka',
    ttmaster: 'Nan Zheng',
    timer: 'Jordan Lee, SR4',
    ahcounter: 'Rebecca Wang',
    grammarian: '',
    saa: '',
    photographer: '',
  };
  Object.keys(state.roles).forEach(k => { state.roles[k] = ''; });
  Object.keys(state.roles).forEach(k => {
    const lk = k.toLowerCase();
    if (/tme|toastmaster/.test(lk) && !/table/.test(lk)) state.roles[k] = want.tme;
    else if (/tt|tabletopic/.test(lk)) state.roles[k] = want.ttmaster;
    else if (/timer/.test(lk)) state.roles[k] = want.timer;
    else if (/ah/.test(lk)) state.roles[k] = want.ahcounter;
  });

  const sp = [
    ['Wei Chen', 'Seven Centuries, Seven Views', 'PM', '1', 'Writing a Speech with Purpose', 'Kim Wong, MS4'],
    ['Riley Ong', 'Bike Riding with my Girl', 'VC', '1', 'Evaluation and Feedback (1st Speech)', 'Alex Tan, PM2'],
    ['Riley Ong', 'The Secret Ingredient', 'DL', '1', 'Evaluation and Feedback (2nd Speech)',
     'Joseph Lane, EH1 (Tampines Changkat TMC)'],
    ['Amir Hassan, PM2', 'Dream On', 'PM', '2', 'Introduction to Toastmasters Mentoring', 'Jordan Lee, SR4'],
  ];
  const speeches = state.segments.filter(s => s.isSpeech);
  speeches.forEach((s, i) => {
    const d = sp[i]; if (!d) return;
    s.speakerName = d[0]; s.speechTitle = d[1];
    s.pathway = d[2]; s.pLevel = d[3]; s.project = d[4];
    s.holderOverride = d[5];
  });
  state.segments.filter(s => s.isEvaluation).forEach((s, i) => {
    const d = sp[i]; if (!d) return;
    s.speakerName = d[0]; s.holderOverride = d[5];
  });

  state.announcementsText = '24/09/2026 - Nee Soon East Table Topics and Evaluations Contest. '
    + 'If you\'re interested to contest or support in the organisation of the contest, '
    + 'please approach the Contest Chair or any of the Exco members to get more information.';
  renderPreviewNow();
}
"""

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
    pct = [round(float(np.mean(g)) / W * 100, 2) for g in groups]
    print(f"   {label}: {W}x{H} full-height rules at {pct}%")
    return pct


async def main():
    out = tempfile.mkdtemp(prefix="repro-")
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for dsf in (1, 1.25, 1.5, 2):
          ctx = await b.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=dsf)
          print(f"\n######## deviceScaleFactor = {dsf}")
          pg = await ctx.new_page()
          pg.on("pageerror", lambda e: print("   PAGEERROR:", e))
          await pg.goto("file://" + TARGET)
          await pg.wait_for_function("() => typeof state !== 'undefined'", timeout=20000)
          await pg.wait_for_timeout(2500)
          await pg.evaluate(SHEET)
          await pg.wait_for_timeout(900)
          got = await pg.evaluate(CAPTURE, "pdf")
          for g in got:
            tag = str(dsf).replace(".", "_")
            path = os.path.join(out, f"r{tag}.pdf")
            open(path, "wb").write(base64.b64decode(g["b64"]))
            subprocess.run(["pdfimages", "-j", path, os.path.join(out, f"im{tag}")], check=True)
            for f in sorted(os.listdir(out)):
                if f.startswith(f"im{tag}-") and f.endswith((".jpg", ".ppm")):
                    rules(os.path.join(out, f), f)
          await ctx.close()
    print("\nartefacts in", out)

asyncio.run(main())
