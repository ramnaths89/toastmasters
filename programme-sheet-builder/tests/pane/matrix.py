import asyncio, sys, glob, os
import exportprobe as EP
from pdfcheck import check
from imgw import widths

async def main():
    path=sys.argv[1]; load=sys.argv[2]; themes=sys.argv[3].split(',')
    for th in themes:
        r = await EP.run(path, load, th)
        a = r['autopsy']; r['pdfPages']=EP.pdfpages(r['pdfPath'])
        clash = [c for c in a['footClashes'] if c['cls']!='pg-spacer']
        print('%-12s %-12s pages=%s size=%7d B (%5.1f KiB) %s  logo=%.4f%s  straddlers=%d  footClash=%d%s'
              % (load, th, r['pdfPages'], r['pdfSize'] or -1, (r['pdfSize'] or 0)/1024,
                 'OVER' if (r['pdfSize'] or 0)>500*1024 else 'ok  ',
                 a['img']['aspectRendered'],
                 ' DISTORTED' if abs(a['img']['aspectRendered']-a['img']['aspectNatural'])>0.02 else '',
                 len(a['straddlers']), a['footClashCount'],
                 ('  worst %.1fpx: %r' % (max(c['overlapPx'] for c in clash), clash[0]['txt'][:34])) if clash else ''))
        if r['pdfPath']:
            pages, rows, _ = check(r['pdfPath'], 72, verbose=False)
            rr = [x[3] for x in rows]
            print('             pane rule rows/page: %s   embedded image width: %s px'
                  % (' '.join('%.0f%%'%v for v in rr), widths(r['pdfPath'])))
asyncio.run(main())
