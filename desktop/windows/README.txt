Toastmasters Tools — Windows (Smart App Control)

The .exe is unsigned. Windows 11 Smart App Control blocks it with a pink
Okay button and no Run anyway. This folder is the workaround: it is not an
app binary. It is a script that opens Edge around the same HTML.

Do this:

1. If you downloaded a zip from the internet, right-click the zip → Properties
   → tick Unblock → Apply. Then extract.
2. Double-click ToastmastersTools.cmd
3. Close the Edge window to quit

Needs Microsoft Edge (or Chrome). Does not need Python. Works offline.

Club Setup, starred clubs, the timer log and the Ah-Counter log save in this
Windows user account (Edge profile under AppData). They stay after you quit.

Open-online.cmd is a one-line fallback: it opens the live website in Edge.
That needs internet.

The unsigned ToastmastersTools.exe is still in desktop/dist for PCs that only
show SmartScreen (More info → Run anyway).
