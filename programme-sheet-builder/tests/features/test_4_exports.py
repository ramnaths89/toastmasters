"""V30 feature 4 - HTML / PDF / JPG / PNG downloads, all budgeted at 500 KB."""

import asyncio
import os
import re
import glob
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import FILL_JS, open_app, run_suite  # noqa: E402

CAP = 500 * 1024          # 512000 bytes
KINDS = ["html", "pdf", "jpg"]   # PNG removed in V31


BANNER_JS = """() => {
  const b = document.getElementById('banner');
  if(!b) return {txt:'', warn:false, shown:false};
  /* showBanner() colours the box inline rather than by class: a warning is the
     red/pink pair, anything else is the green one. */
  const bg = b.style.background || '';
  return {txt: b.textContent, warn: /fdeeec/i.test(bg) || /253, 238, 236/.test(bg),
          shown: b.style.display !== 'none'};
}"""


async def banner_text(p):
    return await p.evaluate(BANNER_JS)


async def grab(p, kind, timeout=180000):
    """Fire pickDownload(kind), capture the file + the banner it raised."""
    async with p.expect_download(timeout=timeout) as dl:
        await p.evaluate("k => pickDownload(k)", kind)
    d = await dl.value
    # showBanner() self-hides after 5 s, so read it before the (slower) save_as.
    await p.wait_for_timeout(120)
    banner = await banner_text(p)
    fd, path = tempfile.mkstemp(prefix="psb_", suffix="_" + kind)
    os.close(fd)
    await d.save_as(path)
    with open(path, "rb") as f:
        data = f.read()
    return d.suggested_filename, data, path, banner


