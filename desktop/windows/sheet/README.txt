Programme Sheet Builder — standalone on Windows

This folder IS the app. It contains no .exe and no PowerShell, only the
builder page (index.html), two .cmd files and a shortcut. Smart App Control
blocks unsigned programs and constrains PowerShell; it does not police plain
.cmd files, and Microsoft Edge is signed by Microsoft. So this runs where
ProgrammeSheet.exe is blocked.

On your PC
----------
1. If the zip came from the internet: right-click the zip → Properties →
   tick Unblock → Apply. Then extract it.
2. Open the ProgrammeSheet folder.
3. Double-click Install.cmd. (If Windows shows "Open File - Security Warning",
   choose Run. That is the download flag, not Smart App Control.)
4. From then on use the Desktop shortcut "Programme Sheet Builder". It is
   also in the Start menu.

START.cmd opens the builder once without installing.

What it does
------------
The shortcut opens index.html in a Microsoft Edge app window (no tabs, no
address bar) with its own Edge profile at
  %LOCALAPPDATA%\ProgrammeSheet\edge-profile
Your Club Setup and the sheet you are working on are saved there, for this
Windows user only. Save as .json, export HTML / PDF / JPG, and the meetings
folder all work as they do on the website. Works offline.

To share
--------
Send ProgrammeSheet-portable.zip, or copy the whole extracted folder onto a
USB stick. On the other PC: Unblock the zip if it was downloaded, extract,
Install.cmd.

Open-online.cmd opens the live website instead and needs internet.

Needs Microsoft Edge (or Google Chrome). Nothing else.
