import asyncio, json, sys
import exportprobe as EP

async def main():
    path = sys.argv[1]; loads = sys.argv[2].split(','); theme = sys.argv[3] if len(sys.argv)>3 else 'classic'
    for ld in loads:
        try:
            r = await EP.run(path, ld, theme)
        except Exception as e:
            print('%-12s EXCEPTION %s' % (ld, e)); continue
        r['pdfPages'] = EP.pdfpages(r['pdfPath'])
        a = r['autopsy']
        if 'error' in a: print('%-12s autopsy error: %s' % (ld, a['error'])); continue
        print('== %s / %s   %d ms' % (ld, theme, r['ms']))
        print('   banner: %s' % (r['banners'][-1] if r['banners'] else '(none)'))
        print('   errors: %s' % (r['errors'] or 'none'))
        print('   layout pages=%d (%.0f mm)  pdfPages=%s  pdfSize=%s B' %
              (a['pages'], a['pageMm'], r['pdfPages'], r['pdfSize']))
        print('   header=%s brand=%s  hdrContentOverflow=%+.1f px  logo aspect %.4f vs natural %.4f  %s'
              % (a['hdrInline'], a['brandInline'], a['hdrContentOverflowPx'],
                 a['img']['aspectRendered'], a['img']['aspectNatural'],
                 'DISTORTED' if abs(a['img']['aspectRendered']-a['img']['aspectNatural'])>0.02 else 'ok'))
        print('   spacers: %d tr %s / %d div %s' % (a['spacersTr'], a['spacerTrH'][:6], a['spacersDiv'], a['spacerDivH'][:6]))
        print('   STRADDLERS LEFT: %d' % len(a['straddlers']))
        for s in a['straddlers'][:6]:
            print('      p%d %s.%s h=%.0f cut %.0f px in: %r' % (s['page'], s['tag'], s['cls'], s['h'], s['cut'], s['txt']))
        print('   footer-strip clashes: %d' % a['footClashCount'])
        for s in a['footClashes'][:6]:
            if s['cls'] != 'pg-spacer':
                print('      p%d %s.%s overlap %.1f px: %r' % (s['page'], s['tag'], s['cls'], s['overlapPx'], s['txt']))
        print('   pane: top=%s h=%.0f bottomGap=%.0f contentBottom=%.0f overrun=%+.0f'
              % (a['asideTop'], a['asideH'], a['asideBottomGapPx'], a['paneContentBottom'], a['paneOverrunPx']))
        print('   pdf: %s' % r['pdfPath'])
asyncio.run(main())
