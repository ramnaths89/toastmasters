"""Build the copy that may go to GitHub, from src/, with the officers' real names
replaced by placeholders.

Why this is a script and not a careful edit: V30 onward were never published
precisely because "swap the names out before uploading" was a note in a handover
rather than something the build could do, and a note does not survive a session.
This one is deterministic, it matches the transform already visible in the
published V31 (`<President Name>`, `<Their Club>`), and it REFUSES to write a file
that still contains a real name.

    python3 publish.py out/index.html

Club identity - the club name, number, district line, cadence, venue, the two
club links, the voting codes - is deliberately left alone. That is what the
published V31 does, `customise-for-your-club.md` is written around it, and a
person's name is a different kind of fact from a club's address.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'src')

# The only substitutions. Each is (exact text in src, replacement), and each one
# must fire - a name that has been edited since this list was written must stop
# the build, not pass through it silently.
SUBS = [
    ("'President|Johnson Soh',",                    "'President|<President Name>',"),
    ("'VP Education|Valerie J. Lim',",              "'VP Education|<VP Education Name>',"),
    ("'VP Membership|Roger Lek',",                  "'VP Membership|<VP Membership Name>',"),
    ("'VP Public Relations|Anjali Jai Anjana',",    "'VP Public Relations|<VP Public Relations Name>',"),
    ("'Secretary|Suhani, Rakshika',",               "'Secretary|<Secretary Name>',"),
    ("'Treasurer|Haziq Muhammad',",                 "'Treasurer|<Treasurer Name>',"),
    ("'Sergeant at Arms|Haziq Muhammad',",          "'Sergeant at Arms|<Sergeant at Arms Name>',"),
    ("'Immediate Past President|Kaydance Ng',",     "'Immediate Past President|<Immediate Past President Name>',"),
    ("'Division Director|Ibrahim Bin Mohd Ismail|Cheng San TMC',",
     "'Division Director|<Division Director Name>|<Their Club>',"),
    ("'Area Director|Edward Lay|Chua Chu Kang TMC',",
     "'Area Director|<Area Director Name>|<Their Club>',"),
]

# The gate. Given names and surnames SEPARATELY, so an edit that reorders or
# reformats a line still trips it - the SUBS list above only catches the exact
# lines it knows about, and this is the part that has to survive them going stale.
#
# Word-boundaried, and case-sensitive: the first version of this was a loose
# case-insensitive alternation and 'Lim' matched 'limit', 'delimiter' and 'sLIM',
# giving 44 hits in a clean file. A gate that cries wolf gets switched off, which
# is worse than no gate. Verified against the source: each of these matches
# exactly the officer lines and nothing else.
FORBIDDEN = re.compile(
    r'\b(?:Johnson|Soh|Valerie|Lim|Roger|Lek|Anjali|Anjana|Suhani|Rakshika|Haziq'
    r'|Muhammad|Kaydance|Ibrahim|Mohd Ismail|Edward Lay|Cheng San|Chua Chu Kang)\b')


def main():
    dest = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'publish', 'index.html')
    tmp = tempfile.mkdtemp(prefix='pspub-')
    try:
        stage = os.path.join(tmp, 'src')
        shutil.copytree(SRC, stage)
        app = os.path.join(stage, '05_app.js')
        text = open(app, encoding='utf-8').read()
        # GitHub src ships placeholders. A local OneDrive copy may still carry
        # real names; SUBS then fire. Either path must produce a clean file.
        already = "'President|<President Name>'," in text
        if already:
            print('src already uses placeholders — skip name substitution')
        else:
            for old, new in SUBS:
                if old not in text:
                    sys.exit('PUBLISH FAIL: expected line not found in 05_app.js, so the officer list '
                             'has changed since publish.py was written:\n  %s' % old)
                text = text.replace(old, new)
            open(app, 'w', encoding='utf-8').write(text)

        # Build with the real build.py, so the publish copy cannot drift from the
        # shipping one in any way except the names.
        os.makedirs(os.path.dirname(os.path.abspath(dest)) or '.', exist_ok=True)
        r = subprocess.run([sys.executable, os.path.join(HERE, 'build.py'), os.path.abspath(dest)],
                           cwd=tmp, capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit('PUBLISH FAIL: build refused:\n' + r.stdout + r.stderr)

        out = open(dest, encoding='utf-8').read()
        hits = [m.group(0) for m in FORBIDDEN.finditer(out)]
        if hits:
            os.unlink(dest)
            sys.exit('PUBLISH FAIL: %d real-name hits still in the output, file deleted: %s'
                     % (len(hits), sorted(set(hits))))
        print('wrote', dest, len(out), '- 0 real-name hits')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    main()
