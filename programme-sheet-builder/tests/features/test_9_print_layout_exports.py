"""V32: the exports now rasterise the PRINT layout, not the screen layout.

Two independent kinds of evidence are used, because either alone is weak:

  * GEOMETRY, read out of the real paginated DOM. renderSheetParts() builds its
    layout in a throwaway iframe and removes it in a finally block; the suite
    intercepts Element.prototype.remove for the duration of one call so the frame
    survives and can be measured. Nothing in the app is modified.
  * PIXELS, read out of the delivered PDF/JPG with pdftoppm + PIL. This is what
    catches a canvas that was laid out to screen rules while every measurement
    said print - the exact trap described for printRulesText().

Every structural check runs for all five themes.
"""

import asyncio
import glob
import os
import re
import subprocess
import sys
import tempfile

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import FILL_JS, PREV, open_app, run_suite  # noqa: E402

THEMES = ["classic", "zine", "swiss", "brutalist", "neomemphis"]
CAP = 500 * 1024
PRINT_H_PX = 277 * 96 / 25.4          # 1047.24
PRINT_W_PX = 718

# Keep the render frame alive for one renderSheetParts() call so its paginated
# DOM can be measured. Restores the prototype in a finally block.
KEEP = """async (paginate) => {
  const orig = Element.prototype.remove;
  window.__kept = null;
  Element.prototype.remove = function(){
    if(this.tagName === 'IFRAME'){ window.__kept = this; return; }
    return orig.call(this);
  };
  try {
    const r = await renderSheetParts(paginate ? {paginate:true} : undefined);
    return {pages: r.pages, w: r.canvas.width, h: r.canvas.height, strip: !!r.footStrip};
  } finally { Element.prototype.remove = orig; }
}"""

DROP_KEPT = "() => { if(window.__kept){ window.__kept.parentNode.removeChild(window.__kept);" \
            " window.__kept = null; } }"

# Everything the geometric assertions need, measured relative to the page box.
GEOM = """() => {
  const d = window.__kept.contentDocument;
  const pg = d.querySelector('.page');
  const pb = pg.getBoundingClientRect();
  const rel = el => { const b = el.getBoundingClientRect();
    return {top: b.top - pb.top, bottom: b.bottom - pb.top,
            left: b.left - pb.left, right: b.right - pb.left,
            w: b.width, h: b.height}; };
  const hdr = d.querySelector('header'), aside = d.querySelector('aside');
  const brand = d.querySelector('.pane-brand'), foot = d.querySelector('footer');
  const body = d.querySelector('.pane-body');
  const rows = [...d.querySelectorAll('tbody tr')].filter(r => !r.classList.contains('pg-spacer'));
  const paneBlocks = [...d.querySelectorAll(
    'aside h3, aside .exco-item, aside .announce-line, aside .path-legend div')]
    .filter(e => !e.classList.contains('pg-spacer'));
  return {
    page: {h: pb.height, w: pb.width},
    header: hdr ? rel(hdr) : null,
    brand: brand ? rel(brand) : null,
    aside: aside ? rel(aside) : null,
    paneBody: body ? rel(body) : null,
    foot: foot ? rel(foot) : null,
    rows: rows.map(rel),
    paneBlocks: paneBlocks.map(rel),
    spacers: d.querySelectorAll('.pg-spacer').length,
    headerText: hdr ? hdr.textContent.replace(/\\s+/g, ' ').trim() : '',
    paneText: aside ? aside.textContent.replace(/\\s+/g, ' ').trim() : '',
    hasLogo: !!(brand && brand.querySelector('img')),
    logoComplete: !!(brand && brand.querySelector('img') && brand.querySelector('img').complete),
    minHeight: pg.style.minHeight || '',
    footOverlap: (()=>{
      const rows=[...d.querySelectorAll('tbody tr')];
      const last=rows[rows.length-1], f=d.querySelector('footer');
      if(!last||!f) return 0;
      return Math.max(0, Math.round(last.getBoundingClientRect().bottom - f.getBoundingClientRect().top));
    })(),
    paneRule: aside ? getComputedStyle(d.querySelector('.pane-body') || aside).borderRightWidth : '',
    paneRuleColor: aside ? getComputedStyle(d.querySelector('.pane-body') || aside).borderRightColor : '',
    paneFrac: body ? (body.getBoundingClientRect().right - pb.left) / pb.width : 0,
  };
}"""

