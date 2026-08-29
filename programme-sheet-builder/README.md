# Programme Sheet Builder (V45)

Single-file Toastmasters agenda builder for Nee Soon East, District 80 — also
usable by any club via Club Setup. **V45** is the V44 builder (contest mode,
JPG footer fix, Break 10–20) published into this repo with officer names as
placeholders.

**Live:** https://ramnaths89.github.io/toastmasters/programme-sheet-builder/

Do not hand-edit `index.html`. Edit `src/`, then:

```
python3 build.py ProgSheetGenV45.html   # local monolith (gitignored)
python3 publish.py index.html           # GitHub copy: placeholders + name gate
```

`publish.py` refuses to write a file that still contains a real officer name.
Club identity (name, venue, Slido codes) is left in on purpose — see
[customise-for-your-club.md](customise-for-your-club.md).

## Parts

| part | contents |
|---|---|
| `00_head_open.html` | doctype, head, fonts link |
| `01_builder.css` | the builder UI |
| `02_body.html` | the form markup |
| `03_sheetcss.js` | printed sheet CSS (all themes + `@media print`), Pathways, logo |
| `04_h2c.js` | html2canvas 1.4.1 |
| `05_app.js` | state, presets, `defaultState()`, `adoptState()` |
| `06_app2.js` | render, export, save, pane-fit |
| `07_tail.html` | closing tags |

`03_sheetcss.js` is injected into a JS template literal. A backtick or `${` in
it kills the app. `build.py` refuses all three traps (backtick/`${`, `</script>`,
raw control characters). After every build:

```
python3 -c "import re;s=open('index.html',encoding='utf-8').read();open('/tmp/a.js','w',encoding='utf-8').write('\n;\n'.join(re.findall(r'<script>(.*?)</script>',s,re.S)))"
node --check /tmp/a.js
```

Do not change print CSS or default segment durations without running
`tests/pane/pgprobe5.py` (or `tests/pgprobe.py`). The sheet sits about 4 mm from
a third A4 page.

## Tests

The V44 harnesses live in `tests/`. They need Playwright + Chromium and poppler
(`pdfinfo`). Point them at this folder's `index.html` (that is now the default
`V34` / `PSB_BUILD` target). `test_11_v34_markdown` is deliberately not in
`run_all` — Markdown save was removed in V35.

Print geometry is in `03_sheetcss.js`, not `01_builder.css`. Do not re-add
`column-count` on the reference pane.

Full working notes: [HANDOVER.md](HANDOVER.md).
