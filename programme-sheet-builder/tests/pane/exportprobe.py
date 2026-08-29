"""Attack harness for the V32 export path. Read-only: nothing is fixed here.

Drives the REAL renderSheetParts()/downloadPdfImage() in the page, but
  - stubs saveBlob() so the PDF comes back as bytes instead of a download
  - no-ops HTMLIFrameElement.remove() so the export iframe survives for autopsy
and then measures the staged print DOM: spacers, straddlers, header/brand
equalisation, logo aspect, footer collisions, pane extent.

    python3 tests/pane/exportprobe.py <file.html> <load> [theme]
"""
import asyncio, base64, json, os, subprocess, sys, tempfile
from playwright.async_api import async_playwright
import panefit as PF

PX_PER_MM = 96 / 25.4
PRINT_H_PX = 277 * PX_PER_MM

# ---------------------------------------------------------------- attack loads
def ann(n, text='Announcement line %d about something the club needs to hear tonight'):
    return '\\n'.join(text % (i + 1) for i in range(n))

LOADS = dict(PF.LOADS)

LOADS['empty'] = "() => {}"

LOADS['no-ann'] = """
() => { state.announcementsText = ''; }
"""

# One announcement long enough to be TALLER THAN A PAGE on its own. The
# pagination pass explicitly gives up on any block taller than a page.
LOADS['giant-ann'] = """
() => {
  state.announcementsText = ('The committee wishes to remind every member and guest that '
    + 'the following applies without exception ').repeat(40);
}
"""

# Pane forced past TWO pages: the aside is the tallest thing on the sheet.
LOADS['pane-3page'] = ("() => { state.announcementsText = '" + ann(46) + "'; }")

# Pane far past the 60-iteration guard budget.
LOADS['pane-huge'] = ("() => { state.announcementsText = '" + ann(400) + "'; }")

# Past the 60-iteration guard: the pane pass needs roughly 2 iterations per page.
LOADS['pane-20'] = ("() => { state.announcementsText = '" + ann(530) + "'; }")
LOADS['pane-23'] = ("() => { state.announcementsText = '" + ann(620) + "'; }")
LOADS['pane-28'] = ("() => { state.announcementsText = '" + ann(760) + "'; }")
LOADS['pane-30'] = ("() => { state.announcementsText = '" + ann(830) + "'; }")
LOADS['pane-max'] = ("() => { state.announcementsText = '" + ann(1000) + "'; }")

# Banner blown up: a venue address that wraps the meta row many times.
LOADS['long-venue'] = """
() => {
  state.meeting.location = ('Nee Soon East Community Club, 1 Yishun Avenue 9, #04-01 Culinary Studio, '
    + 'entrance via the side door facing the carpark, Nee Soon East Constituency, Singapore 768893').repeat(4);
  state.meeting.title = 'Chapter Meeting: Voices of a Nation ' + 'and Other Very Long Titles '.repeat(3);
}
"""

# A single agenda row taller than a page, via the sub-note's newline support.
LOADS['tall-row'] = """
() => {
  const s = state.segments.find(x => x.sub !== undefined && !x.isSpeech) || state.segments[0];
  s.sub = Array.from({length: 90}, (_, i) => 'Sub-note line ' + (i + 1)).join('\\n');
}
"""

# Banner just past the point where the brand box out-grows the pane column.
LOADS['tall-banner'] = """
() => {
  state.meeting.title = 'Chapter Meeting: Voices of a Nation';
  state.meeting.dateDisplay = 'Thursday, 13 August 2026';
  state.meeting.cadence = 'We meet every 2nd and 4th Thursday of the month from 7:00PM to 9:30PM, and on the 5th Thursday when the calendar allows it';
  state.meeting.location = 'Nee Soon East Community Club, 1 Yishun Avenue 9, #04-01 (Culinary Studio), Singapore 768893, entrance via the side door facing the carpark';
}
"""

SETUP = """
() => {
  window.__cap = {pdf: null, banners: []};
  window.__origSave = window.saveBlob;
  window.saveBlob = (blob, name) => new Promise(res => {
    const fr = new FileReader();
    fr.onload = () => { window.__cap.pdf = {name, size: blob.size, b64: fr.result.split(',')[1]}; res(); };
    fr.readAsDataURL(blob);
  });
  window.__origBanner = window.showBanner;
  window.showBanner = (msg, bad) => { window.__cap.banners.push(String(msg)); };
  HTMLIFrameElement.prototype.remove = function(){ this.setAttribute('data-kept', '1'); };
}
"""

