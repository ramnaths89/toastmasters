"""V30 feature 3 - the in-page Save dialog and the one file base name."""

import asyncio
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import open_app, run_suite  # noqa: E402

DLG = "#saveDialog"
NAME = "#saveFileName"

# nasty inputs -> what tidyStem() must leave behind
TIDY = [
    ("meeting.json", "meeting"),
    ("meeting.nse.json", "meeting"),
    ("Sheet.HTML", "Sheet"),
    ("poster.PDF", "poster"),
    ("shot.jpeg", "shot"),
    ("shot.JPG", "shot"),
    ("shot.png", "shot"),
    (r"a\b/c:d*e?f\"g<h>i|j", "a-b-c-d-e-f-g-h-i-j"),
    ("  padded  ", "padded"),
    ("trailing...", "trailing"),
    ("trailing. . .", "trailing"),
    ("...leading", "leading"),
    ("con:file", "con-file"),
    ("   ", ""),
    ("...", ""),
    ("", ""),
    # Extension stripping is anchored to end-of-string but runs BEFORE the
    # trailing-space/dot trim, so a name copied with a trailing space keeps
    # its extension.
    ("meeting.json ", "meeting"),
    ("sheet.pdf ", "sheet"),
    ("sheet.pdf.", "sheet"),
    # Cases named by the fix for defects 2 + 3.
    ("////", ""),                       # all-illegal -> nothing left, must be refused
    ("-", ""),
    ("--.-", ""),
    ("a.json.pdf ", "a"),               # stacked extensions, trailing space
    (".nse.json", ""),                  # extension only
    ("NSE-ProgSheet-2026-08-13-1930.nse.json", "NSE-ProgSheet-2026-08-13-1930"),
    # A legitimate name with internal dashes must survive intact.
    ("NSE-ProgSheet-2026-08-13-1930", "NSE-ProgSheet-2026-08-13-1930"),
    ("Area-Y1-Humorous-Speech-Contest", "Area-Y1-Humorous-Speech-Contest"),
    ("2026-08-13", "2026-08-13"),
    ("a-b-c.html ", "a-b-c"),
    ("NSE-ProgSheet-2026-08-13-1930", "NSE-ProgSheet-2026-08-13-1930"),
    ("a/b", "a-b"),
    ("a//b", "a-b"),       # runs of illegal chars collapse to one dash
    ("Voices of a Nation", "Voices of a Nation"),
]


async def open_dialog(p):
    await p.evaluate("() => saveMeeting()")
    await p.wait_for_timeout(250)


async def is_open(p):
    return "open" in ((await p.locator(DLG).get_attribute("class")) or "")


