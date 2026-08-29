"""V42: Retro-Futurism retired, Neo Memphis Pop added.

Also re-runs the check the V39 session's orphaned-declaration finding demands:
every selector written in the stylesheet must survive the browser's parser. That
defect (52 written, 46 built) was invisible for versions and is exactly the kind
of thing deleting a whole theme block can reintroduce.
"""
import os, re, sys
sys.path.insert(0, "/tmp/v39/pkg/tests/json")
from harness import App, head, ok

res = []
BUILD = os.environ.get("PSB_BUILD")
with App(build=BUILD) as app:
    head("the theme list")
    keys = app.js("()=>THEMES.map(t=>t.key)")
    res.append(ok(keys == ['classic', 'zine', 'swiss', 'brutalist', 'neomemphis'],
                  f"five themes, Neo Memphis Pop last | {keys}"))
    name = app.js("()=>{const t=THEMES.find(t=>t.key==='neomemphis');return t&&t.name;}")
    res.append(ok(name == 'Neo Memphis Pop', f"display name | {name!r}"))
    res.append(ok('retrofuture' in app.js("()=>RETIRED_THEMES"),
                  "retrofuture is retired, not merely dropped"))

    head("a meeting saved under Retro-Futurism still opens")
    got = app.js("""()=>{ const st=JSON.parse(JSON.stringify(state)); st.theme='retrofuture';
        adoptState({state:st}); return state.theme; }""")
    res.append(ok(got == 'classic', f"falls back to Classic rather than rendering unstyled | {got}"))

    head("the picker offers it and it applies")
    opts = app.js("""()=>[...document.querySelectorAll('select')]
        .map(s=>[...s.options].map(o=>o.value))
        .filter(v=>v.includes('classic'))[0] || []""")
    res.append(ok('neomemphis' in opts and 'retrofuture' not in opts,
                  f"theme select | {opts}"))
    cls = app.js("""()=>{ state.theme='neomemphis'; renderPreviewNow();
        const f=document.querySelector('iframe');
        try{ return f.contentDocument.body.className; }catch(e){ return 'ERR '+e.message; } }""")
    res.append(ok('th-neomemphis' in str(cls), f"preview body class | {cls}"))

    head("it is actually styled (not falling through to Classic's colours)")
    px = app.js("""()=>{ const f=document.querySelector('iframe'); const d=f.contentDocument;
        const th=d.querySelector('thead th'), tm=d.querySelector('td.time');
        return {th: th?getComputedStyle(th).backgroundColor:null,
                time: tm?getComputedStyle(tm).color:null}; }""")
    res.append(ok(px.get('th') == 'rgb(31, 168, 160)', f"column heads are the turquoise | {px.get('th')}"))
    res.append(ok(px.get('time') == 'rgb(234, 90, 139)', f"times are the coral | {px.get('time')}"))

    head("no retired theme leaks into the built stylesheet")
    # The sheet's CSS lives in the PREVIEW IFRAME, not the top document - the first
    # version of this probe read document.querySelectorAll('style') and scored 0 for
    # both, which would have passed the "no leak" half on an empty string.
    leaked = app.js("""()=>{ const d=document.querySelector('iframe').contentDocument;
        const s=[...d.querySelectorAll('style')].map(e=>e.textContent).join('');
        return {retro: (s.match(/th-retrofuture/g)||[]).length,
                memphis: (s.match(/th-neomemphis/g)||[]).length, chars: s.length}; }""")
    res.append(ok(leaked['chars'] > 20000, f"read a real stylesheet | {leaked['chars']} chars"))
    res.append(ok(leaked['retro'] == 0, f"no Retro-Futurism CSS left | {leaked['retro']}"))
    res.append(ok(leaked['memphis'] > 15, f"Neo Memphis Pop rules present | {leaked['memphis']}"))

    head("every selector written survives the CSS parser (the V39 orphan trap)")
    counts = app.js("""()=>{
        /* el.sheet is null on the iframe's <style>; the document's own
           styleSheets collection is what holds the parsed rules. Errors are
           reported, not swallowed - a silent catch here scored 0 and read as
           "nothing parsed", which is the same false alarm shape as the bug
           this check exists to catch. */
        const d = document.querySelector('iframe').contentDocument;
        let built = 0, err = null;
        const walk = rules => { for(let i=0;i<rules.length;i++){ const r = rules[i];
            if(r.cssRules && r.cssRules.length) walk(r.cssRules);
            else if(r.selectorText) built++; } };
        try{ for(let i=0;i<d.styleSheets.length;i++) walk(d.styleSheets[i].cssRules); }
        catch(e){ err = String(e); }
        return {built, err}; }""")
    res.append(ok(counts['built'] > 200,
                  f"the browser parsed {counts['built']} rules | err={counts['err']}"))
    res.append(ok(not app.pageerrors, f"no JS errors | {app.pageerrors[:1]}"))

print(f"\n{sum(res)}/{len(res)} passed")
sys.exit(0 if all(res) else 1)
