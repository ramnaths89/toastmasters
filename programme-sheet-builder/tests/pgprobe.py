import os
APP = "file://" + os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "index.html"))
import asyncio, subprocess, sys
from playwright.async_api import async_playwright
TH=["classic","zine","swiss","brutalist","retrofuture","handmade"]
async def one(b,sem,k,html):
    async with sem:
        f=f"pp_{k}.html"; open(f,"w").write(html)
        pg=await b.new_page(viewport={"width":794,"height":1123})
        await pg.goto("file://"+os.path.abspath(f),timeout=60000)
        await pg.emulate_media(media="print")
        await pg.pdf(path=f"pp_{k}.pdf",format="A4",print_background=True)
        await pg.close()
        n=int(subprocess.run(["pdfinfo",f"pp_{k}.pdf"],capture_output=True,text=True).stdout.split("Pages:")[1].split()[0])
        return k,n
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch()
        pg=await b.new_page(viewport={"width":1200,"height":900})
        await pg.goto(APP,timeout=60000)
        await pg.evaluate("localStorage.clear()"); await pg.reload(); await pg.wait_for_timeout(900)
        gen=await pg.evaluate("(ks)=>{const o={};for(const k of ks){state.theme=k;o[k]=buildSheetHTML(false);}return o;}",TH)
        await pg.close()
        sem=asyncio.Semaphore(6)
        r=await asyncio.gather(*[one(b,sem,k,h) for k,h in gen.items()])
        await b.close()
    bad=[f"{k}={n}" for k,n in sorted(r) if n!=2]
    print(("ALL 2 PAGES" if not bad else "NOT 2: "+", ".join(bad)))
asyncio.run(main())