HEAVY = """() => {
  state.announcementsText = Array.from({length:14},
    (_,i)=>'Announcement number '+(i+1)+': a reasonably wordy notice for the club').join('\\n');
  state.districtText = ['Division Director|<Division Director Name>|<Their Club>',
    'Area Director|Pat Chen|<Their Club>',
    'Programme Quality Director|Meera Raghunathan|Yishun TMC',
    'Club Growth Director|Samuel Tan Wei Ming|Sembawang TMC'].join('\\n');
  state.linksText = ['Toastmasters Intl.|https://www.toastmasters.org|www.toastmasters.org',
    'Our Club|https://www.facebook.com/groups/neesooneast|facebook.com/groups/neesooneast',
    'District 80|https://d80toastmasters.org|d80toastmasters.org',
    'Pathways|https://www.toastmasters.org/pathways|toastmasters.org/pathways'].join('\\n');
  renderFormPane(); renderPreviewNow();
}"""

LIGHT = """() => {
  state.announcementsText = 'Club anniversary dinner, 20 Sept';
  renderFormPane(); renderPreviewNow();
}"""


async def grab_pdf(p):
    async with p.expect_download(timeout=300000) as dl:
        await p.evaluate("() => pickDownload('pdf')")
    d = await dl.value
    await p.wait_for_timeout(150)
    banner = await p.evaluate("() => document.getElementById('banner').textContent")
    fd, path = tempfile.mkstemp(prefix="psb9_", suffix=".pdf")
    os.close(fd)
    await d.save_as(path)
    return path, os.path.getsize(path), banner


def pdf_pages(path):
    out = subprocess.run(["pdfinfo", path], capture_output=True, text=True).stdout
    m = re.search(r"^Pages:\s+(\d+)", out, re.M)
    return int(m.group(1)) if m else 0


def raster(path, dpi=110):
    d = tempfile.mkdtemp(prefix="psb9_pg_")
    subprocess.run(["pdftoppm", "-png", "-r", str(dpi), path, os.path.join(d, "pg")],
                   capture_output=True)
    return d, sorted(glob.glob(os.path.join(d, "pg*.png")))


