"""Left-pane export probe.

The user reports that "for some of the themes, when generating the PDF, the pane
on the left disappears".  The PDF and the images do not print: they go through
renderSheetCanvas() -> html2canvas, and html2canvas has a long tail of CSS it
silently cannot paint.  So the first question is not "is the pane in the DOM" but
"did html2canvas put ink where the pane is".

RESULT: it did, in all six themes, in both builds - the rasterised canvas is a
pixel match for the screen in the pane column, so html2canvas is NOT the fault.
The pane is lost further downstream, in the page slicing; see pdfdiag.py, which
is the probe that actually reproduces the complaint.

For every build x theme x (blank | filled) this:

  * calls the app's OWN renderSheetCanvas(), so the export path is exercised
    exactly as shipped, and reads the canvas back (downscaled to the sheet's
    900px design width so the coordinates match the screenshot),
  * screenshots the same sheet in SCREEN media at the same 900px width - that is
    the ground truth for what the pane is meant to look like,
  * counts non-white pixels in the pane column (x < 200px of 900) and in the
    agenda column, in both images, and calls the export a FAIL when the pane has
    lost the bulk of its ink relative to the screen.

    python3 tests/diag/panediag.py            # both builds, all six themes
    python3 tests/diag/panediag.py --themes zine,swiss --builds v30
"""
import argparse, asyncio, base64, io, json, os, sys

import numpy as np
from PIL import Image
from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')

BUILDS = {'v29': '/tmp/V29.html', 'v30': '/home/claude/psb/ProgSheetGenV30.html'}
THEMES = ['classic', 'zine', 'swiss', 'brutalist', 'neomemphis']

SHEET_W = 900          # IMAGE_WIDTH in 06_app2.js, and .page max-width on screen
PANE_W = 200           # .body-grid grid-template-columns: 200px 1fr

# The same fill the page-count probe uses, so the two diagnostics talk about the
# same document.
FILL = """
() => {
  const m = state.meeting;
  m.title = 'Chapter Meeting: Voices of a Nation';
  m.dateDisplay = 'Thursday, 13 August 2026';
  Object.keys(state.roles).forEach((k, i) => { state.roles[k] = 'Member Name ' + (i + 1); });
  state.announcementsText = 'Club anniversary dinner, 20 Sept\\nArea contest briefing after the meeting';
  const sp = state.segments.filter(s => s.isSpeech);
  sp.forEach((s, i) => {
    s.speakerName = 'Speaker Name ' + (i + 1);
    s.speechTitle = 'A Speech Title That Runs Reasonably Long';
    s.pathway = 'DL'; s.pLevel = '1'; s.project = 'Ice Breaker';
  });
  state.segments.filter(s => s.isEvaluation).forEach((s, i) => {
    s.holderOverride = 'Evaluator Name ' + (i + 1);
    s.speakerName = 'Speaker Name ' + (i + 1);
  });
}
"""

# renderSheetCanvas() returns a 2700px-wide canvas (900 x scale 3).  Handing that
# back as a data URL is tens of megabytes of base64, so it is stepped down with
# the app's own downscaler to the 900px design width first - the pane either has
# ink at that size or it does not.  EXTRA_CSS, when set, is appended to the
# override stylesheet inside the export iframe; that is the bisection lever.
GRAB = """
async (extraCss) => {
  window.__diagExtraCss = extraCss || '';
  const c = await renderSheetCanvas();
  const d = c.width > 900 ? downscaleCanvas(c, 900) : c;
  return { url: d.toDataURL('image/png'), w: c.width, h: c.height };
}
"""

# renderSheetCanvas() has no hook for extra CSS, and patching the iframe's
# appendChild from out here does not work - the iframe is a separate realm, so
# idoc.head.appendChild is the FRAME's Node.prototype.appendChild, not ours.
# buildSheetHTML() is the one thing both paths go through, so the bisection
# stylesheet is spliced into the document it returns.  It lands last in <head>,
# after SHEET_CSS, so a plain declaration already wins; !important is only needed
# against the app's own override sheet, which renderSheetCanvas appends later.
PATCH_EXTRA_CSS = """
() => {
  if (window.__diagPatched) return;
  window.__diagPatched = true;
  const orig = window.buildSheetHTML;
  window.buildSheetHTML = function (interactive) {
    const html = orig.call(this, interactive);
    if (!window.__diagExtraCss) return html;
    return html.replace('</head>', '<style>' + window.__diagExtraCss + '</style></head>');
  };
}
"""