async def main(ctx, s):
    app = await open_app(ctx)
    p = app.page
    await p.evaluate(FILL_JS)
    await p.wait_for_timeout(600)

    # ---------- 4.1 the menu offers all four ----------
    for menu_id, where in (("dlMenu", "toolbar"), ("dlMenuM", "phone bar")):
        items = await p.evaluate(
            "id => [...document.querySelectorAll('#'+id+' [role=menuitem] b')].map(b=>b.textContent)",
            menu_id,
        )
        s.check(f"4.1 {where} download menu offers HTML, PDF, JPG only (no PNG)",
                [i.split()[0].lower() for i in items] == KINDS, f"{items}")

    # ---------- 4.2 two download buttons, mutually exclusive menus ----------
    s.eq("4.2 #dlBtn exists", await p.locator("#dlBtn").count(), 1)
    s.eq("4.3 #dlBtnM exists", await p.locator("#dlBtnM").count(), 1)

    async def click_btn(bid):
        await p.evaluate(
            "id => document.getElementById(id).dispatchEvent("
            "new MouseEvent('click',{bubbles:true,cancelable:true}))", bid)
        await p.wait_for_timeout(150)

    async def open_menus():
        return await p.evaluate(
            "() => [...document.querySelectorAll('.dl-menu')].map(m=>[m.id, m.classList.contains('open')])")

    await click_btn("dlBtn")
    s.eq("4.4 pressing #dlBtn opens only the toolbar menu",
         await open_menus(), [["dlMenu", True], ["dlMenuM", False]])
    await click_btn("dlBtnM")
    s.eq("4.5 pressing #dlBtnM closes the toolbar menu and opens the phone one",
         await open_menus(), [["dlMenu", False], ["dlMenuM", True]])
    await click_btn("dlBtn")
    s.eq("4.6 and back again - never both open at once",
         await open_menus(), [["dlMenu", True], ["dlMenuM", False]])
    await click_btn("dlBtn")
    s.eq("4.7 pressing the same button again closes its menu",
         await open_menus(), [["dlMenu", False], ["dlMenuM", False]])

    s.eq("4.8 aria-expanded is cleared on both buttons when closed",
         await p.evaluate("() => ['dlBtn','dlBtnM'].map(i=>document.getElementById(i)"
                          ".getAttribute('aria-expanded'))"),
         ["false", "false"])

    # ---------- 4.9 both buttons drive the same exports ----------
    for bid, mid in (("dlBtn", "dlMenu"), ("dlBtnM", "dlMenuM")):
        await click_btn(bid)
        try:
            async with p.expect_download(timeout=30000) as dl:
                await p.evaluate(
                    "id => document.querySelector('#'+id+' [role=menuitem]')"
                    ".dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true}))", mid)
            d = await dl.value
            name = d.suggested_filename
            await d.cancel()
        except Exception as e:
            name = f"<none {type(e).__name__}>"
        s.check(f"4.9 the {mid} HTML item downloads a .html file",
                name.endswith(".html"), f"{name}")
        s.check(f"4.10 choosing an item from {mid} closes the menu",
                not any(o[1] for o in await open_menus()))

    # ---------- 4.11 HTML export ----------
    name, data, path, b = await grab(p, "html")
    text = data.decode("utf-8", "replace")
    s.check("4.11 HTML export downloads", bool(data), "")
    s.check("4.12 HTML export is a standalone document",
            text.lstrip()[:15].lower().startswith("<!doctype html") and "</html>" in text.lower(),
            text[:80])
    s.check("4.13 HTML export carries its own <style> (no external CSS needed)",
            "<style" in text.lower(), "")
    s.check("4.14 HTML export contains the meeting title",
            "Voices of a Nation" in text, "")
    s.check("4.15 HTML export contains the sheet's agenda rows",
            "Prepared Speech 1" in text and "Table Topics" in text, "")
    s.check("4.16 HTML export contains the roster people",
            "Member Name 1" in text and "Speaker Name 1" in text, "")
    # (the bundled stylesheet still names the builder classes; what matters is
    #  that no such ELEMENT is emitted)
    stray = re.findall(r'<(?:input|select|textarea)\b', text)
    btns = re.findall(r'<button[^>]*class="([^"]*)"', text)
    s.check("4.17 HTML export is the CLEAN sheet (no builder edit controls)",
            not stray and 'class="cbx"' not in text and 'class="row-edit"' not in text
            and btns == ['print-btn'],
            f"inputs={stray[:5]} buttons={btns}")
    # it must render on its own
    side = await ctx.new_page()
    perr = []
    side.on("pageerror", lambda e: perr.append(str(e)))
    await side.goto("file://" + path)
    await side.wait_for_timeout(500)
    body_len = len((await side.locator("body").inner_text()) or "")
    s.check("4.18 the exported HTML opens on its own and renders text",
            body_len > 800 and not perr, f"len={body_len} errs={perr[:2]}")
    await side.close()
    os.unlink(path)

    # ---------- 4.19 PDF ----------
    name, data, path, b = await grab(p, "pdf")
    s.check("4.19 PDF export downloads", bool(data), "")
    s.check("4.20 PDF starts with the %PDF header", data[:5] == b"%PDF-", str(data[:8]))
    s.check("4.21 PDF ends with %%EOF", data.rstrip()[-5:] == b"%%EOF", str(data[-12:]))
    info = subprocess.run(["pdfinfo", path], capture_output=True, text=True)
    s.check("4.22 pdfinfo parses the file (it is a real PDF)", info.returncode == 0,
            info.stderr.strip()[:200])
    pages = 0
    m = re.search(r"^Pages:\s+(\d+)", info.stdout, re.M)
    if m:
        pages = int(m.group(1))
    s.check("4.23 the PDF has 1-3 A4 pages for a normal meeting", 1 <= pages <= 3,
            f"Pages={pages}\n{info.stdout[:300]}")
    psize = re.search(r"^Page size:\s+([\d.]+) x ([\d.]+)", info.stdout, re.M)
    s.check("4.24 the PDF page box is A4 (595 x 842 pt)",
            bool(psize) and abs(float(psize.group(1)) - 595.28) < 2
            and abs(float(psize.group(2)) - 841.89) < 2,
            psize.group(0) if psize else info.stdout[:200])
    s.check(f"4.25 PDF is <= 500 KB ({len(data)} bytes)", len(data) <= CAP,
            f"{len(data)} bytes = {len(data)//1024} KB")
    s.eq("4.25b the PDF is 2 pages for the standard filled meeting", pages, 2)
    s.check(f"4.25c PDF headroom under the cap is at least 1% "
            f"({CAP - len(data)} bytes spare)",
            len(data) <= CAP * 0.99,
            f"only {CAP - len(data)} bytes ({100 - len(data) * 100 // CAP}%) spare - the "
            f"quality ladder has almost nothing left to give")
    s.check("4.26 the PDF banner reports the page count and size",
            "PDF" in b["txt"] and "KB" in b["txt"], b["txt"][:160])
    s.check("4.27 the PDF banner is not a warning when inside the cap",
            (len(data) <= CAP) == ("over the 500 KB cap" not in b["txt"]), b["txt"][:160])

    # ---------- 4.27b-e the print-layout PDF (V32) ----------
    # The club name vanishing from the masthead is the regression that started
    # this, so it is asserted from the DELIVERED FILE, not from the DOM.
    # pdfFromJpegs() embeds one JPEG per page, so the PDF carries no text layer
    # at all - pdftotext returns "". That is by design, and asserted here so a
    # future switch to real text is noticed. The masthead is therefore read back
    # by OCR of the rasterised page 1.
    pdftext = subprocess.run(["pdftotext", "-f", "1", "-l", "1", path, "-"],
                             capture_output=True, text=True).stdout
    s.check("4.27b the PDF is image-only by design (no extractable text layer)",
            not pdftext.strip(), f"unexpected text layer: {pdftext[:120]!r}")

    # Read the MASTHEAD BAND back by OCR. Cropping to the band first matters:
    # OCR of the whole page walks the left pane column before the header, so a
    # position test on full-page text would prove nothing about the masthead.
    from PIL import Image  # noqa: E402
    ocr_dir = tempfile.mkdtemp(prefix="psb_ocr_")
    subprocess.run(["pdftoppm", "-png", "-r", "200", "-f", "1", "-l", "1", path,
                    os.path.join(ocr_dir, "p1")], capture_output=True)
    ocr_pngs = sorted(glob.glob(os.path.join(ocr_dir, "p1*.png")))
    band_text = ""
    if ocr_pngs:
        im = Image.open(ocr_pngs[0])
        W, H = im.size
        mx, my = W * 10 / 210, H * 10 / 297
        cw, ch = W - 2 * mx, H - 2 * my
        band_png = os.path.join(ocr_dir, "band.png")
        im.crop((int(mx), int(my), int(mx + cw), int(my + ch * 0.16))).save(band_png)
        band_text = " ".join(subprocess.run(["tesseract", band_png, "stdout"],
                                            capture_output=True, text=True).stdout.split())
    s.check("4.27c the CLUB NAME is in the masthead band of the exported PDF (OCR)",
            "Nee Soon East Toastmasters Club" in band_text,
            f"masthead band OCR = {band_text[:260]!r}")
    for label, needle in (("district line", "District: 80"),
                          ("meeting title", "Voices of a Nation"),
                          ("date", "13 August 2026"),
                          ("time", "7:00 PM"),
                          ("location", "Yishun Ave 9"),
                          ("cadence", "2nd and 4th Thursday")):
        s.check(f"4.27c2 the masthead band also carries the {label} (OCR)",
                needle in band_text, f"masthead band OCR = {band_text[:260]!r}")
    s.check("4.27c3 the Toastmasters brand box is in the SAME band as the masthead",
            "TOASTMASTERS INTERNATIONAL" in band_text.upper(),
            f"masthead band OCR = {band_text[:260]!r}")
    s.check("4.27c4 the club name is the FIRST thing in the masthead band",
            band_text.startswith("Nee Soon East Toastmasters Club"),
            f"band starts {band_text[:80]!r}")
    for f_ in ocr_pngs:
        os.unlink(f_)
    for leftover in glob.glob(os.path.join(ocr_dir, "*")):
        os.unlink(leftover)
    os.rmdir(ocr_dir)

    # The pane column across the seam. V30/V31 PAINTED a copy of the pane onto
    # every later page; V32 lets one column FLOW. Both outcomes below are
    # correct - what must hold in each is that the rule is drawn and that no
    # pane line is sliced in half at the boundary.
    from PIL import Image  # noqa: E402

    async def pane_frac(page):
        return await page.evaluate(
            """async () => {
                 const orig = Element.prototype.remove; let kept = null;
                 Element.prototype.remove = function(){
                   if(this.tagName === 'IFRAME'){ kept = this; return; }
                   return orig.call(this); };
                 try { await renderSheetParts({paginate:true}); }
                 finally { Element.prototype.remove = orig; }
                 const d = kept.contentDocument;
                 const pb = d.querySelector('.page').getBoundingClientRect();
                 const bb = d.querySelector('.pane-body').getBoundingClientRect();
                 const H = 277 * 96 / 25.4;
                 const blocks = [...d.querySelectorAll(
                   'aside h3, aside .exco-item, aside .announce-line, aside .path-legend div')]
                   .filter(e => !e.classList.contains('pg-spacer'))
                   .map(e => { const b = e.getBoundingClientRect();
                               return [b.top - pb.top, b.bottom - pb.top]; });
                 const pages = Math.max(1, Math.round(pb.height / H));
                 const cut = [];
                 for(let k = 1; k < pages; k++){ const y = k * H;
                   blocks.forEach(([a,b]) => { if(a < y - 0.5 && b > y + 0.5) cut.push([a,b,y]); }); }
                 const onP2 = blocks.filter(([a]) => a >= H).length;
                 kept.parentNode.removeChild(kept);
                 return {frac: (bb.right - pb.left) / pb.width, cut, onP2, pages}; }"""
        )

    def rule_contrast(png, frac, y0=0.35, y1=0.75):
        im = Image.open(png).convert("L")
        W, H = im.size
        mx, my = W * 10 / 210, H * 10 / 297
        cw, ch = W - 2 * mx, H - 2 * my
        xc = int(round(mx + cw * frac))
        prof = []
        for dx in range(-6, 7):
            col = [im.getpixel((xc + dx, int(y)))
                   for y in range(int(my + ch * y0), int(my + ch * y1), 2)]
            prof.append((dx, min(col)))
        here = min(v for dx, v in prof if abs(dx) <= 1)
        around = min(v for dx, v in prof if 3 <= abs(dx) <= 6)
        return around - here, prof

    def page2_pane_ink(png, frac):
        im = Image.open(png).convert("L")
        W, H = im.size
        mx, my = W * 10 / 210, H * 10 / 297
        cw, ch = W - 2 * mx, H - 2 * my
        crop = im.crop((int(mx), int(my + ch * 0.05),
                        int(mx + cw * frac * 0.92), int(my + ch * 0.60)))
        px = list(crop.getdata())
        return sum(1 for v in px if v < 200) / max(1, len(px))

    # (a) SHORT pane: page 2's column is empty but still ruled.
    pf = await pane_frac(p)
    tmpdir, pngs = tempfile.mkdtemp(prefix="psb_pg_"), None
    subprocess.run(["pdftoppm", "-png", "-r", "150", path, os.path.join(tmpdir, "pg")],
                   capture_output=True)
    pngs = sorted(glob.glob(os.path.join(tmpdir, "pg*.png")))
    if len(pngs) >= 2:
        s.eq("4.27d a short pane leaves no pane block on page 2", pf["onP2"], 0)
        contrast, prof = rule_contrast(pngs[1], pf["frac"])
        s.check("4.27e the pane rule is still drawn down page 2 when the column is empty",
                contrast >= 12, f"contrast={contrast} profile={prof}")
        s.check("4.27f the empty page-2 pane column really is empty",
                page2_pane_ink(pngs[1], pf["frac"]) < 0.005,
                f"ink={page2_pane_ink(pngs[1], pf['frac']):.4f}")
        s.check("4.27g no pane line is cut in half at the seam (short pane)",
                not pf["cut"], f"{pf['cut'][:3]}")
    else:
        s.check("4.27d-g short-pane seam checks", False, f"{len(pngs)} pages rasterised")
    for f_ in pngs or []:
        os.unlink(f_)
    os.rmdir(tmpdir)
    os.unlink(path)

    # (b) LONG pane: page 2's column carries the CONTINUATION, still ruled,
    #     still nothing sliced at the seam.
    await p.evaluate(
        r"""() => { state.announcementsText = Array.from({length:14},
             (_,i)=>'Announcement number '+(i+1)+': a reasonably wordy notice for the club')
             .join('\n');
           state.districtText = ['Division Director|<Division Director Name>|<Their Club>',
             'Area Director|Pat Chen|<Their Club>',
             'Programme Quality Director|Meera Raghunathan|Yishun TMC',
             'Club Growth Director|Samuel Tan Wei Ming|Sembawang TMC'].join('\n');
           renderFormPane(); renderPreviewNow(); }""")
    await p.wait_for_timeout(600)
    pf2 = await pane_frac(p)
    _, ldata, lpath, lb = await grab(p, "pdf")
    tmpdir = tempfile.mkdtemp(prefix="psb_pg2_")
    subprocess.run(["pdftoppm", "-png", "-r", "150", lpath, os.path.join(tmpdir, "pg")],
                   capture_output=True)
    pngs = sorted(glob.glob(os.path.join(tmpdir, "pg*.png")))
    if len(pngs) >= 2:
        s.check("4.27h a long pane continues onto page 2", pf2["onP2"] >= 1,
                f"{pf2['onP2']} pane blocks on page 2 of {pf2['pages']}")
        s.check("4.27i page 2's pane column shows the continuation in pixels",
                page2_pane_ink(pngs[1], pf2["frac"]) > 0.01,
                f"ink={page2_pane_ink(pngs[1], pf2['frac']):.4f}")
        contrast, prof = rule_contrast(pngs[1], pf2["frac"], 0.55, 0.92)
        s.check("4.27j the pane rule is drawn down page 2 with a long pane too",
                contrast >= 12, f"contrast={contrast} profile={prof}")
        s.check("4.27k no pane line is cut in half at the seam (long pane)",
                not pf2["cut"], f"{pf2['cut'][:3]}")
    else:
        s.check("4.27h-k long-pane seam checks", False, f"{len(pngs)} pages rasterised")
    for f_ in pngs:
        os.unlink(f_)
    os.rmdir(tmpdir)
    os.unlink(lpath)
    # restore the normal meeting (raw string: a plain one turns \n into a real
    # newline inside the JS string literal and the eval is a SyntaxError)
    await p.evaluate(
        r"""() => {
              state.announcementsText =
                'Club anniversary dinner, 20 Sept\nArea contest briefing after the meeting';
              state.districtText = ['Division Director|<Division Director Name>|<Their Club>',
                'Area Director|Pat Chen|<Their Club>'].join('\n');
              renderFormPane(); renderPreviewNow();
            }""")
    await p.wait_for_timeout(500)

    # ---------- 4.28 JPG ----------
    name, data, path, b = await grab(p, "jpg")
    s.check("4.28 JPG export downloads", bool(data), "")
    s.check("4.29 JPG has the JFIF/SOI magic", data[:2] == b"\xff\xd8", str(data[:4]))
    s.check(f"4.30 JPG is <= 500 KB ({len(data)} bytes)", len(data) <= CAP,
            f"{len(data)} bytes = {len(data)//1024} KB")
    s.check("4.31 the JPG banner reports the pixel size and KB",
            "JPG" in b["txt"] and "KB" in b["txt"], b["txt"][:160])
    s.check("4.32 the JPG banner only claims 'over the cap' when it really is",
            ("over the 500 KB cap" in b["txt"]) == (len(data) > CAP), b["txt"][:160])
    wmatch = re.search(r"(\d+)×(\d+)", b["txt"])
    s.check("4.33 the JPG width is capped at MAX_EXPORT_WIDTH (1500)",
            bool(wmatch) and int(wmatch.group(1)) <= 1500,
            b["txt"][:160])
    # ---------- 4.33b the JPG is ONE tall print-layout image, pane not repeated ----
    from PIL import Image as _Im
    _j = _Im.open(path)
    JW, JH = _j.size
    page_ratio = 277 / 190
    s.check("4.33b the JPG is a single tall image, taller than one A4 page",
            JH > JW * page_ratio * 1.2, f"{JW}x{JH}, one page would be {JW*page_ratio:.0f} tall")
    s.check("4.33c the JPG is NOT padded to a whole number of pages",
            abs(JH / (JW * page_ratio) - round(JH / (JW * page_ratio))) > 0.02,
            f"{JH/(JW*page_ratio):.3f} pages - suspiciously exact")
    unpag = await p.evaluate(
        r"""async () => {
              const orig = Element.prototype.remove; let kept = null;
              Element.prototype.remove = function(){
                if(this.tagName === 'IFRAME'){ kept = this; return; }
                return orig.call(this); };
              try { await renderSheetParts(); } finally { Element.prototype.remove = orig; }
              const d = kept.contentDocument;
              const aside = d.querySelector('aside');
              const txt = aside.textContent.replace(/\s+/g, ' ');
              const r = {spacers: d.querySelectorAll('.pg-spacer').length,
                         minHeight: d.querySelector('.page').style.minHeight || '',
                         footOverlap: (()=>{
                           const rows=[...d.querySelectorAll('tbody tr')];
                           const last=rows[rows.length-1], f=d.querySelector('footer');
                           if(!last||!f) return 0;
                           const o = last.getBoundingClientRect().bottom - f.getBoundingClientRect().top;
                           return Math.max(0, Math.round(o));
                         })(),
                         brands: d.querySelectorAll('.pane-brand').length,
                         panes: d.querySelectorAll('aside').length,
                         excoOnce: (txt.match(/EXECUTIVE COMMITTEE/gi) || []).length,
                         anniv: (txt.match(/Club anniversary dinner/g) || []).length};
              kept.parentNode.removeChild(kept);
              return r; }"""
    )
    s.eq("4.33d the JPG render is unpaginated (no spacers)", unpag["spacers"], 0)
    # V44: the JPG path now DOES set a minHeight - content height plus the footer
    # band, because the footer is out of flow and was painting over the last row.
    # The property this check has always been protecting is the one beside it in
    # 4.33c: the JPG must not be padded to whole A4 pages the way the PDF is. Pin
    # that, and pin the footer clearance that replaced the old empty string.
    _mh = float(unpag["minHeight"][:-2]) if unpag["minHeight"].endswith("px") else 0.0
    s.check("4.33e the JPG minHeight is content + footer, not a whole page count",
            _mh > 0 and abs(_mh / (JW * page_ratio / (JW / 718.0)) - round(
                _mh / (JW * page_ratio / (JW / 718.0)))) > 0.02,
            f"minHeight={unpag['minHeight']}")
    s.eq("4.33e2 the footer clears the last row in the JPG render",
         unpag["footOverlap"], 0)
    s.eq("4.33f there is exactly ONE pane in the JPG render", unpag["panes"], 1)
    s.eq("4.33g the pane's brand box appears once, not per page", unpag["brands"], 1)
    s.eq("4.33h the pane's officer block is not repeated", unpag["excoOnce"], 1)
    s.eq("4.33i the pane's announcements are not repeated", unpag["anniv"], 1)

    os.unlink(path)

    # ---------- 4.34 PNG is gone (V31) ----------
    s.check("4.34 no PNG item in either download menu",
            await p.evaluate(
                "() => ![...document.querySelectorAll('.dl-menu [role=menuitem]')]"
                ".some(b => /png/i.test(b.textContent))"))
    s.check("4.35 encodePngUnder() no longer exists",
            await p.evaluate("() => typeof encodePngUnder") == "undefined")
    s.check("4.36 downloadImage() takes no argument",
            await p.evaluate("() => downloadImage.length") == 0,
            f"arity={await p.evaluate('() => downloadImage.length')}")
    # A stale pickDownload('png') must not silently produce a PNG.
    try:
        async with p.expect_download(timeout=25000) as dl:
            await p.evaluate("() => pickDownload('png')")
        d = await dl.value
        png_name = d.suggested_filename
        await d.cancel()
    except Exception:
        png_name = None
    s.check("4.37 pickDownload('png') never yields a .png file",
            png_name is None or not png_name.endswith(".png"),
            f"got {png_name!r}")
    # No user-facing copy may still promise PNG. Deepest nodes only, so one
    # mention is not reported once per ancestor. NOTE: this JS must be a RAW
    # string - a plain one turns \b into a backspace and the regex stops matching.
    stale = await p.evaluate(
        r"""() => { const hits = [];
             document.querySelectorAll(
               '.dl-menu button, #helpOverlay dd, #helpOverlay dt, #helpOverlay p, .hint')
               .forEach(e => { if(/\bPNG\b/i.test(e.textContent)) hits.push(
                 (e.tagName + ' ' + e.className) + ': ' + e.textContent.trim().slice(0,150)); });
             return hits; }"""
    )
    s.check("4.38 no user-facing text still offers PNG", not stale, f"{stale[:2]}")

    # The Balance button lost its ⚖ icon in V31; the instructions must not still
    # describe it by an icon that is no longer on screen.
    stale_bal = await p.evaluate(
        r"""() => { const hits = [];
             document.querySelectorAll('#helpOverlay dt').forEach(e => {
               if(/balance/i.test(e.textContent) && /[⚖]/.test(e.textContent))
                 hits.push(e.textContent.trim().slice(0,60)); });
             return hits; }"""
    )
    s.check("4.38b the instructions do not still label Balance with the retired ⚖ icon",
            not stale_bal, f"{stale_bal}")

    # ---------- 4.39 a LONG meeting still respects the budget ----------
    await p.evaluate(
        """() => {
             state.announcementsText = Array.from({length:12},
               (_,i)=>'Announcement line number ' + (i+1) + ' with a fair amount of text on it').join('\\n');
             for(let i=0;i<3;i++) addSpeechSlot();
             state.segments.filter(s=>s.isSpeech).forEach((s,i)=>{
               s.speakerName = 'Speaker Name ' + (i+1);
               s.speechTitle = 'Another Reasonably Long Speech Title For Padding';
               s.pathway='DL'; s.pLevel='1'; applyProjectChoice(s,'Ice Breaker');
             });
             renderFormPane(); renderPreviewNow();
           }"""
    )
    await p.wait_for_timeout(700)
    _, jdata, jpath, _b = await grab(p, "jpg")
    s.check(f"4.39 JPG stays <= 500 KB on a longer meeting ({len(jdata)} bytes)",
            len(jdata) <= CAP, f"{len(jdata)//1024} KB")
    os.unlink(jpath)
    _, pdata, ppath, _b = await grab(p, "pdf")
    s.check(f"4.40 PDF stays <= 500 KB on a longer meeting ({len(pdata)} bytes)",
            len(pdata) <= CAP, f"{len(pdata)//1024} KB")
    s.check(f"4.40b the longer PDF keeps at least 1% headroom "
            f"({CAP - len(pdata)} bytes spare)",
            len(pdata) <= CAP * 0.99,
            f"only {CAP - len(pdata)} bytes spare - the quality ladder stopped at its "
            f"first fit with almost nothing in reserve")
    info2 = subprocess.run(["pdfinfo", ppath], capture_output=True, text=True)
    s.check("4.41 the longer PDF is still valid and gained pages",
            info2.returncode == 0, info2.stderr[:150])
    os.unlink(ppath)

    # ---------- 4.41b the MAX_CANVAS_PX guard ----------
    s.check("4.41b MAX_CANVAS_PX guard constant exists",
            await p.evaluate("() => typeof MAX_CANVAS_PX") == "number")
    s.eq("4.41c the guard is 30000px",
         await p.evaluate("() => MAX_CANVAS_PX"), 30000)
    # A sheet long enough to force the scale down (h*3 > 30000 at ~10 pages).
    # The old failure mode was a BLANK canvas reported as success, so the test is
    # that every page carries ink - or that it fails loudly with a readable error.
    await p.evaluate(
        r"""() => { state.announcementsText = Array.from({length:150},
              (_,i)=>'Filler announcement line number '+(i+1)+' padding the pane out')
              .join('\n');
            renderFormPane(); renderPreviewNow(); }""")
    await p.wait_for_timeout(900)
    huge_err = None
    try:
        async with p.expect_download(timeout=420000) as dl:
            await p.evaluate("() => pickDownload('pdf')")
        dh = await dl.value
        await p.wait_for_timeout(200)
        hban = await p.evaluate("() => document.getElementById('banner').textContent")
        fdh, hpath = tempfile.mkstemp(prefix="psb_huge_", suffix=".pdf")
        os.close(fdh)
        await dh.save_as(hpath)
        hpages = 0
        hinfo = subprocess.run(["pdfinfo", hpath], capture_output=True, text=True).stdout
        mh = re.search(r"^Pages:\s+(\d+)", hinfo, re.M)
        if mh:
            hpages = int(mh.group(1))
        s.check(f"4.41d a very long sheet still produces a valid PDF ({hpages} pages)",
                hpages >= 5, f"pages={hpages} banner={hban[:120]!r}")
        # no page may be blank - that was the failure the guard exists to stop
        hd = tempfile.mkdtemp(prefix="psb_huge_pg_")
        subprocess.run(["pdftoppm", "-png", "-r", "60", hpath, os.path.join(hd, "pg")],
                       capture_output=True)
        hpngs = sorted(glob.glob(os.path.join(hd, "pg*.png")))
        blank = []
        for i, q in enumerate(hpngs):
            imq = Image.open(q).convert("L")
            pxq = list(imq.getdata())
            frac = sum(1 for v in pxq if v < 200) / max(1, len(pxq))
            if frac < 0.002:
                blank.append((i + 1, round(frac, 5)))
        s.check("4.41e no page of the long PDF is blank", not blank,
                f"blank pages: {blank[:6]} of {len(hpngs)}")
        for q in hpngs:
            os.unlink(q)
        os.rmdir(hd)
        os.unlink(hpath)
    except Exception as e:
        huge_err = e
        eb = await p.evaluate("() => document.getElementById('banner').textContent")
        s.check("4.41d a very long sheet fails LOUDLY with a readable message, not silently",
                "too long" in eb or "Could not build" in eb,
                f"no download and banner={eb[:160]!r} ({type(e).__name__})")
        s.check("4.41e (n/a) the long PDF was refused rather than shipped blank", True)

    # ---------- 4.42 no errors ----------
    s.check("4.42 zero uncaught page errors during feature 4", not app.clean_errors(),
            str(app.clean_errors()[:3]))
    s.check("4.43 zero console errors during feature 4", not app.clean_console(),
            str(app.clean_console()[:3]))


if __name__ == "__main__":
    asyncio.run(run_suite(main, "4_exports"))