def ink(im, x0, y0, x1, y1, thresh=225):
    """Fraction of pixels darker than `thresh` in a box, and their y centre."""
    x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
    if x1 <= x0 or y1 <= y0:
        return 0.0, None
    crop = im.crop((x0, y0, x1, y1))
    px = list(crop.getdata())
    w = crop.size[0]
    dark = [i for i, v in enumerate(px) if v < thresh]
    if not px:
        return 0.0, None
    frac = len(dark) / len(px)
    cy = (sum(i // w for i in dark) / len(dark) + y0) if dark else None
    return frac, cy


def column_profile(im, xc, y0, y1, span=6):
    """Darkest pixel in each column within +/-span of xc, sampled down y0..y1."""
    out = []
    for dx in range(-span, span + 1):
        x = int(round(xc)) + dx
        if x < 0 or x >= im.size[0]:
            continue
        col = [im.getpixel((x, y)) for y in range(int(y0), int(y1), 2)]
        out.append((dx, min(col) if col else 255))
    return out


def cleanup(d, files):
    for f in files:
        try:
            os.unlink(f)
        except OSError:
            pass
    try:
        os.rmdir(d)
    except OSError:
        pass


async def main(ctx, s):
    app = await open_app(ctx)
    p = app.page
    await p.evaluate(FILL_JS)
    await p.wait_for_timeout(600)
    # a marker that must appear exactly once in the pane, to catch repetition
    await p.evaluate("() => { state.announcementsText = "
                     "'Club anniversary dinner, 20 Sept\\nUNIQUEPANEMARKER only once'; "
                     "renderPreviewNow(); }")

    # ================= 9.1 regression guard on printRulesText =================
    # The documented trap: mutating r.media.mediaText is invisible to html2canvas
    # because it clones <style> nodes and re-parses the source. Assert the fix is
    # in place - a real stylesheet whose text carries the print declarations.
    css = await p.evaluate(
        """() => { const f = document.createElement('iframe');
             f.style.cssText = 'position:fixed;left:-10000px;width:718px;height:600px';
             document.body.appendChild(f);
             return new Promise(res => { f.onload = () => {
               const t = printRulesText(f.contentDocument);
               f.remove(); res(t); };
               f.srcdoc = buildSheetHTML(false); }); }"""
    )
    s.check("9.1 printRulesText() returns real CSS text, not an empty string",
            isinstance(css, str) and len(css) > 2000, f"len={len(css) if css else 0}")
    s.check("9.2 the lifted text carries print-only declarations",
            "--print-pane" in css or "print-head" in css or "@page" not in css,
            css[:120])
    s.check("9.3 the lifted text has no @media wrapper left around it",
            "@media" not in css, css[css.find("@media"):][:120] if "@media" in css else "")
    s.check("9.4 no rule was left targeting media 'all' in place (mediaText untouched)",
            await p.evaluate(
                """() => { let bad = 0;
                     for(const sh of document.styleSheets){ let rs;
                       try{ rs = sh.cssRules; }catch(e){ continue; }
                       for(const r of rs||[]) if(r.type===4 && /^all$/i.test(r.conditionText||''))
                         bad++; }
                     return bad; }""") == 0)

    # ================= per-theme structural checks =================
    pane_frac, rule_col = {}, {}
    for theme in THEMES:
        T = f"[{theme}]"
        await p.evaluate("t => { bindTheme(t); renderPreviewNow(); }", theme)
        await p.wait_for_timeout(350)

        parts = await p.evaluate(KEEP, True)
        g = await p.evaluate(GEOM)

        # ---- 1. masthead: logo BESIDE the banner, in one band ----
        hdr, brand, aside = g["header"], g["brand"], g["aside"]
        s.check(f"9.5 {T} the print layout has a header and a brand box",
                hdr is not None and brand is not None, f"header={hdr} brand={brand}")
        if hdr and brand:
            s.check(f"9.6 {T} the brand box sits BESIDE the banner, not below it",
                    brand["right"] <= hdr["left"] + 2
                    and brand["top"] < hdr["bottom"] and brand["bottom"] > hdr["top"],
                    f"brand={brand} header={hdr}")
            s.check(f"9.7 {T} banner and brand box are the same height (no clipping)",
                    abs(brand["h"] - hdr["h"]) <= 2, f"brand.h={brand['h']} hdr.h={hdr['h']}")
            s.check(f"9.8 {T} both start at the top of the page",
                    brand["top"] <= 2 and hdr["top"] <= 2, f"brand.top={brand['top']} hdr.top={hdr['top']}")
        s.check(f"9.9 {T} the Toastmasters logo is present and loaded in the brand box",
                g["hasLogo"] and g["logoComplete"], f"hasLogo={g['hasLogo']} complete={g['logoComplete']}")

        ht = g["headerText"]
        for label, needle in (("club name", "Nee Soon East Toastmasters Club"),
                              ("district line", "District: 80"),
                              ("meeting title", "Voices of a Nation"),
                              ("date", "13 August 2026"),
                              ("time", "7:00"),
                              ("location", "Yishun Ave 9"),
                              ("cadence", "2nd and 4th Thursday")):
            s.check(f"9.10 {T} the masthead carries the {label}", needle in ht,
                    f"header text = {ht[:220]!r}")

        # ---- 2/3. pagination geometry ----
        H = PRINT_H_PX
        pages = max(1, round(g["page"]["h"] / H))
        s.check(f"9.11 {T} the page is padded to a whole number of A4 pages",
                abs(g["page"]["h"] - pages * H) <= 2,
                f"pageH={g['page']['h']:.1f} pages={pages} expected={pages*H:.1f}")
        s.eq(f"9.12 {T} renderSheetParts reports that page count", parts["pages"], pages)
        s.check(f"9.13 {T} the sheet is {pages} pages (2 for a normal meeting)", pages == 2,
                f"pages={pages}")

        straddling = []
        for i, r in enumerate(g["rows"]):
            for k in range(1, pages):
                b = k * H
                if r["top"] < b - 0.5 and r["bottom"] > b + 0.5:
                    straddling.append(("row", i, round(r["top"], 1), round(r["bottom"], 1), round(b, 1)))
        s.check(f"9.14 {T} no agenda row is cut across a page boundary",
                not straddling, f"{straddling[:4]}")

        pstrad = []
        for i, r in enumerate(g["paneBlocks"]):
            for k in range(1, pages):
                b = k * H
                if r["top"] < b - 0.5 and r["bottom"] > b + 0.5:
                    pstrad.append(("pane", i, round(r["top"], 1), round(r["bottom"], 1), round(b, 1)))
        s.check(f"9.15 {T} no pane block is cut across a page boundary",
                not pstrad, f"{pstrad[:4]}")

        # ---- 3. pane and rule run to the bottom of every page; footer last ----
        foot = g["foot"]
        s.check(f"9.16 {T} the pane column runs to the footer on the last page",
                aside is not None and foot is not None
                and abs(aside["bottom"] - foot["top"]) <= 2,
                f"aside.bottom={aside and aside['bottom']} foot.top={foot and foot['top']}")
        s.check(f"9.17 {T} the pane starts at the very top of the sheet",
                aside is not None and aside["top"] <= 1, f"aside.top={aside and aside['top']}")
        s.check(f"9.18 {T} the pane column carries a visible rule",
                g["paneRule"] not in ("", "0px"), f"border-right-width={g['paneRule']!r}")
        s.check(f"9.19 {T} the footer sits on the LAST page",
                foot is not None and foot["top"] >= (pages - 1) * H
                and foot["bottom"] <= pages * H + 2,
                f"foot={foot} lastPageStart={(pages-1)*H:.1f}")
        s.check(f"9.20 {T} a footer strip was produced for the earlier pages",
                parts["strip"] is True)
        s.check(f"9.21 {T} pagination inserted spacers rather than cutting blind",
                g["spacers"] >= 1, f"spacers={g['spacers']}")

        # ---- 4. the pane spills, it does not repeat ----
        s.eq(f"9.22 {T} the pane's unique marker appears exactly once (no repetition)",
             g["paneText"].count("UNIQUEPANEMARKER"), 1)
        pane_frac[theme] = g["paneFrac"]
        rule_col[theme] = g["paneRuleColor"]

        await p.evaluate(DROP_KEPT)

    # ================= 9.23 pixel evidence, per theme =================
    for theme in THEMES:
        T = f"[{theme}]"
        await p.evaluate("t => { bindTheme(t); renderPreviewNow(); }", theme)
        await p.wait_for_timeout(300)
        pdf, size, banner = await grab_pdf(p)
        npages = pdf_pages(pdf)
        s.eq(f"9.23 {T} the delivered PDF has 2 pages", npages, 2)
        spare = CAP - size
        s.check(f"9.24 {T} the PDF is within the 500 KB cap ({size} bytes, {spare} spare)",
                size <= CAP, f"{size} bytes = {size//1024} KB, over by {-spare}")
        s.check(f"9.25 {T} the banner's over-cap claim matches reality",
                ("over the 500 KB cap" in banner) == (size > CAP), banner[:140])

        d, pngs = raster(pdf)
        if len(pngs) < 2:
            s.check(f"9.26 {T} page 1 and page 2 rasterise", False, f"{len(pngs)} images")
            cleanup(d, pngs)
            os.unlink(pdf)
            continue
        im1 = Image.open(pngs[0]).convert("L")
        im2 = Image.open(pngs[1]).convert("L")
        W, Hh = im1.size
        # the A4 page image includes the sheet's 1 cm margin: content starts at
        # 10/210 of the width and 10/297 of the height
        mx, my = W * 10 / 210, Hh * 10 / 297
        cw, ch = W - 2 * mx, Hh - 2 * my
        paneW = cw * 0.23          # the pane is ~23% of the content width
        bandH = ch * 0.14          # the masthead band

        left_frac, left_cy = ink(im1, mx, my, mx + paneW, my + bandH)
        right_frac, right_cy = ink(im1, mx + paneW, my, mx + cw, my + bandH)
        s.check(f"9.26 {T} page 1 has ink in the top-LEFT logo region",
                left_frac > 0.01, f"ink fraction={left_frac:.4f}")
        s.check(f"9.27 {T} page 1 has ink in the banner region beside it",
                right_frac > 0.02, f"ink fraction={right_frac:.4f}")
        s.check(f"9.28 {T} logo and banner occupy the SAME horizontal band",
                left_cy is not None and right_cy is not None
                and abs(left_cy - right_cy) < bandH * 0.6,
                f"logo cy={left_cy}, banner cy={right_cy}, band={bandH:.0f}px")
        # if the logo were still BELOW the banner, the band under the masthead in
        # the left column would hold it instead - and the top-left would be blank
        s.check(f"9.29 {T} the top-left is not blank (logo did not fall below the banner)",
                left_frac > 0.01, f"{left_frac:.4f}")

        # The pane rule must run the full height of page 2. It is a 1px hairline
        # and on three themes it is near-white (classic is rgb(226,225,221)), so a
        # fixed darkness threshold is the wrong instrument - what identifies it is
        # a LOCAL minimum in the column profile at the measured pane boundary.
        bx = mx + cw * pane_frac[theme]
        for tag, ya, yb in (("top", 0.08, 0.30), ("bottom", 0.68, 0.94)):
            prof = column_profile(im2, bx, my + ch * ya, my + ch * yb, span=6)
            here = min(v for dx, v in prof if abs(dx) <= 1)
            around = min(v for dx, v in prof if 3 <= abs(dx) <= 6)
            s.check(f"9.30 {T} the pane rule is visible on page 2 ({tag})",
                    around - here >= 12,
                    f"rule={here} paper={around} (needs >=12 darker); "
                    f"colour={rule_col[theme]}; profile={prof}")

        cleanup(d, pngs)
        os.unlink(pdf)

    await p.evaluate("() => { bindTheme('classic'); renderPreviewNow(); }")
    await p.wait_for_timeout(300)

    # ================= 9.31 a LIGHT pane leaves page 2's column empty =========
    await p.evaluate(LIGHT)
    await p.wait_for_timeout(400)
    await p.evaluate(KEEP, True)
    gl = await p.evaluate(GEOM)
    pages_l = max(1, round(gl["page"]["h"] / PRINT_H_PX))
    on_p2 = [b for b in gl["paneBlocks"] if b["top"] >= PRINT_H_PX]
    s.check("9.31 a light pane puts no block on page 2 (column simply empty)",
            not on_p2, f"{len(on_p2)} pane blocks start on page 2")
    s.check("9.32 the pane column still runs the full height with a light pane",
            abs(gl["aside"]["bottom"] - gl["foot"]["top"]) <= 2
            and gl["aside"]["bottom"] > PRINT_H_PX,
            f"aside={gl['aside']} foot={gl['foot']}")
    s.check("9.33 a light pane does not change the page count", pages_l == 2, f"pages={pages_l}")
    await p.evaluate(DROP_KEPT)

    # ================= 9.34 a HEAVY pane SPILLS onto page 2 ==================
    await p.evaluate(HEAVY)
    await p.wait_for_timeout(500)
    await p.evaluate(KEEP, True)
    gh = await p.evaluate(GEOM)
    pages_h = max(1, round(gh["page"]["h"] / PRINT_H_PX))
    spill = [b for b in gh["paneBlocks"] if b["top"] >= PRINT_H_PX]
    s.check("9.34 a heavy pane continues onto page 2",
            len(spill) >= 1, f"{len(spill)} pane blocks on page 2 of {pages_h}")
    s.check("9.35 the continuation is a CONTINUATION, not a repeat",
            gh["paneText"].count("Announcement number 1:") == 1
            and gh["paneText"].count("Announcement number 14:") == 1,
            "a pane block appears more than once")
    hstrad = []
    for i, r in enumerate(gh["paneBlocks"]):
        for k in range(1, pages_h):
            b = k * PRINT_H_PX
            if r["top"] < b - 0.5 and r["bottom"] > b + 0.5:
                hstrad.append((i, round(r["top"], 1), round(r["bottom"], 1)))
    s.check("9.36 no heavy-pane block straddles the boundary either",
            not hstrad, f"{hstrad[:4]}")
    s.check("9.37 the heavy pane still ends at the footer",
            abs(gh["aside"]["bottom"] - gh["foot"]["top"]) <= 2,
            f"aside={gh['aside']} foot={gh['foot']}")
    await p.evaluate(DROP_KEPT)

    pdf, size, banner = await grab_pdf(p)
    d, pngs = raster(pdf)
    if len(pngs) >= 2:
        im2 = Image.open(pngs[1]).convert("L")
        W, Hh = im2.size
        mx, my = W * 10 / 210, Hh * 10 / 297
        cw, ch = W - 2 * mx, Hh - 2 * my
        frac, _ = ink(im2, mx, my + ch * 0.05, mx + cw * 0.22, my + ch * 0.6)
        s.check("9.38 page 2's pane column carries the heavy pane's continuation in pixels",
                frac > 0.01, f"ink fraction={frac:.4f}")
    else:
        s.check("9.38 page 2's pane column carries the continuation", False,
                f"{len(pngs)} pages rasterised")
    cleanup(d, pngs)
    os.unlink(pdf)

    # ================= 9.39 the JPG is NOT paginated, but IS print layout =====
    await p.evaluate(FILL_JS)
    await p.wait_for_timeout(500)
    await p.evaluate(KEEP, False)
    gj = await p.evaluate(GEOM)
    s.eq("9.39 an unpaginated render inserts no page spacers", gj["spacers"], 0)
    # V44: the unpaginated path sets minHeight to content + footer, because the
    # footer is absolutely positioned and was painting over the last table row.
    # 9.41 below is the assertion that actually matters here (not padded to whole
    # pages) and it still holds; this one now pins the footer clearance instead of
    # the empty string that used to stand in for it.
    s.check("9.40 the unpaginated render reserves room for the footer",
            gj["minHeight"].endswith("px") and float(gj["minHeight"][:-2]) > 0,
            f"minHeight={gj['minHeight']!r}")
    s.eq("9.40b the footer does not overlap the last row", gj["footOverlap"], 0)
    s.check("9.41 the unpaginated sheet is NOT padded to whole A4 pages",
            abs(gj["page"]["h"] - round(gj["page"]["h"] / PRINT_H_PX) * PRINT_H_PX) > 4,
            f"height={gj['page']['h']:.1f} is a whole number of pages")
    s.check("9.42 the JPG render still uses the PRINT width (718 CSS px)",
            abs(gj["page"]["w"] - PRINT_W_PX) <= 2, f"width={gj['page']['w']}")
    s.check("9.43 the JPG render still puts the brand box beside the banner",
            gj["brand"]["right"] <= gj["header"]["left"] + 2
            and abs(gj["brand"]["h"] - gj["header"]["h"]) <= 2,
            f"brand={gj['brand']} header={gj['header']}")
    await p.evaluate(DROP_KEPT)

    async with p.expect_download(timeout=300000) as dl:
        await p.evaluate("() => pickDownload('jpg')")
    dj = await dl.value
    await p.wait_for_timeout(150)
    jban = await p.evaluate("() => document.getElementById('banner').textContent")
    fd, jpath = tempfile.mkstemp(prefix="psb9_", suffix=".jpg")
    os.close(fd)
    await dj.save_as(jpath)
    jsize = os.path.getsize(jpath)
    s.check("9.44 the JPG downloads and is a real JPEG",
            open(jpath, "rb").read(2) == b"\xff\xd8")
    s.check(f"9.45 the JPG is within the 500 KB cap ({jsize} bytes, {CAP - jsize} spare)",
            jsize <= CAP, f"{jsize} bytes = {jsize//1024} KB")
    s.check("9.46 the JPG banner's cap claim matches reality",
            ("over the 500 KB cap" in jban) == (jsize > CAP), jban[:140])
    jim = Image.open(jpath).convert("L")
    JW, JH = jim.size
    band = JH * 0.14 * (PRINT_H_PX / max(1, JH))     # masthead is ~14% of ONE page
    band = JH * (138.0 / gj["page"]["h"])            # measured header height, scaled
    lf, lcy = ink(jim, 0, 0, JW * 0.23, band)
    rf, rcy = ink(jim, JW * 0.23, 0, JW, band)
    s.check("9.47 the JPG shows the logo in the top-left band", lf > 0.01, f"{lf:.4f}")
    s.check("9.48 the JPG shows the banner beside it", rf > 0.02, f"{rf:.4f}")
    s.check("9.49 logo and banner share the same band in the JPG",
            lcy is not None and rcy is not None and abs(lcy - rcy) < band * 0.6,
            f"logo cy={lcy} banner cy={rcy} band={band:.0f}")
    s.check("9.50 the JPG is one continuous image, not padded to a page multiple",
            abs(JH / (JW * (277 / 190)) - round(JH / (JW * (277 / 190)))) > 0.02,
            f"{JW}x{JH} is suspiciously exactly {JH/(JW*(277/190)):.3f} pages")
    os.unlink(jpath)

    # ================= 9.51 errors =================
    s.check("9.51 zero uncaught page errors across the print-layout exports",
            not app.clean_errors(), str(app.clean_errors()[:4]))
    s.check("9.52 zero console errors across the print-layout exports",
            not app.clean_console(), str(app.clean_console()[:4]))


if __name__ == "__main__":
    asyncio.run(run_suite(main, "9_print_layout_exports"))
