"""Rasterise an exported PDF: per-page ink, footer band, pane column rule continuity.

Geometry is taken from the real A4 page with the sheet's own 10mm margins:
content box starts at 10mm and is 190mm wide; the pane is the first 45.6mm of it.
"""
import subprocess, sys, os, glob, tempfile
from PIL import Image
import numpy as np

def check(pdf, dpi=72, verbose=True):
    info = subprocess.run(['pdfinfo', pdf], capture_output=True, text=True).stdout
    pages = int([l for l in info.splitlines() if l.startswith('Pages:')][0].split(':')[1])
    td = tempfile.mkdtemp()
    subprocess.run(['pdftoppm','-r',str(dpi),'-png',pdf,os.path.join(td,'p')],capture_output=True)
    files = sorted(glob.glob(os.path.join(td,'p-*.png')))
    ppmm = dpi/25.4
    x_margin = 10*ppmm
    x_rule   = x_margin + 45.6*ppmm          # pane column rule sits here
    rows = []
    if verbose:
        print('%s  pages=%d  dpi=%d' % (os.path.basename(pdf), pages, dpi))
        print('   %-5s %7s %9s %9s %9s %9s' % ('page','ink%','paneInk%','ruleRows%','footInk%','footRule'))
    for i,f in enumerate(files):
        im = np.asarray(Image.open(f).convert('L')).astype(float)
        h,w = im.shape
        ink = (im<240).mean()*100
        x0,x1 = int(x_margin), int(x_rule)
        paneink = (im[:, x0:x1]<240).mean()*100
        band = im[:, max(0,int(x_rule)-2):int(x_rule)+3].min(axis=1)
        rulerows = (band<248).mean()*100
        fb = im[int(h - (10*ppmm) - 6.5*ppmm):int(h - 10*ppmm), int(x_margin):int(w-x_margin)]
        footink = (fb<240).mean()*100
        # the footer's own 1px top rule, spanning the full content width
        toprow = fb[0:2,:].min(axis=0)
        footrule = (toprow<238).mean()*100
        rows.append((i+1, ink, paneink, rulerows, footink, footrule))
        if verbose:
            print('   %-5d %6.2f %8.2f %8.1f%% %8.2f %8.1f%%' % (i+1, ink, paneink, rulerows, footink, footrule))
    return pages, rows, files

def seams(pdf, out, dpi=110, band_mm=22):
    pages, rows, files = check(pdf, dpi, verbose=False)
    ppmm = dpi/25.4; b = int(band_mm*ppmm)
    ims = [Image.open(f).convert('RGB') for f in files]
    tiles = []
    for i in range(len(ims)-1):
        a = ims[i].crop((0, ims[i].height-b, ims[i].width, ims[i].height))
        c = ims[i+1].crop((0, 0, ims[i+1].width, b))
        t = Image.new('RGB',(a.width, a.height+c.height+6),'#e00')
        t.paste(a,(0,0)); t.paste(c,(0,a.height+6)); tiles.append(t)
    if not tiles: return None
    W = max(t.width for t in tiles); H = max(t.height for t in tiles)
    sheet = Image.new('RGB',(W*len(tiles)+10*(len(tiles)-1), H),'#999')
    for i,t in enumerate(tiles): sheet.paste(t,(i*(W+10),0))
    sheet.save(out); return out

if __name__ == '__main__':
    if sys.argv[1] == '--seams':
        print(seams(sys.argv[2], sys.argv[3]))
    else:
        for p in sys.argv[1:]: check(p); print()
