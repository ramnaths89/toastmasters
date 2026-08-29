"""End-to-end PDF probe: does the pane survive onto every page of the file the
user actually gets?

panediag.py proves the pane is in the rasterised canvas.  This drives the real
downloadPdfImage() - saveBlob() is intercepted so the PDF is captured instead of
downloaded - renders every page with pdftoppm, and measures the pane column on
each page separately.

That per-PAGE split is the point.  The export rasterises the sheet in SCREEN
media, where the pane is an ordinary grid column whose content stops after about
1200px; downloadPdfImage() then slices that one tall canvas at fixed A4 heights.
The pane's position:fixed repeat lives only in @media print, which the export
never enters - so page 2 onwards used to get an empty pane column, and in the
themes whose pane fill equals the paper (swiss, brutalist) that column was
invisible.  That is what the user saw.

downloadPdfImage() now repaints the pane onto every page after the first from a
separate raster (renderSheetParts().pane), so this measures, per page:

  edges   pane-column edge density - real CONTENT, not just a tinted column
  ink     fraction of the pane column that is not near-white
  bg      modal colour of the pane column vs the modal colour of the paper
  algn    where the pane's column rule actually lands, vs where the column ends
  bleed   ink from the pane raster spilling right of the column boundary

    python3 tests/diag/pdfdiag.py [--builds v30] [--themes swiss,classic] [--long]
"""
import argparse, asyncio, base64, glob, json, os, subprocess, sys
from collections import Counter

import numpy as np
from PIL import Image
from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out', 'pdf')
BUILDS = {'v29': '/tmp/V29.html', 'v30': '/home/claude/psb/ProgSheetGenV30.html'}
THEMES = ['classic', 'zine', 'swiss', 'brutalist', 'neomemphis']

sys.path.insert(0, HERE)
from panediag import FILL, LONG, PATCH_EXTRA_CSS  # noqa: E402

# Isolates the byte cost of the repeated pane: renderSheetParts() still runs, but
# the pane raster is dropped, so downloadPdfImage() falls back to the old
# empty-column behaviour and the two file sizes are directly comparable.
NO_PANE = """
() => {
  if (window.__noPane) return;
  window.__noPane = true;
  const orig = window.renderSheetParts;
  window.renderSheetParts = async function () {
    const p = await orig.apply(this, arguments);
    return Object.assign({}, p, {pane: null, paneFrac: 0});
  };
}
"""

CAPTURE = """
async () => {
  window.__pdf = null;
  const orig = window.saveBlob;
  window.saveBlob = (blob, name) => { window.__blob = blob; };
  let err = null;
  try { await downloadPdfImage(); } catch (e) { err = String(e && e.message || e); }
  window.saveBlob = orig;
  if (!window.__blob) return { err: err || 'saveBlob never called' };
  const buf = new Uint8Array(await window.__blob.arrayBuffer());
  let s = '';
  for (let i = 0; i < buf.length; i += 8192) {
    s += String.fromCharCode.apply(null, buf.subarray(i, i + 8192));
  }
  window.__blob = null;
  return { b64: btoa(s), err: err };
}
"""


PANE_FRAC = 200 / 900.0     # .body-grid grid-template-columns: 200px 1fr


def pane_stats(png):
    """Everything measured off one rendered PDF page.

    Coordinates come from the page itself, not from an assumption: the sheet is
    inset by the 10mm PDF margin, and the pane column is the first 200/900 of
    what is left.  `rule_x` is found rather than assumed, so a pane raster drawn
    a few pixels off would show up as a mismatch instead of being averaged away.
    """
    a = np.asarray(Image.open(png).convert('RGB')).astype(np.int16)
    h, w = a.shape[:2]
    m = int(round(w * 10 / 210.0))
    sheet_w = w - 2 * m
    x_edge = m + int(round(sheet_w * PANE_FRAC))      # expected right edge of the pane
    pane = a[:, m + 2:x_edge - 2]
    g = pane.mean(axis=2)
    edges = ((np.abs(np.diff(g, axis=1)) > 24).sum()
             + (np.abs(np.diff(g, axis=0)) > 24).sum()) / max(g.size, 1)
    notwhite = ((pane.min(axis=2) < 243) | ((pane.max(axis=2) - pane.min(axis=2)) > 6)).mean()

    # Vertical extent of the sheet on this page, so the paper below it does not
    # dominate the modal colours.
    body = a[:, m:m + sheet_w]
    rr = np.where(body.reshape(h, -1, 3).min(axis=(1, 2)) < 250)[0]
    y0, y1 = (rr.min() + 4, rr.max() - 4) if len(rr) > 8 else (0, h)

    def modal(x0, x1):
        c = Counter(map(tuple, a[y0:y1, x0:x1].reshape(-1, 3)))
        return tuple(int(v) for v in c.most_common(1)[0][0])

    pane_bg = modal(m + 6, x_edge - 6)
    page_bg = modal(m + int(sheet_w * 0.55), m + sheet_w - 6)

    # The column rule: darkest vertical line within a few px of the boundary.
    band = a[y0:y1, x_edge - 8:x_edge + 8].mean(axis=(0, 2))
    rule_x = int(np.argmin(band)) - 8 if band.size else 99

    # Bleed: pane content spilling INTO the agenda column, just right of the rule.
    right = a[y0:y1, x_edge + 3:x_edge + 12]
    bleed = float(((right.min(axis=2) < 200)).mean())
    return dict(edges=round(float(edges), 4), ink=round(float(notwhite), 3),
                pane_bg=pane_bg, page_bg=page_bg,
                dbg=int(max(abs(p - q) for p, q in zip(pane_bg, page_bg))),
                rule_dx=rule_x, bleed=round(bleed, 4))


