"""Reproduce the vertical seam through the BROWSER PRINT path (Ctrl+P), not the
app's own PDF export.

Rama's file is a browser print, not a Download > PDF: its background is the sheet's
cream paper bled to the paper edge and its ink runs to 95% of the page width, where
the app's exporter forces #ffffff and stops at 88%. Those two paths use different
layouts, so a defect in one says nothing about the other.

    python3 tests/printseam.py <file.html> [theme]
"""
import asyncio, os, subprocess, sys, tempfile
import numpy as np
from PIL import Image
from playwright.async_api import async_playwright

TARGET = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "/home/claude/psb/ProgSheetGenV36.html")
THEMES = [sys.argv[2]] if len(sys.argv) > 2 else ["classic", "zine", "swiss", "brutalist", "neomemphis"]

FILL = """
() => {
  const m = state.meeting;
  m.title = 'National Day: Voices of a Nation';
  m.dateDisplay = 'Thursday, 13/08/2026';
  m.location = 'Nee Soon East Community Club, 1 Yishun Ave 9, #04-01 (Culinary Studio), Singapore 768893';
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


def rules(png, label):
    a = np.asarray(Image.open(png).convert("RGB")).astype(int)
    H, W, _ = a.shape
    l, r = np.roll(a, 1, axis=1), np.roll(a, -1, axis=1)
    d = (np.abs(a - l).sum(2) > 8) & (np.abs(a - r).sum(2) > 8)
    d[:, 0] = d[:, -1] = False
    c = d.sum(0)
    hits = [x for x in range(1, W - 1) if c[x] > H * 0.55]
    groups = []
    for x in hits:
        if groups and x - groups[-1][-1] <= 2:
            groups[-1].append(x)
        else:
            groups.append([x])
    bg = tuple(int(v) for v in np.median(a.reshape(-1, 3), axis=0))
    out = [round(float(np.mean(g)) / W * 100, 1) for g in groups]
    print(f"    {label}: {W}x{H} bg={bg} full-height rules at {out}% of page width")
    return out


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={"width": 1440, "height": 900})
        await ctx.route("http*://**", lambda r: asyncio.ensure_future(r.abort()))
        pg = await ctx.new_page()
        await pg.goto("file://" + TARGET)
        await pg.wait_for_function("() => typeof state !== 'undefined'", timeout=20000)
        await pg.wait_for_timeout(900)
        await pg.evaluate(FILL)
        await pg.wait_for_timeout(400)

        out = tempfile.mkdtemp(prefix="printseam-")
        sheet = await ctx.new_page()
        for theme in THEMES:
            await pg.evaluate("t => { state.theme = t; renderPreviewNow(); }", theme)
            await pg.wait_for_timeout(200)
            html = await pg.evaluate("() => buildSheetHTML(false)")
            await sheet.set_content(html, wait_until="domcontentloaded")
            await sheet.emulate_media(media="print")
            await sheet.wait_for_timeout(400)
            pdf = os.path.join(out, f"{theme}.pdf")
            await sheet.pdf(path=pdf, format="A4", print_background=True,
                            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
            subprocess.run(["pdftoppm", "-r", "150", "-png", pdf,
                            os.path.join(out, theme)], check=True)
            print(f"\n  == {theme}")
            for f in sorted(os.listdir(out)):
                if f.startswith(theme + "-") and f.endswith(".png"):
                    rules(os.path.join(out, f), f)
        print("\n  artefacts in", out)
        await b.close()

asyncio.run(main())
