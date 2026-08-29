"""Where exactly does the footer's top rule land on each page, and is it doubled?"""
import subprocess, glob, os, sys, tempfile
from PIL import Image
import numpy as np

def run(pdf, dpi=300):
    td=tempfile.mkdtemp(); ppmm=dpi/25.4
    subprocess.run(['pdftoppm','-r',str(dpi),'-png',pdf,os.path.join(td,'p')],capture_output=True)
    fs=sorted(glob.glob(os.path.join(td,'p-*.png')))
    print('%s (%d pages, %d dpi)' % (os.path.basename(pdf), len(fs), dpi))
    print('   %-5s %-34s %s' % ('page','full-width dark rules in bottom 25mm (mm from page top)','n'))
    for i,f in enumerate(fs):
        im=np.asarray(Image.open(f).convert('L')).astype(float)
        h,w=im.shape
        x0,x1=int(10*ppmm),int(w-10*ppmm)
        y0=int(h-25*ppmm)
        hits=[]
        for y in range(y0,h):
            row=im[y,x0:x1]
            if (row<200).mean()>0.92: hits.append(round(y/ppmm,2))
        # collapse runs
        grouped=[]
        for v in hits:
            if grouped and v-grouped[-1][-1]<0.3: grouped[-1].append(v)
            else: grouped.append([v])
        desc=', '.join('%.2f%s'%(g[0],'' if len(g)==1 else '-%.2f'%g[-1]) for g in grouped)
        print('   %-5d %-34s %d' % (i+1, desc or '(none)', len(grouped)))
for p in sys.argv[1:]: run(p); print()