async def run(builds, themes, fills, extra_css='', tag='', long=False, no_pane=False):
    os.makedirs(OUT, exist_ok=True)
    rows = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        for bname in builds:
            ctx = await browser.new_context(viewport={'width': 1280, 'height': 900})
            await ctx.route('**/fonts.googleapis.com/**', lambda r: asyncio.ensure_future(r.abort()))
            await ctx.route('**/fonts.gstatic.com/**', lambda r: asyncio.ensure_future(r.abort()))
            page = await ctx.new_page()
            await page.goto('file://' + BUILDS[bname])
            await page.wait_for_timeout(600)
            await page.evaluate(PATCH_EXTRA_CSS)
            await page.evaluate("c => { window.__diagExtraCss = c; }", extra_css)
            if no_pane:
                await page.evaluate(NO_PANE)
            for filled in fills:
                if filled:
                    await page.evaluate(FILL)
                    if long:
                        await page.evaluate(LONG)
                for theme in themes:
                    await page.evaluate("t => { state.theme = t; }", theme)
                    stem = '%s_%s_%s%s' % (bname, 'filled' if filled else 'blank', theme,
                                           ('_' + tag if tag else ''))
                    got = await page.evaluate(CAPTURE)
                    if not got.get('b64'):
                        print('CAPTURE FAILED %s: %s' % (stem, got.get('err')), flush=True)
                        continue
                    pdf = os.path.join(OUT, stem + '.pdf')
                    open(pdf, 'wb').write(base64.b64decode(got['b64']))
                    for old in glob.glob(os.path.join(OUT, stem + '-*.png')):
                        os.unlink(old)
                    subprocess.run(['pdftoppm', '-png', '-r', '80', pdf,
                                    os.path.join(OUT, stem)], check=True)
                    pages = sorted(glob.glob(os.path.join(OUT, stem + '-*.png')))
                    per = [pane_stats(p) for p in pages]
                    rows.append(dict(build=bname, fill='filled' if filled else 'blank',
                                     theme=theme, pages=len(pages),
                                     bytes=os.path.getsize(pdf),
                                     kb=round(os.path.getsize(pdf) / 1024.0, 1),
                                     under_cap=os.path.getsize(pdf) <= 512000,
                                     edges=[p['edges'] for p in per],
                                     ink=[p['ink'] for p in per],
                                     dbg=[p['dbg'] for p in per],
                                     pane_bg=[p['pane_bg'] for p in per],
                                     rule_dx=[p['rule_dx'] for p in per],
                                     bleed=[p['bleed'] for p in per]))
                    print(json.dumps(rows[-1]), flush=True)
            await ctx.close()
        await browser.close()
    return rows


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--builds', default='v30')
    ap.add_argument('--themes', default=','.join(THEMES))
    ap.add_argument('--fills', default='blank,filled')
    ap.add_argument('--extra-css', default='')
    ap.add_argument('--tag', default='')
    ap.add_argument('--long', action='store_true')
    ap.add_argument('--no-pane', action='store_true',
                    help='drop the repeated pane raster, to price it')
    a = ap.parse_args()
    rows = asyncio.run(run(a.builds.split(','), a.themes.split(','),
                           [f == 'filled' for f in a.fills.split(',')],
                           a.extra_css, a.tag, a.long, a.no_pane))
    hdr = ('%-5s %-6s %-12s %5s %8s %5s  %-26s %-22s %-10s %s'
           % ('build', 'fill', 'theme', 'pages', 'KB', 'cap',
              'pane edge-density / page', 'pane-vs-paper d / page', 'rule dx', 'bleed'))
    print('\n' + hdr)
    print('-' * len(hdr))
    for r in rows:
        print('%-5s %-6s %-12s %5d %8.1f %5s  %-26s %-22s %-10s %s' % (
            r['build'], r['fill'], r['theme'], r['pages'], r['kb'],
            'ok' if r['under_cap'] else 'OVER',
            str(r['edges']), str(r['dbg']), str(r['rule_dx']), str(r['bleed'])))
    json.dump(rows, open(os.path.join(OUT, 'pdfresults%s.json'
                                      % (('_' + a.tag) if a.tag else '')), 'w'), indent=1)