async def main(ctx, s):
    app = await open_app(ctx)
    p = app.page
    # The real save path ends in showDirectoryPicker(), which cannot resolve in
    # headless. Stub it so confirmSaveDialog() completes instead of hanging;
    # everything under test (the name, the state, the downloads) happens first.
    await p.evaluate(
        "() => { window.showDirectoryPicker = () => Promise.reject("
        "Object.assign(new Error('no picker'), {name:'AbortError'})); }"
    )

    # ---------- 3.1 the button opens the dialog ----------
    s.check("3.1 dialog markup exists", await p.locator(DLG).count() == 1)
    s.check("3.2 dialog starts closed", not await is_open(p))
    await p.locator("#saveBtn").click()
    await p.wait_for_timeout(300)
    s.check("3.3 pressing Save opens #saveDialog", await is_open(p))
    s.check("3.4 the dialog is actually visible", await p.locator(".save-panel").is_visible())
    s.check("3.5 the filename field is focused", await p.evaluate(
        "() => document.activeElement && document.activeElement.id") == "saveFileName")

    # ---------- 3.6 prefilled with the suggested name ----------
    val = await p.locator(NAME).input_value()
    s.check(
        "3.6 #saveFileName prefilled as NSE-ProgSheet-YYYY-MM-DD-HHMM",
        bool(re.fullmatch(r"NSE-ProgSheet-\d{4}-\d{2}-\d{2}-\d{4}", val)),
        f"value={val!r}",
    )
    s.eq("3.7 the prefill equals fileBaseName()", val, await p.evaluate("() => fileBaseName()"))

    # ---------- 3.8 Escape closes without saving ----------
    await p.keyboard.press("Escape")
    await p.wait_for_timeout(250)
    s.check("3.8 Escape closes the dialog", not await is_open(p))
    s.eq("3.9 Escape does not save a file name",
         await p.evaluate("() => state.meeting.fileName"), "")
    s.eq("3.10 Escape restores body scrolling",
         await p.evaluate("() => document.body.style.overflow"), "")

    # ---------- 3.11 Cancel closes without saving ----------
    await open_dialog(p)
    await p.locator(NAME).fill("Should-Not-Stick")
    await p.locator("#saveDialog .save-foot .btn.ghost").click()
    await p.wait_for_timeout(250)
    s.check("3.11 Cancel closes the dialog", not await is_open(p))
    s.eq("3.12 Cancel does not save the typed name",
         await p.evaluate("() => state.meeting.fileName"), "")

    # ---------- 3.13 clicking the backdrop closes without saving ----------
    await open_dialog(p)
    await p.locator(NAME).fill("Backdrop-Test")
    await p.locator(DLG).click(position={"x": 5, "y": 5})
    await p.wait_for_timeout(250)
    s.check("3.13 clicking the overlay closes the dialog", not await is_open(p))
    s.eq("3.14 the backdrop click does not save the name",
         await p.evaluate("() => state.meeting.fileName"), "")

    # ---------- 3.15 empty name is refused ----------
    await open_dialog(p)
    await p.locator(NAME).fill("")
    await p.locator("#saveDialog .save-foot .btn:not(.ghost)").click()
    await p.wait_for_timeout(300)
    s.check("3.15 an empty name keeps the dialog open", await is_open(p))
    s.eq("3.16 an empty name is not saved to state",
         await p.evaluate("() => state.meeting.fileName"), "")
    banner = await p.evaluate(
        "() => { const b=document.getElementById('banner')||document.querySelector('.banner');"
        " return b ? b.textContent : ''; }")
    s.check("3.17 an empty name shows a 'give the file a name' banner",
            "name" in banner.lower(), f"banner={banner!r}")

    # A name that is nothing but illegal characters. tidyStem() maps the run of
    # slashes to a dash BEFORE trimming, and the trim only strips whitespace and
    # dots, so this survives as the junk stem "-" and is saved silently.
    await p.locator(NAME).fill("////")
    await p.locator("#saveDialog .save-foot .btn:not(.ghost)").click()
    await p.wait_for_timeout(300)
    stem_illegal = await p.evaluate("() => state.meeting.fileName")
    still_open = await is_open(p)
    s.check("3.18 a name of only illegal characters ('////') is refused, not saved as junk",
            stem_illegal == "" and still_open,
            f"dialog stayed open={still_open}, state.meeting.fileName={stem_illegal!r}")
    s.check("3.19 no empty or junk stem reaches the writer",
            bool(await p.evaluate("() => fileBaseName()"))
            and await p.evaluate("() => fileBaseName()") != "-",
            f"fileBaseName()={await p.evaluate('() => fileBaseName()')!r}")
    # the same for a dash-only name
    await p.locator(NAME).fill("--.-")
    await p.locator("#saveDialog .save-foot .btn:not(.ghost)").click()
    await p.wait_for_timeout(300)
    s.check("3.19b a dash/dot-only name ('--.-') is refused too",
            await is_open(p) and await p.evaluate("() => state.meeting.fileName") == "",
            f"open={await is_open(p)} name={await p.evaluate('() => state.meeting.fileName')!r}")
    if not await is_open(p):
        await open_dialog(p)

    # ---------- 3.20 Enter in the field confirms ----------
    await p.locator(NAME).fill("Typed-By-Enter")
    await p.locator(NAME).press("Enter")
    await p.wait_for_timeout(400)
    s.check("3.20 Enter closes the dialog", not await is_open(p))
    s.eq("3.21 Enter saves the typed name to state.meeting.fileName",
         await p.evaluate("() => state.meeting.fileName"), "Typed-By-Enter")

    # ---------- 3.22 the Save button confirms and the name sticks ----------
    await open_dialog(p)
    s.eq("3.22 reopening prefills with the name already saved",
         await p.locator(NAME).input_value(), "Typed-By-Enter")
    await p.locator(NAME).fill("NSE Chapter Meeting 13 Aug")
    await p.locator("#saveDialog .save-foot .btn:not(.ghost)").click()
    await p.wait_for_timeout(400)
    s.check("3.23 the Save button closes the dialog", not await is_open(p))
    s.eq("3.24 the Save button writes state.meeting.fileName",
         await p.evaluate("() => state.meeting.fileName"), "NSE Chapter Meeting 13 Aug")
    s.eq("3.25 fileBaseName() returns the typed name",
         await p.evaluate("() => fileBaseName()"), "NSE Chapter Meeting 13 Aug")
    s.eq("3.26 sheetFileStem() returns the typed name",
         await p.evaluate("() => sheetFileStem()"), "NSE Chapter Meeting 13 Aug")

    # ---------- 3.27 a typed name is tidied on the way in ----------
    await open_dialog(p)
    await p.locator(NAME).fill(r'Bad:Name/With*Chars?.pdf ')
    await p.locator(NAME).press("Enter")
    await p.wait_for_timeout(400)
    s.eq("3.27 a nasty typed name is tidied before it is stored",
         await p.evaluate("() => state.meeting.fileName"), "Bad-Name-With-Chars")

    # ---------- 3.28 tidyStem() unit table ----------
    bad = []
    for raw, want in TIDY:
        got = await p.evaluate("t => tidyStem(t)", raw)
        if got != want:
            bad.append((raw, got, want))
    s.check(f"3.28 tidyStem() handles all {len(TIDY)} nasty inputs", not bad, f"{bad[:6]}")

    # tidyStem must be idempotent - the dialog re-tidies a stored name every open.
    nonidem = []
    for raw, _ in TIDY:
        once = await p.evaluate("t => tidyStem(t)", raw)
        twice = await p.evaluate("t => tidyStem(tidyStem(t))", raw)
        if once != twice:
            nonidem.append((raw, once, twice))
    s.check("3.29 tidyStem() is idempotent", not nonidem, f"{nonidem[:4]}")

    # blank fileName falls back to the suggestion, never to an empty stem
    fb = await p.evaluate("() => { state.meeting.fileName=''; return fileBaseName(); }")
    s.check("3.30 a blank fileName falls back to the suggested stem",
            bool(re.fullmatch(r"NSE-ProgSheet-\d{4}-\d{2}-\d{2}-\d{4}", fb)), f"{fb!r}")
    fb2 = await p.evaluate("() => { state.meeting.fileName='   '; return fileBaseName(); }")
    s.check("3.31 a whitespace-only fileName also falls back", fb2 == fb, f"{fb2!r}")
    fb3 = await p.evaluate("() => { state.meeting.fileName='///'; return fileBaseName(); }")
    s.check("3.32 an all-illegal stored fileName also falls back", fb3 == fb, f"{fb3!r}")

    # ---------- 3.33 the name survives the .json round trip ----------
    await p.evaluate("() => { state.meeting.fileName = 'Round-Trip-Name'; }")
    payload = await p.evaluate("() => meetingPayload()")
    await p.evaluate("t => { adoptState(JSON.parse(t)); }", payload)
    s.eq("3.33 the saved file name survives save-and-reload",
         await p.evaluate("() => state.meeting.fileName"), "Round-Trip-Name")

    # ---------- 3.34+ every download uses that base name ----------
    BASE = "NSE-Custom-Base-Name"
    await p.evaluate("() => { state.meeting.fileName = ''; }")
    await open_dialog(p)
    await p.locator(NAME).fill(BASE)
    await p.locator(NAME).press("Enter")
    await p.wait_for_timeout(500)
    s.eq("3.34 the base name is in state before the downloads",
         await p.evaluate("() => state.meeting.fileName"), BASE)

    got = {}
    # PNG was removed in V31; the three surviving exports must share the stem.
    for kind, ext in (("html", ".html"), ("pdf", ".pdf"), ("jpg", ".jpg")):
        try:
            async with p.expect_download(timeout=120000) as dl:
                await p.evaluate("k => pickDownload(k)", kind)
            d = await dl.value
            got[kind] = d.suggested_filename
            await d.cancel()
        except Exception as e:
            got[kind] = f"<no download: {type(e).__name__}>"
        s.eq(f"3.3{5 + ['html', 'pdf', 'jpg'].index(kind)} "
             f"{kind.upper()} download is named {BASE}{ext}",
             got[kind], BASE + ext)
    s.check("3.39 all three downloads share one base name",
            len({v.rsplit(".", 1)[0].replace(".nse", "") for v in got.values()
                 if not v.startswith("<")}) == 1, str(got))

    # The .json save uses the same stem too.
    await p.evaluate("() => { window.__jsonName = null; }")
    try:
        async with p.expect_download(timeout=20000) as dl:
            await p.evaluate("() => downloadMeetingJSON()")
        d = await dl.value
        jname = d.suggested_filename
        await d.cancel()
    except Exception as e:
        jname = f"<none: {type(e).__name__}>"
    s.eq("3.40 the .json save uses the same base name", jname, BASE + ".nse.json")

    # ---------- 3.41 no errors ----------
    s.check("3.41 zero uncaught page errors during feature 3", not app.clean_errors(),
            str(app.clean_errors()[:3]))
    s.check("3.42 zero console errors during feature 3", not app.clean_console(),
            str(app.clean_console()[:3]))


if __name__ == "__main__":
    asyncio.run(run_suite(main, "3_save_dialog"))