# The override stylesheet renderSheetCanvas() injects, replicated for the screen
# reference so the two images are of the same object.
SCREEN_FIX = (
    'html,body{background:#fff!important;margin:0!important;padding:0!important}'
    '.page-wrap{padding:0!important;display:block!important}'
    '.page{box-shadow:none!important;border-radius:0!important;'
    'max-width:none!important;width:100%!important}'
    '.print-fab{display:none!important}'
    '.schedule-note{display:none!important}'
)


def box(img, x0, x1, y0=0, y1=None):
    a = np.asarray(img.convert('RGB')).astype(np.int16)
    y1 = a.shape[0] if y1 is None else min(y1, a.shape[0])
    return a[y0:y1, x0:min(x1, a.shape[1])]


def ink(b):
    """Fraction of pixels that are not near-white."""
    if b.size == 0:
        return 0.0
    dark = b.min(axis=2) < 243
    tint = (b.max(axis=2) - b.min(axis=2)) > 6
    return float((dark | tint).mean())


def detail(b):
    """Fraction of pixels sitting on a hard edge.

    A tinted pane (zine, handmade) is 100% "ink" whether or not its CONTENT
    rendered, so ink alone cannot see the failure.  Text, rules and the brand box
    all produce steep local gradients; an empty pane - flat fill or bare white -
    produces almost none.  This is the metric that actually separates them.
    """
    if b.size == 0:
        return 0.0
    g = b.mean(axis=2)
    dx = np.abs(np.diff(g, axis=1))
    dy = np.abs(np.diff(g, axis=0))
    return float(((dx > 24).sum() + (dy > 24).sum()) / max(g.size, 1))


def load_dataurl(url):
    return Image.open(io.BytesIO(base64.b64decode(url.split(',', 1)[1])))


async def sheet_page(ctx, html, extra_css=''):
    """The clean sheet in SCREEN media at the export width - the ground truth."""
    p = await ctx.new_page()
    await p.set_viewport_size({'width': SHEET_W, 'height': 1200})
    await p.set_content(html, wait_until='load')
    # extra_css is already spliced in by the buildSheetHTML wrapper, so both the
    # export and this reference see the same bisected stylesheet.
    await p.add_style_tag(content=SCREEN_FIX)
    await p.wait_for_timeout(250)
    return p


LONG = """
() => {
  state.announcementsText = Array.from({length: 12},
    (_, i) => 'Announcement line number ' + (i + 1) + ' with a fair amount of text on it').join('\\n');
  for (let i = 0; i < 22; i++) {
    const s = Object.assign(newSegment('custom'), {
      title: 'Extra Agenda Segment ' + (i + 1), minutes: 4,
      holderOverride: 'Some Member Name ' + (i + 1) });
    state.segments.splice(state.segments.length - 2, 0, s);
  }
}
"""


