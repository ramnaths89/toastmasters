"""Proof that the candidate fix does not touch PAPER.

The fix recolours the swiss and brutalist reference pane, which is exactly the
kind of change that can leak into print - the print block's
aside.ref-pane{background:#fff} is only specificity 0-1-1 and the swiss theme
rule was 0-1-2, so it outranked it.  This prints both builds to PDF in PRINT
media and compares the rendered pages pixel for pixel.

    python3 tests/diag/printcheck.py [--themes swiss,brutalist]
"""
import argparse, asyncio, glob, os, subprocess, sys

import numpy as np
from PIL import Image
from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out', 'print')
sys.path.insert(0, HERE)
from panediag import BUILDS, THEMES, FILL  # noqa: E402


async def render(builds, themes, fills):
    os.makedirs(OUT, exist_ok=True)
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        for bname in builds:
            ctx = await browser.new_context(viewport={'width': 718, 'height': 1000})
            await ctx.route('**/fonts.g*/**', lambda r: asyncio.ensure_future(r.abort()))
            page = await ctx.new_page()
            await page.goto('file://' + BUILDS[bname])
            await page.wait_for_timeout(600)
            for filled in fills:
                if filled:
                    await page.evaluate(FILL)
                for theme in themes:
                    await page.evaluate("t => { state.theme = t; }", theme)
                    html = await page.evaluate("() => buildSheetHTML(false)")
                    sh = await ctx.new_page()
                    await sh.set_viewport_size({'width': 718, 'height': 1000})
                    await sh.set_content(html, wait_until='load')
                    await sh.emulate_media(media='print')
                    await sh.wait_for_timeout(250)
                    stem = '%s_%s_%s' % (bname, 'filled' if filled else 'blank', theme)
                    pdf = os.path.join(OUT, stem + '.pdf')
                    await sh.pdf(path=pdf, format='A4', print_background=True,
                                 margin={'top': '0', 'bottom': '0', 'left': '0', 'right': '0'})
                    await sh.close()
                    for old in glob.glob(os.path.join(OUT, stem + '-*.png')):
                        os.unlink(old)
                    subprocess.run(['pdftoppm', '-png', '-r', '80', pdf,
                                    os.path.join(OUT, stem)], check=True)
            await ctx.close()
        await browser.close()


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--builds', default='v30,fix')
    ap.add_argument('--themes', default=','.join(THEMES))
    ap.add_argument('--fills', default='blank,filled')
    a = ap.parse_args()
    builds = a.builds.split(',')
    asyncio.run(render(builds, a.themes.split(','),
                       [f == 'filled' for f in a.fills.split(',')]))
    base, other = builds[0], builds[1]
    bad = 0
    for fill in a.fills.split(','):
        for th in a.themes.split(','):
            for p in sorted(glob.glob(os.path.join(OUT, '%s_%s_%s-*.png' % (base, fill, th)))):
                q = p.replace('%s_%s' % (base, fill), '%s_%s' % (other, fill), 1)
                x = np.asarray(Image.open(p).convert('RGB')).astype(int)
                y = np.asarray(Image.open(q).convert('RGB')).astype(int)
                d = int(np.abs(x - y).max()) if x.shape == y.shape else 999
                n = int((np.abs(x - y).max(axis=2) > 2).sum()) if x.shape == y.shape else -1
                bad += (d > 2)
                print('%-34s maxdiff=%3d  pixels-differing=%d' % (os.path.basename(p), d, n))
    print('\nprint-media differences:', bad)
    sys.exit(1 if bad else 0)
