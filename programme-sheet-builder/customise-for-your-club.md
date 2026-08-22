# Use the Programme Sheet Builder for your own club

The builder ships with **Nee Soon East Toastmasters Club** filled in as its factory defaults —
club name, number, district line, venue, links. The officer *names* are deliberately placeholders
like `<President Name>`, so nobody's name is published in the tool; everything else is a real
working example, so you can see the shape of what goes where. None of it is locked. There are two
ways to make it yours, and most clubs only ever need the first.

**The tool:** https://ramnaths89.github.io/toastmasters/programme-sheet-builder/

---

## Route 1 — fill in Club Setup (about five minutes, no code)

Open the tool. **Club Setup** is the first panel in the form on the left. Open it and replace these:

| Field | What it is | Currently |
|---|---|---|
| Club Name | Printed large at the top of the sheet | Nee Soon East Toastmasters Club |
| Club Number | Your TI club number | 00002548 |
| Club initials | Used to name saved meeting files | NSE |
| District line | Prints under the club name | District: 80 \| Division: Y \| Area Y1 \| Club Number: 2548 |
| Meeting cadence | One line at the foot of the banner | We meet every 2nd and 4th Thursday of the month from 7:00PM to 9:30PM |
| Location | Venue, address, postal code | Nee Soon East Community Club, 1 Yishun Ave 9, #04-01 (Culinary Studio), Singapore 768893 |
| Footer note | Short district summary for the page footer | District 80, Division Y, Area 01 |
| Executive Committee | One line per role, `Role\|Name\|Sub-note` — the sub-note is optional | Placeholders — `President\|<President Name>` and so on |
| District Officers | One line per person, `Role\|Name\|Their Club` | Placeholders — `<Division Director Name>`, `<Their Club>` |
| Links | One line per link, `Label\|URL\|Display text` | TI plus Nee Soon East's Facebook group |
| Voting link | Where members vote. Prints under every voting row on the sheet | `https://slido.com` |
| Speeches code | Room code for the prepared-speech vote | `NSE_1` |
| Table topics | Room code for the Table Topics vote | `NSE_2` |
| Evaluations | Room code for the evaluation vote | `NSE_3` |

> **Change the three voting codes or delete them.** They are the one field that carries somebody
> else's club into your meeting silently. Left alone, your printed sheet tells your members to
> vote in Nee Soon East's Slido rooms, and nothing on the page looks wrong. They are also the one
> field the usual check misses: searching the file for "Nee Soon" will not find `NSE_1`. If your
> club doesn't run live voting at all, clear the link and all three codes and the voting lines
> stop printing.

Start and end time live in **Meeting Info**, not Club Setup, because they occasionally change. The
defaults are 19:00 and 21:30, and the standard timings are tuned so a meeting lands exactly on the
end time.

The browser tab still reads **NSE Programme Sheet Builder**. That is cosmetic and nothing on the
printed sheet depends on it, but Route 2 below changes it if it bothers you.

Your entries are saved in your own browser as you type, so the tool opens with your club's details
next time. Two things worth knowing before you rely on that:

- **It is per browser and per device.** Set it up on the laptop you actually build agendas on. A
  different machine, a different browser, or a cleared cache starts from the factory defaults
  again.
- **↺ Reset restores the factory defaults, not yours.** Reset clears saved state and falls back to
  Nee Soon East's club details and the officer placeholders. If you want Reset to land on *your*
  club, use Route 2. If you just want a ready-made file to hand to whoever takes over as VPE, you
  no longer need Route 2 — see **Saving meetings as files**, below.

### Two things you do not need code for

- **Language Evaluator.** Off by default, because Nee Soon East doesn't run one every meeting.
  Tick the role and the Word of the Day row appears with it. (This is per meeting — see Route 2 to
  make it your permanent default.)
- **Number of prepared speeches.** The template has four speech slots with four paired evaluations.
  Use the **− / +** stepper in the Speeches section header to add or remove a slot — the paired
  evaluation always moves with its speech. After changing the count, re-apply your standard
  timings so the meeting still lands on the end time.

---

## Saving meetings as files

**💾 Save** writes the meeting as a plain `.json` file. The first time, your browser asks you to
pick a folder to keep meetings in — choose one and it is remembered. From then on, every change
autosaves straight into that file, so there is nothing to remember to click.

