"""V30 feature 5 - narrow / phone layout (one pane at a time)."""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import open_app, run_suite  # noqa: E402

WIDE = {"width": 1400, "height": 900}
PHONE = {"width": 390, "height": 844}
EDGE_IN = {"width": 900, "height": 800}     # the breakpoint itself: max-width:900 matches
EDGE_OUT = {"width": 901, "height": 800}


async def vis(p, sel):
    return await p.evaluate(
        "s => { const e = document.querySelector(s); if(!e) return null;"
        " const r = e.getBoundingClientRect();"
        " const cs = getComputedStyle(e);"
        " return cs.display !== 'none' && cs.visibility !== 'hidden' && r.width > 0 && r.height > 0; }",
        sel,
    )


async def main(ctx, s):
    app = await open_app(ctx, viewport=WIDE)
    p = app.page

    # ================= 5.1 wide: side by side =================
    await p.set_viewport_size(WIDE)
    await p.wait_for_timeout(400)
    s.check("5.1 [1400px] splitter is visible", await vis(p, "#splitter"))
    s.check("5.2 [1400px] form pane is visible", await vis(p, ".form-pane"))
    s.check("5.3 [1400px] preview pane is visible", await vis(p, ".preview-pane"))
    boxes = await p.evaluate(
        "() => ['.form-pane','.preview-pane'].map(s=>{const r=document.querySelector(s)"
        ".getBoundingClientRect(); return {x:r.x, w:r.width, y:r.y};})")
    s.check("5.4 [1400px] the two panes are side by side, not stacked",
            boxes[1]["x"] >= boxes[0]["x"] + boxes[0]["w"] - 20
            and abs(boxes[0]["y"] - boxes[1]["y"]) < 40, str(boxes))
    s.check("5.5 [1400px] the view tabs are hidden", (await vis(p, ".view-tabs")) is False)
    s.check("5.6 [1400px] the mobile bar is hidden", (await vis(p, ".mobile-bar")) is False)
    s.check("5.7 [1400px] the toolbar download button is visible", await vis(p, "#dlBtn"))
    s.check("5.8 [1400px] isNarrow() is false", await p.evaluate("() => isNarrow()") is False)

    # ================= 5.9 phone =================
    await p.set_viewport_size(PHONE)
    await p.wait_for_timeout(500)
    s.check("5.9 [390px] isNarrow() is true", await p.evaluate("() => isNarrow()") is True)
    s.check("5.10 [390px] the view tabs are visible", await vis(p, ".view-tabs"))
    s.check("5.11 [390px] the mobile bar is visible", await vis(p, ".mobile-bar"))
    s.check("5.12 [390px] the splitter is hidden", (await vis(p, "#splitter")) is False)
    s.check("5.13 [390px] the toolbar download button is hidden",
            (await vis(p, "#dlBtn")) is False)
    s.check("5.14 [390px] the phone download button is visible", await vis(p, "#dlBtnM"))

    fv, pv = await vis(p, ".form-pane"), await vis(p, ".preview-pane")
    s.check("5.15 [390px] exactly ONE pane is visible at a time",
            (fv, pv) == (True, False), f"form={fv} preview={pv}")

    # tab states
    s.eq("5.16 [390px] the Edit tab starts pressed",
         await p.evaluate("() => document.querySelector('[data-view=edit]')"
                          ".getAttribute('aria-pressed')"), "true")

    # ---------- 5.17 Preview / Edit swap ----------
    await p.locator("[data-view=preview]").click()
    await p.wait_for_timeout(500)
    fv, pv = await vis(p, ".form-pane"), await vis(p, ".preview-pane")
    s.check("5.17 clicking 'Preview' hides the form and shows the sheet",
            (fv, pv) == (False, True), f"form={fv} preview={pv}")
    s.eq("5.18 the Preview tab becomes pressed",
         await p.evaluate("() => document.querySelector('[data-view=preview]')"
                          ".getAttribute('aria-pressed')"), "true")
    s.eq("5.19 the Edit tab becomes unpressed",
         await p.evaluate("() => document.querySelector('[data-view=edit]')"
                          ".getAttribute('aria-pressed')"), "false")
    s.check("5.20 the body carries the show-preview class",
            await p.evaluate("() => document.body.classList.contains('show-preview')"))
    frame_text = await p.frame_locator("#previewFrame").locator("body").inner_text()
    s.check("5.21 the preview iframe actually has the sheet in it",
            "Toastmasters" in frame_text, frame_text[:120])

    await p.locator("[data-view=edit]").click()
    await p.wait_for_timeout(400)
    fv, pv = await vis(p, ".form-pane"), await vis(p, ".preview-pane")
    s.check("5.22 clicking 'Edit' swaps back to the form",
            (fv, pv) == (True, False), f"form={fv} preview={pv}")
    s.check("5.23 the show-preview class is removed",
            not await p.evaluate("() => document.body.classList.contains('show-preview')"))

    # ---------- 5.24 nothing overflows horizontally ----------
    await p.evaluate("() => window.scrollTo(0,0)")
    ov = await p.evaluate(
        "() => ({sw: document.documentElement.scrollWidth, iw: window.innerWidth,"
        " bw: document.body.scrollWidth})")
    s.check(f"5.24 [390px, edit view] nothing overflows horizontally "
            f"(scrollWidth {ov['sw']} <= innerWidth {ov['iw']})",
            ov["sw"] <= ov["iw"], str(ov))

    # widest offender, if any
    wide_el = await p.evaluate(
        """() => { const w = window.innerWidth; let worst = null;
             document.querySelectorAll('*').forEach(e=>{
               const r = e.getBoundingClientRect();
               if(r.right > w + 1 && (!worst || r.right > worst.right))
                 worst = {right: Math.round(r.right), tag: e.tagName,
                          cls: (e.className||'').toString().slice(0,60), id: e.id};
             }); return worst; }"""
    )
    s.check("5.25 [390px] no element extends past the viewport", wide_el is None, str(wide_el))

    await p.locator("[data-view=preview]").click()
    await p.wait_for_timeout(500)
    ov2 = await p.evaluate(
        "() => ({sw: document.documentElement.scrollWidth, iw: window.innerWidth})")
    s.check(f"5.26 [390px, preview view] nothing overflows horizontally "
            f"(scrollWidth {ov2['sw']} <= innerWidth {ov2['iw']})",
            ov2["sw"] <= ov2["iw"], str(ov2))

    # ---------- 5.27 resizing back to wide must not strand the user ----------
    # (still in preview view from above)
    s.check("5.27 precondition: narrow + preview view",
            await p.evaluate("() => document.body.classList.contains('show-preview')"))
    await p.set_viewport_size(WIDE)
    await p.wait_for_timeout(600)
    fv, pv = await vis(p, ".form-pane"), await vis(p, ".preview-pane")
    s.check("5.28 resizing narrow-in-preview back to wide leaves the FORM visible",
            fv is True, f"form={fv} preview={pv}")
    s.check("5.29 and the preview pane back beside it", pv is True, f"preview={pv}")
    s.check("5.30 the show-preview class is dropped on widening",
            not await p.evaluate("() => document.body.classList.contains('show-preview')"))
    s.check("5.31 the splitter is back", await vis(p, "#splitter"))

    # Do it again via a rotate-like resize (phone landscape) to make sure the
    # handler is not one-shot.
    await p.set_viewport_size(PHONE)
    await p.wait_for_timeout(350)
    await p.locator("[data-view=preview]").click()
    await p.wait_for_timeout(350)
    await p.set_viewport_size({"width": 844, "height": 390})   # still narrow
    await p.wait_for_timeout(350)
    s.check("5.32 rotating to a still-narrow landscape keeps the preview view",
            await p.evaluate("() => document.body.classList.contains('show-preview')"))
    await p.set_viewport_size(WIDE)
    await p.wait_for_timeout(400)
    s.check("5.33 widening from landscape narrow also returns to the form",
            await vis(p, ".form-pane") is True
            and not await p.evaluate("() => document.body.classList.contains('show-preview')"))

    # ---------- 5.34 the breakpoint itself ----------
    await p.set_viewport_size(EDGE_IN)
    await p.wait_for_timeout(350)
    s.check("5.34 [900px] is narrow (max-width:900 inclusive)",
            await p.evaluate("() => isNarrow()") is True)
    s.check("5.35 [900px] the view tabs are shown", await vis(p, ".view-tabs"))
    await p.set_viewport_size(EDGE_OUT)
    await p.wait_for_timeout(350)
    s.check("5.36 [901px] is wide", await p.evaluate("() => isNarrow()") is False)
    s.check("5.37 [901px] the view tabs are hidden", (await vis(p, ".view-tabs")) is False)
    s.check("5.38 [901px] the splitter is back", await vis(p, "#splitter"))

    # ---------- 5.39 narrow layout is not persisted into the meeting ----------
    await p.set_viewport_size(PHONE)
    await p.wait_for_timeout(300)
    await p.locator("[data-view=preview]").click()
    await p.wait_for_timeout(300)
    payload = await p.evaluate("() => meetingPayload()")
    s.check("5.39 the pane view is a viewport fact, not saved into the .json",
            "mobileView" not in payload and "show-preview" not in payload, "")

    # ---------- 5.40 phone bar actions work ----------
    s.check("5.40 the phone Save button opens the save dialog",
            await p.evaluate(
                "() => { document.querySelector('.mobile-bar .btn.secondary').click();"
                " const o = document.getElementById('saveDialog').classList.contains('open');"
                " closeSaveDialog(); return o; }"))

    # ---------- 5.41 errors ----------
    s.check("5.41 zero uncaught page errors during feature 5", not app.clean_errors(),
            str(app.clean_errors()[:3]))
    s.check("5.42 zero console errors during feature 5", not app.clean_console(),
            str(app.clean_console()[:3]))


if __name__ == "__main__":
    asyncio.run(run_suite(main, "5_layout"))
