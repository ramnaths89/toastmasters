"""V38: the "Roles still open" strip is a working aid, not part of the sheet.

It must appear in the live preview (where it is telling the person building the
agenda to go and fill those roles) and in NOTHING that leaves the tab: the HTML
download, the PDF, the JPG, and the hidden iframe that measures the pane fit.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import App, head, ok

NEEDLE = "Roles still open"
res = []
with App(build=os.environ.get("PSB_BUILD")) as app:
    head("with roles deliberately left open")
    open_roles = app.js("""()=>{ state.roles.photographer=''; state.roles.saa='';
        renderPreviewNow(); return openRoleLabels(); }""")
    res.append(ok(len(open_roles) >= 2, f"roles are open  | {open_roles}"))

    res.append(ok(NEEDLE in app.js("()=>buildSheetHTML(true)"),
                  "preview render KEEPS the notice"))
    res.append(ok(NEEDLE not in app.js("()=>buildSheetHTML(false)"),
                  "export render DROPS the notice"))

    head("it is really gone from the file the user downloads")
    # downloadSheet() does NOT go through saveBlob - it builds its own Blob and
    # clicks an <a download>. Intercepting saveBlob returned an empty string, and
    # "no notice" passed on it. Intercept createObjectURL instead and read the blob
    # the anchor was actually handed.
    html = app.page.evaluate("""async () => {
      let captured = null;
      const realCOU = URL.createObjectURL;
      URL.createObjectURL = (b) => { captured = b; return realCOU.call(URL, b); };
      try { await downloadSheet(); } finally { URL.createObjectURL = realCOU; }
      return captured ? await captured.text() : ''; }""")
    res.append(ok(len(html) > 20000, f"HTML export produced  | {len(html)} bytes"))
    res.append(ok(NEEDLE not in html, "HTML export has no notice"))
    res.append(ok("Programme Sheet" in html, "HTML export is still the sheet"))
    res.append(ok("FLEXIBLE" in html.upper(), "the FLEXIBLE legend below it survives"))

    head("the live preview iframe still shows it")
    seen = app.js("""()=>{ const f=document.querySelector('iframe');
        try{ return (f.contentDocument.body.innerText||'').includes('Roles still open'); }
        catch(e){ return 'ERR '+e.message; } }""")
    res.append(ok(seen is True, f"visible in the preview pane  | {seen}"))

    head("no notice at all once every role is filled")
    app.js("""()=>{ Object.keys(state.roles).forEach((k,i)=>state.roles[k]='Member '+(i+1));
        renderPreviewNow(); }""")
    res.append(ok(NEEDLE not in app.js("()=>buildSheetHTML(true)"),
                  "preview drops it when nothing is open"))
    res.append(ok(not app.pageerrors, f"no JS errors | {app.pageerrors[:1]}"))

print(f"\n{sum(res)}/{len(res)} passed")
sys.exit(0 if all(res) else 1)
