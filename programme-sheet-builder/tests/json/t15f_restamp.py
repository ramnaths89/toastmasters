from harness import App, head
head("probe — what rewrites localStorage during startup?")
with App() as a:
    a.page.add_init_script("""
      (function(){ const real = Storage.prototype.setItem;
        window.__SETS = [];
        Storage.prototype.setItem = function(k,v){
          if(k && k.indexOf('nse-programme-builder')===0){
            window.__SETS.push({t: Math.round(performance.now()),
              stack: (new Error()).stack.split('\\n').slice(1,6).join(' | ')});
          }
          return real.apply(this, arguments); }; })();""")
    a.page.reload(wait_until="domcontentloaded", timeout=90000)
    a.wait(1500)
    for s in a.js("()=>window.__SETS") or []:
        print("  +%sms  %s" % (s["t"], s["stack"][:300]))
        print()