- The **Saved meetings** dropdown beside 💾 reopens anything in that folder. **＋ Save as a new
  file** keeps the current meeting and starts another — handy for copying last month's agenda into
  this month's.
- Files are named `<Club initials>-ProgSheet-<meeting date>-<time saved>.nse.json`, for example
  `NSE-ProgSheet-2026-08-13-1930.nse.json`. The time is what stops two saves of the same meeting
  from overwriting each other. Set **Club initials** in Club Setup; if you leave it blank the tool
  uses the capitals of your club name.
- After a browser restart you may be asked to reconnect the folder once. That is normal — a web
  page can only re-request folder permission when you click something, which is what the dropdown's
  **Connect the meetings folder** entry is for.
- **Chrome and Edge** support this properly. **Safari and Firefox** do not have the underlying
  browser feature, so there Save becomes an ordinary download and opening a meeting an ordinary
  file picker. The JSON is identical either way, so files move between browsers and between people
  without conversion.

This is the easy way to hand a finished agenda to a colleague: save it, send them the `.json`, and
they open it with the dropdown.

---

## Getting a PDF or an image

Use **⭳ Download**:

- **PDF** — a print-ready A4 file under 500 KB, saved straight away with no print dialog.
- **JPG** — an image of the whole sheet, under 500 KB, for WhatsApp, email and posting.
- **HTML** — the sheet as a standalone page that reopens and stays editable in any browser.

There is deliberately no print button. The browser's own print dialog has a **destination**
setting, and on Windows the "Microsoft Print to PDF" destination photographs every page at 300dpi —
producing a blurry file around 1.4 MB instead of a sharp one. A web page cannot choose that setting
for you, or even see which one is selected, so the tool builds the PDF itself instead.

To print on paper, download the PDF and print that, or press **Ctrl + P** on the downloaded HTML.
If you do use the browser dialog, set the destination to **"Save as PDF"** and untick
**"Headers and footers"**, or the browser stamps its own title and URL across your sheet.

---

## Route 2 — make your club the built-in default

Do this if you want your club's details to survive a ↺ Reset. (If you only want to share one
finished agenda, save it as a `.json` and send that instead — see above.)

You will need the HTML file itself. Download it from the tool's page (or save the page as
`ProgSheetGen.html`), then give it to an AI assistant — Claude, ChatGPT, Copilot, whichever you
use — together with the prompt below. Paste the prompt, attach the file, and answer its questions.

````
Attached is `ProgSheetGen.html`, a single-file Toastmasters meeting-programme-sheet
generator. It is currently hardcoded with Nee Soon East Toastmasters Club's details as its
factory defaults, and with placeholder officer names. Replace those defaults with my club's,
then hand back the finished file.

Do this as a short interactive interview — ask the questions below, wait for my answers, then
edit the file. If I paste all my details in one go, skip straight to editing.

WHAT TO ASK ME

Show me the current default in brackets so I know what it is replacing. Do not copy any
default into my file.

1. Club name (default: Nee Soon East Toastmasters Club)
2. Club number (default: 00002548)
3. Club initials, used to name saved meeting files (default: NSE)
4. District line, printed under the club name, format
   `District: X | Division: Y | Area Z | Club Number: NNNN`
   (default: District: 80 | Division: Y | Area Y1 | Club Number: 2548)
5. Meeting cadence, one line at the foot of the banner
   (default: We meet every 2nd and 4th Thursday of the month from 7:00PM to 9:30PM)
6. Meeting start and end time, 24-hour, used to auto-time the agenda
   (defaults: 19:00 and 21:30)
7. Venue, full address including postal code
   (default: Nee Soon East Community Club, 1 Yishun Ave 9, #04-01 (Culinary Studio),
   Singapore 768893)
8. Footer note, a short district summary (default: District 80, Division Y, Area 01)
9. Executive Committee, one line per role, format `Role|Name`. Ask me to list the roles I
   actually have. The file currently holds placeholders like `President|<President Name>` —
   every one of them must be replaced. Format example only, do not copy:
   President|Jane Tan
   VP Education|Sam Lee
10. District Officers, one line per person, format `Role|Name|Their Club`. These are
    placeholders too. Format example only, do not copy:
    Division Director|Name|Their Club
    Area Director|Name|Their Club