BREAKS_JS = """
() => {
  const PX=96/25.4, PAGE=277*PX;
  const fr=Array.from(document.querySelectorAll('iframe[data-kept]')).pop();
  if(!fr) return null;
  const d=fr.contentDocument, page=d.querySelector('.page');
  const pt=page.getBoundingClientRect().top, H=page.getBoundingClientRect().height;
  const pages=Math.max(1,Math.round(H/PAGE));
  const rows=Array.from(d.querySelectorAll('tbody tr')).filter(r=>!r.classList.contains('pg-spacer'));
  const out=[];
  for(let i=1;i<pages;i++){
    const B=i*PAGE;
    const first=rows.find(r=>(r.getBoundingClientRect().top-pt)>=B-0.5);
    out.push(first ? (first.querySelector('td').textContent||'').trim() : '(no row)');
  }
  return out;
}
"""

AUTOPSY = """
() => {
  const PX = 96/25.4, PAGE = 277*PX, FOOTMM = 6.5;
  const fr = Array.from(document.querySelectorAll('iframe[data-kept]')).pop();
  if(!fr) return {error: 'no export iframe kept'};
  const d = fr.contentDocument, w = fr.contentWindow;
  const page = d.querySelector('.page');
  const aside = d.querySelector('aside.ref-pane');
  const foot = d.querySelector('footer');
  const hdr = d.querySelector('header');
  const brand = d.querySelector('.pane-brand');
  const img = brand && brand.querySelector('img');
  const pt = page.getBoundingClientRect().top;
  const pageH = page.getBoundingClientRect().height;
  const pages = Math.max(1, Math.round(pageH / PAGE));
  const footH = foot ? foot.getBoundingClientRect().height : 0;

  // header / brand equalisation
  const hr = hdr ? hdr.getBoundingClientRect() : null;
  const br = brand ? brand.getBoundingClientRect() : null;
  let imgInfo = null;
  if(img){
    const ir = img.getBoundingClientRect();
    imgInfo = {w: ir.width, h: ir.height, natW: img.naturalWidth, natH: img.naturalHeight,
               aspectRendered: ir.width/ir.height, aspectNatural: img.naturalWidth/img.naturalHeight};
  }
  // does the header CONTENT overflow the height that was pinned on it?
  let hdrContentBottom = 0;
  if(hdr) for(const el of hdr.querySelectorAll('*'))
    hdrContentBottom = Math.max(hdrContentBottom, el.getBoundingClientRect().bottom);

  // spacers inserted by the pagination pass
  const spTr  = Array.from(d.querySelectorAll('tr.pg-spacer'));
  const spDiv = Array.from(d.querySelectorAll('div.pg-spacer'));

  // straddlers LEFT BEHIND at every page boundary
  const cands = Array.from(d.querySelectorAll(
    'tbody tr, aside h3, aside .exco-item, aside .announce-line, aside .path-legend div'));
  const straddle = [], footClash = [];
  for(let i = 1; i < pages; i++){
    const B = i*PAGE;
    for(const el of cands){
      const b = el.getBoundingClientRect();
      const top = b.top - pt, bot = b.bottom - pt;
      if(top < B - 0.5 && bot > B + 0.5)
        straddle.push({page: i, tag: el.tagName.toLowerCase(), cls: el.className,
                       h: +b.height.toFixed(1), cut: +(B - top).toFixed(1),
                       txt: (el.textContent||'').trim().slice(0, 46)});
      // content that the stamped footer strip will paint over on pages 1..n-1
      if(bot > B - footH + 0.5 && top < B - 0.5)
        footClash.push({page: i, tag: el.tagName.toLowerCase(), cls: el.className,
                        overlapPx: +(bot - (B - footH)).toFixed(1),
                        txt: (el.textContent||'').trim().slice(0, 46)});
    }
  }
  const ar = aside ? aside.getBoundingClientRect() : null;
  const paneKids = aside ? Array.from(aside.querySelector('.pane-body').children) : [];
  const paneBottom = paneKids.length
    ? Math.max(...paneKids.map(k => k.getBoundingClientRect().bottom)) - pt : 0;
  const paneBody = aside ? aside.querySelector('.pane-body') : null;
  const pbr = paneBody ? paneBody.getBoundingClientRect() : null;
  return {
    pages, pageH: +pageH.toFixed(1), pageMm: +(pageH/PX).toFixed(1), footH: +footH.toFixed(1),
    hdrH: hr ? +hr.height.toFixed(1) : null, brandH: br ? +br.height.toFixed(1) : null,
    hdrInline: hdr ? hdr.style.height : null, brandInline: brand ? brand.style.height : null,
    hdrContentOverflowPx: hr ? +(hdrContentBottom - hr.bottom).toFixed(1) : null,
    img: imgInfo,
    spacersTr: spTr.length, spacersDiv: spDiv.length,
    spacerTrH: spTr.map(s => +s.getBoundingClientRect().height.toFixed(1)),
    spacerDivH: spDiv.map(s => +s.getBoundingClientRect().height.toFixed(1)),
    straddlers: straddle, footClashes: footClash.slice(0, 12), footClashCount: footClash.length,
    asideTop: ar ? +(ar.top - pt).toFixed(1) : null,
    asideH: ar ? +ar.height.toFixed(1) : null,
    asideBottomGapPx: ar ? +(pageH - (ar.bottom - pt)).toFixed(1) : null,
    paneBodyH: pbr ? +pbr.height.toFixed(1) : null,
    paneContentBottom: +paneBottom.toFixed(1),
    paneOverrunPx: +(paneBottom - (pageH - footH)).toFixed(1),
  };
}
"""