async def run(builds, themes, fills, extra_css='', tag='', long=False):
    rows = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        for bname in builds:
            path = BUILDS[bname]
            ctx = await browser.new_context(viewport={'width': 1280, 'height': 900})
            # Google Fonts is unreachable here; fail the requests fast instead of
            # waiting out the 4s fonts.ready race on every render.
            await ctx.route('**/fonts.googleapis.com/**', lambda r: asyncio.ensure_future(r.abort()))
            await ctx.route('**/fonts.gstatic.com/**', lambda r: asyncio.ensure_future(r.abort()))
            page = await ctx.new_page()
            await page.goto('file://' + path)
            await page.wait_for_timeout(600)
            await page.evaluate(PATCH_EXTRA_CSS)
            for filled in fills:
                if filled:
                    await page.evaluate(FILL)
                    if long:
                        await page.evaluate(LONG)
                for theme in themes:
                    await page.evaluate("t => { state.theme = t; }", theme)
                    stem = '%s_%s_%s%s' % (bname, 'filled' if filled else 'blank', theme,
                                           ('_' + tag if tag else ''))

                    got = await page.evaluate(GRAB, extra_css)
                    exp = load_dataurl(got['url'])
                    exp.save(os.path.join(OUT, stem + '_export.png'))

                    html = await page.evaluate("() => buildSheetHTML(false)")
                    sp = await sheet_page(ctx, html, extra_css)
                    shot = await sp.locator('.page').screenshot()
                    await sp.close()
                    scr = Image.open(io.BytesIO(shot))
                    scr.save(os.path.join(OUT, stem + '_screen.png'))

                    # The builder's own live preview, so a pane that is missing
                    # everywhere can be told apart from one missing only in the
                    # export.  Interactive markup, hence measured on its own.
                    await page.evaluate("() => renderPreviewNow()")
                    await page.wait_for_timeout(250)
                    pv = await page.frame_locator('#previewFrame').locator('.page').screenshot()
                    pvi = Image.open(io.BytesIO(pv))
                    pvi.save(os.path.join(OUT, stem + '_preview.png'))
                    pw_ = round(PANE_W * pvi.width / SHEET_W)
                    p_pane = detail(box(pvi, 4, pw_ - 4))

                    # Compare only over the height both images share, and skip the
                    # outermost 4px so a 1px theme border cannot pass as a pane.
                    h = min(exp.height, scr.height)
                    ep, sp_ = box(exp, 4, PANE_W - 4, 0, h), box(scr, 4, PANE_W - 4, 0, h)
                    em, sm = box(exp, PANE_W + 30, SHEET_W - 20, 0, h), box(scr, PANE_W + 30, SHEET_W - 20, 0, h)
                    e_pane, s_pane = detail(ep), detail(sp_)
                    e_main, s_main = detail(em), detail(sm)
                    ratio = (e_pane / s_pane) if s_pane > 1e-6 else 0.0
                    rows.append(dict(build=bname, fill='filled' if filled else 'blank',
                                     theme=theme, canvas=[got['w'], got['h']],
                                     exp_h=exp.height, scr_h=scr.height,
                                     e_pane=round(e_pane, 4), s_pane=round(s_pane, 4),
                                     e_main=round(e_main, 4), s_main=round(s_main, 4),
                                     e_ink=round(ink(ep), 4), s_ink=round(ink(sp_), 4),
                                     p_pane=round(p_pane, 4), p_w=pvi.width,
                                     ratio=round(ratio, 3),
                                     verdict='PASS' if ratio >= 0.5 else 'FAIL'))
                    print(json.dumps(rows[-1]), flush=True)
            await ctx.close()
        await browser.close()
    return rows


def table(rows):
    hdr = '%-5s %-7s %-12s %8s %8s %8s %6s %7s %7s  %s' % (
        'build', 'fill', 'theme', 'exp_pane', 'scr_pane', 'prv_pane', 'ratio',
        'exp_ink', 'scr_ink', 'verdict')
    print('\n' + hdr)
    print('-' * len(hdr))
    for r in rows:
        print('%-5s %-7s %-12s %8.4f %8.4f %8.4f %6.2f %7.3f %7.3f  %s' % (
            r['build'], r['fill'], r['theme'], r['e_pane'], r['s_pane'],
            r.get('p_pane', 0), r['ratio'], r['e_ink'], r['s_ink'],
            r['verdict']))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--builds', default='v29,v30')
    ap.add_argument('--themes', default=','.join(THEMES))
    ap.add_argument('--fills', default='blank,filled')
    ap.add_argument('--extra-css', default='')
    ap.add_argument('--extra-css-file', default='')
    ap.add_argument('--tag', default='')
    ap.add_argument('--long', action='store_true',
                    help='pad the agenda so the sheet runs to three A4 pages')
    a = ap.parse_args()
    css = a.extra_css
    if a.extra_css_file:
        css = open(a.extra_css_file).read()
    os.makedirs(OUT, exist_ok=True)
    rows = asyncio.run(run(a.builds.split(','), a.themes.split(','),
                           [f == 'filled' for f in a.fills.split(',')], css, a.tag, a.long))
    table(rows)
    json.dump(rows, open(os.path.join(OUT, 'results%s.json' % (('_' + a.tag) if a.tag else '')), 'w'), indent=1)
    sys.exit(1 if any(r['verdict'] == 'FAIL' for r in rows) else 0)
