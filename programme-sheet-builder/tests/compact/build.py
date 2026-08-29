import sys,os
P='/home/claude/psb/tests/compact/src/'
def r(n): return open(P+n,encoding='utf-8').read()
css_sheet = r('03_sheetcss.js')
# trap 1: backticks / ${ inside the SHEET_CSS literal region
lit_start = css_sheet.find('`')
lit_end   = css_sheet.rfind('`')
body = css_sheet[lit_start+1:lit_end]
for i,line in enumerate(body.split('\n'),1):
    if '`' in line: sys.exit('BUILD FAIL: backtick in sheet css line %d: %s'%(i,line))
    if '${' in line and 'esc(' not in line and '${' not in '': pass
h2c = r('04_h2c.js')
for n,t in [('h2c',h2c),('app',r('05_app.js')),('app2',r('06_app2.js'))]:
    if '</script' in t.lower(): sys.exit('BUILD FAIL: literal </script> in '+n)
SEP='</script>\n<script>'
out = (r('00_head_open.html') + '<style>' + r('01_builder.css') + r('02_body.html')
       + css_sheet + SEP + h2c + SEP
       + r('05_app.js') + SEP + r('06_app2.js') + r('07_tail.html'))
dest = sys.argv[1] if len(sys.argv)>1 else 'ProgSheetGenV30.html'
open(dest,'w',encoding='utf-8').write(out)
print('wrote',dest,len(out))