async def run(path, load, theme='classic', keep_png=None):
    script = LOADS[load]
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={'width': PF.PAGE_W, 'height': 1000})
        await ctx.route('http*://**', lambda r: asyncio.ensure_future(r.abort()))
        page = await ctx.new_page()
        errs = []
        page.on('pageerror', lambda e: errs.append(str(e)))
        await page.goto('file://' + os.path.abspath(path), wait_until='domcontentloaded')
        await page.wait_for_timeout(700)
        await page.evaluate(SETUP)
        await page.evaluate(script)
        await page.evaluate("t => { state.theme = t; }", theme)
        t0 = asyncio.get_event_loop().time()
        try:
            await asyncio.wait_for(page.evaluate("() => downloadPdfImage()"), timeout=420)
        except asyncio.TimeoutError:
            errs.append('downloadPdfImage TIMED OUT after 420s')
        ms = int((asyncio.get_event_loop().time() - t0) * 1000)
        # saveBlob is not awaited by downloadPdfImage, so the FileReader for a
        # large PDF can still be running. Poll rather than race it.
        for _ in range(120):
            if await page.evaluate("() => !!(window.__cap && window.__cap.pdf)"): break
            await page.wait_for_timeout(500)
        cap = await page.evaluate("() => window.__cap")
        au = await page.evaluate(AUTOPSY)
        brk = await page.evaluate(BREAKS_JS)
        pdfpath = None
        if cap.get('pdf'):
            fd, pdfpath = tempfile.mkstemp(suffix='.pdf', prefix='%s-%s-' % (load, theme),
                                           dir=os.path.dirname(os.path.abspath(__file__)))
            os.close(fd)
            open(pdfpath, 'wb').write(base64.b64decode(cap['pdf']['b64']))
        await b.close()
    return {'load': load, 'theme': theme, 'ms': ms, 'errors': errs, 'breaks': brk,
            'banners': cap.get('banners', []),
            'pdfSize': cap['pdf']['size'] if cap.get('pdf') else None,
            'pdfPath': pdfpath, 'autopsy': au}


def pdfpages(p):
    if not p: return None
    out = subprocess.run(['pdfinfo', p], capture_output=True, text=True).stdout
    for l in out.splitlines():
        if l.startswith('Pages:'): return int(l.split(':')[1])
    return None


async def main():
    path, load = sys.argv[1], sys.argv[2]
    theme = sys.argv[3] if len(sys.argv) > 3 else 'classic'
    r = await run(path, load, theme)
    r['pdfPages'] = pdfpages(r['pdfPath'])
    print(json.dumps(r, indent=1)[:6000])

if __name__ == '__main__':
    asyncio.run(main())