11. Club links, one line per link, format `Label|URL|Display text`. Keep the Toastmasters
    International line as-is and add my club's own. Format example only, do not copy:
    Toastmasters Intl.|https://www.toastmasters.org|www.toastmasters.org
    Our Club|https://www.facebook.com/groups/example|facebook.com/groups/example
12. Live voting. The sheet prints a voting link and a room code under each of the three votes
    (prepared speeches, table topics, evaluations). These currently hold ANOTHER CLUB's
    account — link https://slido.com with codes NSE_1, NSE_2 and NSE_3 — so they must be
    replaced or removed; they are the one setting that goes wrong silently. Ask me for my
    club's voting link and my three room codes. If I say we do not run live voting, set the
    link and all three codes to empty strings, which stops the voting lines printing.

Then ask this, and skip it if I do not answer:

13. Does my club run a Language Evaluator every meeting? If yes, set that role to default ON.
    It is currently OFF. Note that turning it on adds a Word of the Day row, which adds about
    three minutes — I may want to re-tune the flexible segments (Break and Table Topics) so the
    meeting still lands on my end time.

Do NOT ask me how many prepared speeches we run. The tool has a − / + stepper in the Speeches
header and a ✕ to remove one, so the slot count is changed in the interface, not in code.

HOW TO EDIT THE FILE

1. Find the JavaScript function `defaultState()`. It returns an object whose keys are
   meeting, roles, roleActive, customRoles, execText, districtText, linksText,
   announcementsText, paneWidth, theme and segments. Read it before you edit it — do not
   assume the shape from this prompt.
2. Inside the nested `meeting` object, replace ONLY the string values for: clubName,
   clubNumber, clubInitials, orgLine, cadence, location, startTime, endTime, footerNote, and
   the voting link and three codes (in `meeting.voting`, or wherever the file holds
   votingLink / voteSpeech / voteTT / voteEval — find them, they exist).
3. At the top level of the same object, replace the string values for execText, districtText
   and linksText.
4. Only if I answered the Language Evaluator question with yes, change `langeval: false` to
   `langeval: true` in the `roleActive` object.
5. Leave `roles`, `customRoles`, `announcementsText`, `paneWidth`, `theme` and `segments`
   alone. Those are per-meeting data, layout preferences and the timing template.
6. Change the `<title>` in the document head from "NSE Programme Sheet Builder" to my club's
   equivalent. Leave the localStorage key alone — renaming it discards anything already saved.
7. Do not touch anything else — no CSS, no other JavaScript, no reformatting or re-indenting
   of code you did not change. Keep the same quote style and structure.
8. Everything else (the Pathways catalogue, timing logic, print layout, themes, help panel) is
   shared Toastmasters International content and mechanics. It is not club-specific.

WHAT TO HAND BACK

1. The complete modified HTML file — the whole file, not a diff or a snippet — ready to save
   and open in a browser.
2. A short summary of exactly which fields you changed, so I can check it before I trust it.
3. A reminder to open the file, click ↺ Reset, and confirm Club Setup shows my club — then
   search the file for "Nee Soon", "2548", "Yishun", "NSE_", "slido" and "<" and confirm the
   only matches left are ones I put there myself.
````

### Check the result before you use it in front of a room

1. Open the file and click **↺ Reset**. Club Setup should show *your* club, not Nee Soon East's.
2. Search the file (Ctrl+F) for `Nee Soon`, `2548`, `Yishun` and `<President Name>`. All four
   should return nothing.
3. Search it again for `NSE_` and `slido`. This is a separate step because the first search
   cannot catch it: the voting codes carry no club name, so a file that passes step 2 perfectly
   can still send your members to somebody else's poll.
4. Build one real agenda and download the PDF. Confirm the banner, the footer and the side panel
   all read correctly, that the voting rows show your codes, and that the meeting still ends at
   your end time.

---

## A note on what is and isn't yours to change

Your club's name, number, initials, district line, venue, officers and links are yours. The
Pathways catalogue, project timings, the timing-light logic and the print layout are shared
Toastmasters International content and tool mechanics — leave them alone, and everyone's sheets
stay consistent with each other and with the official programme.

This tool is a personal project by an individual member. It is not an official Toastmasters
International or District 80 publication and is not endorsed by either. Check anything that
matters — a project duration, a timing — before you rely on it in front of a room.
