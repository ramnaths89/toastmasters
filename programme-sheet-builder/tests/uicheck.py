import os
APP = "file://" + os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "index.html"))
import asyncio, base64, os
from playwright.async_api import async_playwright
res=[]
def ck(n,ok,x=""):
    res.append(ok); print(("PASS  " if ok else "FAIL  ")+n+(("  | "+str(x)) if x else ""))

async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch()
        pg=await b.new_page(viewport={"width":1500,"height":950})
        errs=[]
        pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(APP,timeout=60000)
        await pg.evaluate("localStorage.clear()"); await pg.reload(); await pg.wait_for_timeout(1200)

        # --- save badge: fixed, constant size, no reflow ---
        pos = await pg.evaluate("getComputedStyle(document.getElementById('saveDot')).position")
        ck("save badge is fixed (out of flow)", pos=="fixed", pos)
        before = await pg.evaluate("document.querySelector('.toolbar').getBoundingClientRect().height")
        # offsetWidth = layout box. getBoundingClientRect() includes the pulse transform,
        # which is composited and cannot reflow -- measuring that would fail a working fix.
        r1 = await pg.evaluate("document.getElementById('saveDot').offsetWidth")
        await pg.evaluate("flashSaved()"); await pg.wait_for_timeout(60)
        r2 = await pg.evaluate("document.getElementById('saveDot').offsetWidth")
        after = await pg.evaluate("document.querySelector('.toolbar').getBoundingClientRect().height")
        ck("badge layout box never changes", r1==r2, (r1,r2))
        ck("toolbar height unaffected by autosave", before==after, (before,after))
        ck("no saveStatus text span left", await pg.evaluate("!document.getElementById('saveStatus')"))

        # --- icon toolbar + tooltips ---
        tips = await pg.evaluate("[...document.querySelectorAll('.toolbar .btn')].map(b=>[b.textContent.trim(), (b.dataset.tip||'').slice(0,28)])")
        ck("every toolbar button is an icon with a tooltip",
           all(len(t)<=2 and tip for t,tip in tips), tips)
        ck("tooltip shows on hover", await pg.evaluate("""(()=>{
             const b=document.querySelector('.toolbar .btn.icon');
             return getComputedStyle(b,'::after').content.includes('Balance');})()"""))

        # --- download menu ---
        await pg.click('#dlBtn'); await pg.wait_for_timeout(200)
        ck("download menu opens", await pg.is_visible('#dlMenu.open'))
        items = await pg.evaluate("[...document.querySelectorAll('#dlMenu button b')].map(e=>e.textContent)")
        ck("menu offers HTML/PDF/JPG only", items==["HTML","PDF","JPG image"], items)
        await pg.keyboard.press("Escape"); await pg.wait_for_timeout(150)
        ck("Escape closes the menu", not await pg.is_visible('#dlMenu.open'))

        # --- help panel ---
        await pg.click('button[aria-label="Instructions"]'); await pg.wait_for_timeout(250)
        ck("instructions panel opens", await pg.is_visible('.help-overlay.open .help-panel'))
        htxt = await pg.inner_text('.help-body')
        want=["Save","Saved meetings","Balance","Download","Printing on paper","Reset","Club Setup","Programme Segments","Timing lights"]
        U=htxt.upper()
        gone=[k for k in want if k.upper() not in U]
        ck("help covers the toolbar and sections", not gone, gone or len(htxt))
        await pg.keyboard.press("Escape"); await pg.wait_for_timeout(200)
        ck("Escape closes instructions", not await pg.is_visible('.help-overlay.open'))

        # --- print icon hidden on touch devices only ---
        # V29: no print button at all -- every PDF is built in-page, on every device,
        # so its size never depends on which destination a print dialog had selected.
        ck("no print button remains", await pg.evaluate(
            "!document.querySelector('.print-only') && typeof printSheet==='undefined'"))
        ck("PDF is always built in-page", await pg.evaluate(
            "typeof downloadPdfImage==='function'"))

        # --- bell 30s past red, on every timing sequence ---
        await pg.evaluate("""()=>{const s=state.segments.find(x=>x.isSpeech);
            s.speakerName='X'; updSpeech(s.id,'durMin','8');}""")
        await pg.wait_for_timeout(500)
        frame = pg.frames[1]
        bells = await frame.evaluate("[...document.querySelectorAll('.sig-bell')].map(e=>e.textContent.trim())")
        reds  = await frame.evaluate("[...document.querySelectorAll('.sig-boxes .br')].map(e=>e.textContent.trim())")
        ck("a bell sits beside every timing sequence", len(bells)==len(reds) and len(bells)>0, (len(bells),len(reds)))
        def plus30(t):
            m,s=t.split(':'); tot=int(m)*60+int(s)+30
            return f"{tot//60}:{tot%60:02d}"
        ck("bell is exactly red + 30 sec",
           all(b.replace('🔔','').strip()==plus30(r) for b,r in zip(bells,reds)),
           list(zip(reds,bells))[:4])

        # --- image export: JPG only, must fit the 200 KB budget ---
        await pg.evaluate("bindMeeting('title','Render Test')")
        out = await pg.evaluate("""async ()=>{
          const c = await renderSheetCanvas();
          const o = await encodeJpegUnder(c, IMAGE_TARGET_BYTES);
          return {w:o.w, h:o.h, q:o.q, size:o.blob.size, baseW:c.width};
        }""")
        ck("renders at high res before downscaling", out["baseW"]>=2600, out["baseW"])
        # 500 KB is the figure the Download menu promises the user. Keep the two in step:
        # if this number moves, the menu text and customise-for-your-club.md move with it.
        ck("JPG fits the 500 KB budget", out["size"]<=500*1024, f'{out["size"]//1024} KB @ {out["w"]}px q{out["q"]}')
        # Capped at MAX_EXPORT_WIDTH (1500) on purpose since V26 -- past this,
        # extra pixels cost quality instead of buying legibility.
        ck("hits the capped export width", out["w"]==1500, out["w"])
        ck("quality is above the graining threshold", out["q"]>=0.7, out["q"])
        ck("PNG export no longer offered", await pg.evaluate(
            "document.querySelector('#dlMenu').innerHTML.indexOf('PNG')<0"))
        ck("no JS errors", not errs, errs[:3])
        await b.close()
    print(f"\n{sum(res)}/{len(res)} passed")
    return 0 if all(res) else 1
raise SystemExit(asyncio.run(main()))
