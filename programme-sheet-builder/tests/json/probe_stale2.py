from harness import App, head
head("probe: why the savedAt stamp never matches")
with App() as a:
    r = a.js("""()=>{ const t = meetingPayload();
        return { snippet: t.slice(0,120),
                 tight: !!t.match(/"savedAt":"[^"]+"/),
                 loose: !!t.match(/"savedAt":\\s*"[^"]+"/),
                 stampTight: (t.match(/"savedAt":"[^"]+"/)||[''])[0],
                 stampLoose: (t.match(/"savedAt":\\s*"[^"]+"/)||[''])[0] }; }""")
    for k, v in r.items():
        print("  %-11s %r" % (k, v))
