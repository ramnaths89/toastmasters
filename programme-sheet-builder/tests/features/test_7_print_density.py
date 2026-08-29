"""Print-density compaction must be PRINT-ONLY (and stay that way in V31).

The sheet's printed rows were tightened to buy back vertical space. Every one of
those declarations lives inside @media print, so this suite asserts two things:

  * under print media the compacted values are in force;
  * under screen media the ORIGINAL values are still in force, and the on-screen
    geometry of the sheet is byte-for-byte identical to the previous shipped
    build for the same meeting - which is the real "screen is unaffected" claim.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import FILL_JS, PREV, open_app, run_suite  # noqa: E402

SHEET_W = 900

# Values declared outside @media print in src/03_sheetcss.js. These are what a
# screen render - the live preview, the downloaded HTML opened in a browser -
# must still compute to.
SCREEN_EXPECT = {
    "tbody td": {"paddingTop": "8px", "paddingLeft": "10px", "lineHeight": "18.46px"},
    "thead th": {"paddingTop": "8px", "paddingLeft": "10px"},
    ".poetts": {"rowGap": "1px", "lineHeight": "17.4px", "marginTop": "4px"},
    ".role-roster": {"rowGap": "1px", "lineHeight": "17.4px", "marginTop": "4px"},
    "td.item .item-sub": {"fontSize": "12.3px", "marginTop": "2px"},
}
# .theme-strip ("Roles still open: ...") only renders when a role is unfilled, so
# it is measured on its own sheet below.
STRIP_SCREEN = {"paddingTop": "8px", "paddingLeft": "14px", "fontSize": "13px"}
STRIP_PRINT = {"paddingTop": "4px", "paddingLeft": "12px", "fontSize": "11.5px"}
# Values declared inside @media print - the compaction.
PRINT_EXPECT = {
    "tbody td": {"paddingTop": "4.5px", "paddingLeft": "10px", "lineHeight": "17.68px"},
    "thead th": {"paddingTop": "6px", "paddingLeft": "10px"},
    ".poetts": {"rowGap": "0px", "lineHeight": "16.08px", "marginTop": "2px"},
    ".role-roster": {"rowGap": "0px", "lineHeight": "16.08px", "marginTop": "2px"},
    # 11.5 -> 11px in V37, when the five per-theme density patches were replaced
    # by one set that applies to every theme. Three of those patches were being
    # silently discarded by the CSS parser anyway (an orphaned declaration left
    # by a deleted retired-theme selector), so several themes were printing
    # denser than others. line-height follows font-size at 1.3.
    "td.item .item-sub": {"fontSize": "11px", "lineHeight": "14.3px"},
}

# The reference pane down the left of the sheet. Its print typography was
# compacted in V31; none of it may leak onto the screen.
PANE_SELECTORS = [
    "aside h3", ".exco-block", ".exco-item", ".exco-role", ".exco-name", ".exco-sub",
    ".links a", ".path-legend div", ".announcements .announce-line",
]
# Only the FONT SIZES are pinned as absolutes - they are the design intent and
# the readability floor. Line-heights and margins have been retuned more than
# once, so they are checked as a DIFFERENTIAL against the previous build instead
# of as constants that go stale every time the pane is adjusted.
PANE_PRINT_FONT = {
    "aside h3": "9.5px",
    ".exco-role": "9.5px",
    ".exco-name": "10px",
    ".exco-sub": "8.5px",
    ".links a": "9px",
    ".path-legend div": "9px",
    ".announcements .announce-line": "9px",
}
PANE_MEASURE = """sel => {
  const e = document.querySelector(sel);
  if(!e) return null;
  const c = getComputedStyle(e);
  return {fontSize:c.fontSize, lineHeight:c.lineHeight, marginBottom:c.marginBottom,
          paddingBottom:c.paddingBottom, marginTop:c.marginTop, letterSpacing:c.letterSpacing};
}"""
# Smallest font-size anywhere in the printed pane - the readability floor.
PANE_MIN_FONT = """() => {
  const aside = document.querySelector('aside');
  if(!aside) return null;
  let min = Infinity, who = '';
  aside.querySelectorAll('*').forEach(e => {
    if(!e.textContent.trim()) return;
    const fs = parseFloat(getComputedStyle(e).fontSize);
    if(fs < min){ min = fs; who = e.tagName + '.' + (e.className||'').toString().slice(0,30); }
  });
  return {min, who};
}"""

MEASURE = """sel => {
  const e = document.querySelector(sel);
  if(!e) return null;
  const c = getComputedStyle(e);
  return {paddingTop:c.paddingTop, paddingLeft:c.paddingLeft, lineHeight:c.lineHeight,
          rowGap:c.rowGap, marginTop:c.marginTop, fontSize:c.fontSize};
}"""

# Geometry of the whole sheet, for the screen-unaffected comparison.
GEOM = """() => {
  const pg = document.querySelector('.page');
  const rows = [...document.querySelectorAll('tbody tr')];
  return {
    pageH: Math.round(pg.getBoundingClientRect().height),
    pageW: Math.round(pg.getBoundingClientRect().width),
    tableH: Math.round(document.querySelector('table').getBoundingClientRect().height),
    theadH: Math.round(document.querySelector('thead').getBoundingClientRect().height),
    nRows: rows.length,
    rowH: rows.map(r => Math.round(r.getBoundingClientRect().height)),
    paneW: Math.round((document.querySelector('aside')||{getBoundingClientRect:()=>({width:0})})
                        .getBoundingClientRect().width),
    paneH: Math.round((document.querySelector('aside')||{getBoundingClientRect:()=>({height:0})})
                        .getBoundingClientRect().height),
    rosterH: Math.round((document.querySelector('.role-roster')||{getBoundingClientRect:()=>({height:0})})
                          .getBoundingClientRect().height),
    poettsH: Math.round((document.querySelector('.poetts')||{getBoundingClientRect:()=>({height:0})})
                          .getBoundingClientRect().height),
  };
}"""


async def sheet_page(ctx, html, media="screen"):
    pg = await ctx.new_page()
    await pg.set_viewport_size({"width": SHEET_W, "height": 1200})
    await pg.route("**/fonts.googleapis.com/**", lambda r: asyncio.ensure_future(r.abort()))
    await pg.route("**/fonts.gstatic.com/**", lambda r: asyncio.ensure_future(r.abort()))
    await pg.set_content(html, wait_until="load")
    await pg.emulate_media(media=media)
    await pg.wait_for_timeout(350)
    return pg


async def main(ctx, s):
    # ---------- build the same meeting in both builds ----------
    prev = await open_app(ctx, PREV)
    await prev.page.evaluate(FILL_JS)
    await prev.page.wait_for_timeout(500)
    html_prev = await prev.page.evaluate("() => buildSheetHTML(false)")

    app = await open_app(ctx)
    p = app.page
    await p.evaluate(FILL_JS)
    await p.wait_for_timeout(500)
    html_now = await p.evaluate("() => buildSheetHTML(false)")

    # ---------- 7.1 screen media keeps the ORIGINAL values ----------
    scr = await sheet_page(ctx, html_now, "screen")
    bad = []
    for sel, want in SCREEN_EXPECT.items():
        got = await scr.evaluate(MEASURE, sel)
        if got is None:
            bad.append((sel, "element missing"))
            continue
        for k, v in want.items():
            if got.get(k) != v:
                bad.append((sel, k, got.get(k), v))
    s.check("7.1 on SCREEN the sheet keeps every pre-compaction value", not bad, f"{bad[:6]}")

    # ---------- 7.2 print media applies the compaction ----------
    prn = await sheet_page(ctx, html_now, "print")
    bad = []
    for sel, want in PRINT_EXPECT.items():
        got = await prn.evaluate(MEASURE, sel)
        if got is None:
            bad.append((sel, "element missing"))
            continue
        for k, v in want.items():
            if got.get(k) != v:
                bad.append((sel, k, got.get(k), v))
    s.check("7.2 in PRINT the compacted values are in force", not bad, f"{bad[:6]}")

    # ---------- 7.3 the compaction actually shortens the printed sheet ----------
    g_scr = await scr.evaluate(GEOM)
    g_prn = await prn.evaluate(GEOM)
    # ---------- 7.2b the "roles still open" strip ----------
    strip_html = await p.evaluate(
        "() => { const keep = state.roles.timer; state.roles.timer = '';"
        " const h = buildSheetHTML(false); state.roles.timer = keep; return h; }")
    sbad = []
    for media, want in (("screen", STRIP_SCREEN), ("print", STRIP_PRINT)):
        sp = await sheet_page(ctx, strip_html, media)
        got = await sp.evaluate(MEASURE, ".theme-strip")
        if got is None:
            sbad.append((media, "strip missing"))
        else:
            for k, v in want.items():
                if got.get(k) != v:
                    sbad.append((media, k, got.get(k), v))
        await sp.close()
    s.check("7.2b the still-open-roles strip keeps screen values and compacts in print",
            not sbad, f"{sbad[:6]}")

    s.check("7.3 the print table is shorter than the screen table (compaction works)",
            g_prn["tableH"] < g_scr["tableH"],
            f"screen={g_scr['tableH']}px print={g_prn['tableH']}px")
    s.eq("7.4 compaction changes no row COUNT", g_prn["nRows"], g_scr["nRows"])
    # ---------- 7.19 the reference pane in print ----------
    pbad = []
    for sel, want in PANE_PRINT_FONT.items():
        got = await prn.evaluate(PANE_MEASURE, sel)
        if got is None:
            pbad.append((sel, "element missing from the sheet"))
        elif got.get("fontSize") != want:
            pbad.append((sel, "fontSize", got.get("fontSize"), want))
    s.check("7.19 the printed reference pane holds its font sizes", not pbad, f"{pbad[:6]}")

    # every pane metric must match the PREVIOUS build exactly - this is the real
    # "the pane was not touched" test, and it does not go stale when the pane is
    # deliberately retuned (it fails loudly on the build that retunes it).
    prn_prev = await sheet_page(ctx, html_prev, "print")
    pdiff = []
    for sel in PANE_SELECTORS:
        a = await prn.evaluate(PANE_MEASURE, sel)
        b = await prn_prev.evaluate(PANE_MEASURE, sel)
        if a != b:
            pdiff.append((sel, a, b))
    s.check("7.19b the printed pane metrics are identical to the previous build",
            not pdiff, f"{pdiff[:4]}")
    await prn_prev.close()

    # the officers' names deliberately stay at 10px
    nm = await prn.evaluate(PANE_MEASURE, ".exco-name")
    s.eq("7.20 the officers' names stay at 10px in print", nm["fontSize"], "10px")

    # readability floor
    floor = await prn.evaluate(PANE_MIN_FONT)
    s.check("7.21 nothing in the printed pane computes below 8.5px",
            floor is not None and floor["min"] >= 8.5,
            f"smallest={floor and floor['min']}px on {floor and floor['who']}")

    # the compaction must actually shorten the pane
    s.check("7.22 the printed pane is shorter than the screen pane",
            g_prn["paneH"] < g_scr["paneH"],
            f"screen={g_scr['paneH']}px print={g_prn['paneH']}px")
    await prn.close()

    # ---------- 7.5 screen geometry identical to the previous shipped build ----------
    scr_prev = await sheet_page(ctx, html_prev, "screen")
    g_prev = await scr_prev.evaluate(GEOM)
    s.eq("7.5 screen page height unchanged vs the previous build (V32)", g_scr["pageH"], g_prev["pageH"])
    s.eq("7.6 screen table height unchanged vs the previous build (V32)", g_scr["tableH"], g_prev["tableH"])
    s.eq("7.7 screen thead height unchanged vs the previous build (V32)", g_scr["theadH"], g_prev["theadH"])
    s.eq("7.8 screen row count unchanged vs the previous build (V32)", g_scr["nRows"], g_prev["nRows"])
    diff = [(i, a, b) for i, (a, b) in enumerate(zip(g_scr["rowH"], g_prev["rowH"])) if a != b]
    s.check("7.9 every screen row height is identical to the previous build (V32)", not diff, f"{diff[:6]}")
    s.eq("7.10 screen role-roster block height unchanged vs the previous build (V32)",
         g_scr["rosterH"], g_prev["rosterH"])
    s.eq("7.11 screen POETTS block height unchanged vs the previous build (V32)", g_scr["poettsH"], g_prev["poettsH"])
    s.eq("7.23 screen pane width unchanged vs the previous build (V32)",
         g_scr["paneW"], g_prev["paneW"])
    s.eq("7.24 screen pane height unchanged vs the previous build (V32)",
         g_scr["paneH"], g_prev["paneH"])
    # every pane declaration, measured on screen, must be byte-identical to V30
    leak = []
    for sel in PANE_SELECTORS:
        a = await scr.evaluate(PANE_MEASURE, sel)
        b = await scr_prev.evaluate(PANE_MEASURE, sel)
        if a != b:
            leak.append((sel, a, b))
    s.check("7.25 no pane print value leaked onto the screen (identical to the previous build)",
            not leak, f"{leak[:4]}")
    await scr_prev.close()
    await scr.close()
    await prev.page.close()

    # ---------- 7.12 the LIVE PREVIEW iframe is screen media and unaffected ----------
    await p.evaluate("() => renderPreviewNow()")
    await p.wait_for_timeout(500)
    fr = p.frame_locator("#previewFrame")
    live = await fr.locator("tbody td").first.evaluate(
        "e => { const c = getComputedStyle(e);"
        " return {p:c.paddingTop, lh:c.lineHeight}; }")
    s.eq("7.12 the live preview renders at the SCREEN padding, not the print one",
         live["p"], "8px")
    s.eq("7.13 the live preview keeps the screen line-height", live["lh"], "18.46px")
    live_gap = await fr.locator(".poetts").first.evaluate(
        "e => getComputedStyle(e).rowGap")
    s.eq("7.14 the live preview keeps the screen POETTS row-gap", live_gap, "1px")

    # text must still be readable out of the iframe (every other suite depends on it)
    txt = await fr.locator("body").inner_text()
    for needle in ("Voices of a Nation", "Prepared Speech 1", "Speaker Name 1",
                   "Member Name 1", "Table Topics"):
        s.check(f"7.15 preview iframe text still contains {needle!r}", needle in txt, "")

    # ---------- 7.16 the builder's own chrome is untouched ----------
    chrome = await p.evaluate(
        """() => {
             const r = {};
             ['.form-pane','.preview-pane','#splitter','.toolbar'].forEach(sel=>{
               const e = document.querySelector(sel);
               const b = e ? e.getBoundingClientRect() : null;
               r[sel] = b ? {w:Math.round(b.width), h:Math.round(b.height)} : null;
             });
             return r;
           }"""
    )
    s.check("7.16 the builder panes still fill the window side by side",
            chrome[".form-pane"]["w"] > 300 and chrome[".preview-pane"]["w"] > 300
            and chrome["#splitter"]["w"] > 0, str(chrome))

    # ---------- 7.17 no errors ----------
    s.check("7.17 zero uncaught page errors during the density checks",
            not app.clean_errors(), str(app.clean_errors()[:3]))
    s.check("7.18 zero console errors during the density checks",
            not app.clean_console(), str(app.clean_console()[:3]))


if __name__ == "__main__":
    asyncio.run(run_suite(main, "7_print_density"))
