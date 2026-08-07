#!/usr/bin/env python3
"""Assemble the single-file programme-sheet generator from the parts in this folder.

  skeleton.html + builder.css + sheet.css + app.js + app2.js + ti-logo.b64 + pathways_data.json
        -> NSE_Programme_Generator.html

Every part is a real file — this script only substitutes placeholders. It must never
WRITE any of the parts back (an earlier version regenerated builder.css from an inline
string and silently reverted weeks of edits).
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
def part(name):
    with open(os.path.join(HERE, name), encoding='utf-8') as f:
        return f.read()

# sheet.css is injected into a JS template literal in skeleton.html, so a
# backtick or ${ anywhere in it silently breaks the entire app at parse time.
sheet_css = part('sheet.css')
for bad in ('`', '${'):
    if bad in sheet_css:
        line = sheet_css[:sheet_css.index(bad)].count('\n') + 1
        sys.exit('sheet.css line %d contains %r - it is embedded in a JS template '
                 'literal and would break the build. Use straight quotes.' % (line, bad))

for lib in ('h2c.js',):
    if '</script' in part(lib).lower():
        sys.exit(lib + ' contains a literal </script> and cannot be inlined as-is.')

pathways = json.dumps(json.loads(part('pathways_data.json')), ensure_ascii=False)

out = part('skeleton.html')
for token, value in [
    ('__BUILDER_CSS__',   part('builder.css')),
    ('__SHEET_CSS__',     sheet_css),
    ('__PATHWAYS_DATA__', pathways),
    ('__APP_JS__',        part('app.js')),
    ('__APP2_JS__',       part('app2.js')),
    # Bundled, not CDN-loaded: Rama exports images at club meetings on whatever
    # wifi is going, and a self-contained file is the whole point of this tool.
    # (jsPDF was dropped in V23 - the hand-rolled pdfFromJpegs() in app2.js
    # replaced its single use at 1/200th the size.)
    ('__H2C_JS__',        part('h2c.js')),
    ('__LOGO_B64__',      part('ti-logo.b64').strip()),   # last: appears twice
]:
    if token not in out:
        sys.exit('placeholder missing from skeleton.html: ' + token)
    out = out.replace(token, value)

for leftover in ('__BUILDER_CSS__','__SHEET_CSS__','__PATHWAYS_DATA__','__APP_JS__','__APP2_JS__','__LOGO_B64__','__H2C_JS__'):
    assert leftover not in out, leftover

dest = os.path.join(HERE, 'NSE_Programme_Generator.html')
with open(dest, 'w', encoding='utf-8') as f:
    f.write(out)
print('built %s  (%.0f KB)' % (dest, len(out)/1024))
