import subprocess, sys
def widths(pdf):
    out = subprocess.run(['pdfimages','-list',pdf],capture_output=True,text=True).stdout
    ws=set()
    for l in out.splitlines()[2:]:
        p=l.split()
        if len(p)>4:
            try: ws.add(int(p[3]))
            except: pass
    return sorted(ws)
if __name__=='__main__':
    for p in sys.argv[1:]: print(p, widths(p))
