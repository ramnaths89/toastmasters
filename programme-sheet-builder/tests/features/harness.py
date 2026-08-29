"""Shared harness for the V30 feature tests.

Every test file imports `Suite` and `open_app`. Results are collected as
(check_id, ok, detail) triples and printed as a table by run_all.py.

Design notes:
  * file:// only - the app is a single self-contained HTML file.
  * Google Fonts is unreachable here, so requests to fonts.googleapis.com /
    fonts.gstatic.com are aborted up front. Those aborts are then EXCLUDED from
    the console/page-error tally (the task says blocked fonts are expected).
  * localStorage is shared across every file:// page in a profile, so each test
    clears it before the app boots, otherwise one test's meeting leaks into the
    next one's "blank template".
"""

import asyncio
import json
import os
import re
import sys
import traceback

from playwright.async_api import async_playwright

# Build under test, and the earlier builds used as regression baselines.
# V34 is the harness's historical TARGET name — it means "the build under test".
_HERE = os.path.dirname(os.path.abspath(__file__))
_INDEX = os.path.abspath(os.path.join(_HERE, '..', '..', 'index.html'))
V34 = os.path.abspath(os.environ.get("V34", _INDEX if os.path.isfile(_INDEX) else "/home/claude/psb/ProgSheetGenV34.html"))
V33 = os.path.abspath(os.environ.get("V33", "/home/claude/psb/ProgSheetGenV33.html"))
V32 = os.path.abspath(os.environ.get("V32", "/home/claude/psb/ProgSheetGenV32.html"))
V31 = os.path.abspath(os.environ.get("V31", "/home/claude/psb/ProgSheetGenV31.html"))
V30 = os.path.abspath(os.environ.get("V30", "/home/claude/psb/ProgSheetGenV30.html"))
V29 = os.path.abspath(os.environ.get("V29", "/tmp/V29.html"))
TARGET = V34          # what every suite exercises unless it says otherwise
PREV = V33            # the previous shipped build, for screen-render regressions

FONT_HOSTS = ("fonts.googleapis.com", "fonts.gstatic.com")

# Console noise that is a blocked-network artefact, not an app defect.
NOISE = re.compile(
    r"fonts\.(googleapis|gstatic)\.com"
    r"|net::ERR_(FAILED|BLOCKED|NAME_NOT_RESOLVED|INTERNET_DISCONNECTED|CONNECTION)"
    r"|Failed to load resource"
    r"|ERR_ABORTED",
    re.I,
)


class Suite:
    def __init__(self, name):
        self.name = name
        self.results = []

    def check(self, cid, ok, detail=""):
        self.results.append((cid, bool(ok), detail))
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {cid}" + (f" :: {detail}" if detail and not ok else ""))
        return bool(ok)

    def eq(self, cid, got, want, extra=""):
        ok = got == want
        d = "" if ok else f"got {got!r}, want {want!r}"
        if extra:
            d = (d + " | " + extra) if d else extra
        return self.check(cid, ok, d)

    def error(self, cid, exc):
        return self.check(cid, False, f"EXCEPTION {type(exc).__name__}: {exc}")

    def dump(self, path):
        with open(path, "w") as f:
            json.dump({"suite": self.name, "results": self.results}, f, indent=1)


class App:
    """A booted copy of the app plus its error log."""

    def __init__(self, page, errors, console):
        self.page = page
        self.errors = errors        # uncaught page errors
        self.console = console      # console.error / warning entries (filtered)

    def clean_errors(self):
        return [e for e in self.errors if not NOISE.search(e)]

    def clean_console(self):
        return [c for c in self.console if not NOISE.search(c)]


async def open_app(ctx, path=TARGET, viewport=None, boot_wait=900):
    page = await ctx.new_page()
    if viewport:
        await page.set_viewport_size(viewport)
    errors, console = [], []
    page.on("pageerror", lambda e: errors.append(str(e)))

    def _con(msg):
        if msg.type in ("error", "warning"):
            console.append(f"{msg.type}: {msg.text}")

    page.on("console", _con)

    async def _route(route):
        if any(h in route.request.url for h in FONT_HOSTS):
            await route.abort()
        else:
            await route.continue_()

    await page.route("**/*", _route)
    # Fresh localStorage: file:// shares one origin across every build.
    await page.add_init_script(
        "try{localStorage.clear();}catch(e){}"
    )
    await page.goto("file://" + path)
    await page.wait_for_function("() => typeof state !== 'undefined'", timeout=15000)
    await page.wait_for_timeout(boot_wait)
    return App(page, errors, console)


# ---- V31 helpers -------------------------------------------------------------
# Every <details class="section"> now loads shut, and every speech card loads
# collapsed. Interaction tests have to open what they are about to click; the
# "it loads shut" assertions live in suite 8.
OPEN_SECTIONS = "() => { document.querySelectorAll('details.section').forEach(d => d.open = true); }"


async def open_sections(page):
    await page.evaluate(OPEN_SECTIONS)
    await page.wait_for_timeout(120)


async def expand_speech(page, seg_id):
    """Open one speech card by id and wait for the re-render."""
    await page.evaluate("id => { if(!expandedSpeeches.has(id)) toggleSpeech(id); }", seg_id)
    await page.wait_for_timeout(200)


# A "normally-filled" meeting: 4 speeches with speakers/titles/projects, every
# role named, a title, a date and two announcements. Used by the export tests
# so the 500 KB assertions are made against a realistic sheet, not a blank one.
FILL_JS = r"""
() => {
  const m = state.meeting;
  m.title = 'Chapter Meeting: Voices of a Nation';
  m.dateDisplay = 'Thursday, 13 August 2026';
  Object.keys(state.roles).forEach((k, i) => { state.roles[k] = 'Member Name ' + (i + 1); });
  state.announcementsText = 'Club anniversary dinner, 20 Sept\nArea contest briefing after the meeting';
  const sp = state.segments.filter(s => s.isSpeech);
  const projs = ['Ice Breaker', 'Evaluation and Feedback', 'Researching and Presenting', 'Understanding Your Leadership Style'];
  sp.forEach((s, i) => {
    s.speakerName = 'Speaker Name ' + (i + 1);
    s.speechTitle = 'A Speech Title That Runs Reasonably Long';
    s.pathway = 'DL'; s.pLevel = '1';
    applyProjectChoice(s, projs[i % projs.length]);
  });
  state.segments.filter(s => s.isEvaluation).forEach((s, i) => {
    s.holderOverride = 'Evaluator Name ' + (i + 1);
    s.speakerName = 'Speaker Name ' + (i + 1);
  });
  renderFormPane(); renderPreviewNow();
}
"""


async def run_suite(coro, name):
    """Boilerplate: launch chromium, run coro(pw_ctx, suite), print + dump."""
    suite = Suite(name)
    print(f"\n=== {name} ===")
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={"width": 1400, "height": 900})
        try:
            await coro(ctx, suite)
        except Exception as e:  # a crash must not lose the checks already made
            traceback.print_exc()
            suite.error(f"{name}:harness", e)
        finally:
            await ctx.close()
            await browser.close()
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"_res_{name}.json")
    suite.dump(out)
    bad = sum(1 for _, ok, _ in suite.results if not ok)
    print(f"--- {name}: {len(suite.results) - bad}/{len(suite.results)} passed")
    return suite
