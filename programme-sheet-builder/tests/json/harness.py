"""Shared Playwright harness for the JSON save/load attack suite.

Usage:  from harness import App
        with App() as app: ...

Everything runs sequentially on one Chromium instance per test file.
"""
import json
import os
import pathlib
import sys

from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
FAKEFS = (HERE / "fakefs.js").read_text()

# The build under test. Was hardcoded to V35, which meant every suite in here
# silently kept testing V35 after V36 was built - the worst possible failure for
# a regression suite, because it goes green.
DEFAULT_BUILD = pathlib.Path(os.environ.get("PSB_BUILD") or (ROOT / "index.html"))


class App:
    def __init__(self, build=None, fs_supported=True, quiet=True, dialogs="accept"):
        self.build = pathlib.Path(build) if build else DEFAULT_BUILD
        self.fs_supported = fs_supported
        self.quiet = quiet
        self.console = []
        self.pageerrors = []
        self.banners = []
        self.dialogs = dialogs          # "accept" | "dismiss"
        self.dialog_log = []

    def _on_dialog(self, d):
        self.dialog_log.append((d.type, d.message))
        if self.dialogs == "dismiss":
            d.dismiss()
        else:
            d.accept("ok")

    def __enter__(self):
        self._pw = sync_playwright().start()
        self.browser = self._pw.chromium.launch(args=["--allow-file-access-from-files"])
        self.ctx = self.browser.new_context()
        self.page = self.ctx.new_page()
        self.page.route("http*://**", lambda r: r.abort())
        # The picker hands back whatever fake folder the test has built, so
        # linkFolder() (and everything it now calls) runs for real.
        # Picking a folder grants permission, as it does in a real browser.
        shim = FAKEFS + ("\n window.showDirectoryPicker = function(){ if(!window.__DIR)"
                         "   return Promise.reject(Object.assign(new Error('no folder picked'), {name:'AbortError'}));"
                         "   window.__DIR.__st.perm = 'granted'; return Promise.resolve(window.__DIR); };"
                         if self.fs_supported else
                         "\n try{ delete window.showDirectoryPicker; }catch(e){} window.showDirectoryPicker = undefined;")
        self.ctx.add_init_script(shim)      # context-wide, so extra tabs get it too
        self.page.on("console", lambda m: self.console.append(m.type + ": " + m.text))
        self.page.on("pageerror", lambda e: self.pageerrors.append(str(e)))
        self.page.on("dialog", self._on_dialog)
        self.page.set_default_timeout(90000)
        for attempt in range(3):
            try:
                self.page.goto(self.build.as_uri(), wait_until="domcontentloaded", timeout=90000)
                break
            except Exception as e:
                if attempt == 2:
                    raise
                print("  (goto retry after %s)" % type(e).__name__)
        self.page.wait_for_timeout(900)
        return self

    def __exit__(self, *a):
        try:
            self.ctx.close(); self.browser.close()
        finally:
            self._pw.stop()

    # ---- helpers -------------------------------------------------------
    def js(self, expr, arg=None):
        return self.page.evaluate(expr, arg)

    def wait(self, ms):
        self.page.wait_for_timeout(ms)

    def attach_folder(self, opts=None):
        """Create the fake folder, assign to the app's folderHandle global."""
        self.js("""(o)=>{ window.__DIR = window.__mkFakeDir(o||{}); folderHandle = window.__DIR; window.__FSLOG=[]; return true; }""", opts or {})

    def dir_list(self):
        return self.js("()=>window.__DIR.__list()")

    def dir_get(self, name):
        return self.js("(n)=>window.__DIR.__get(n)", name)

    def dir_set(self, name, text):
        return self.js("(a)=>window.__DIR.__set(a[0],a[1])", [name, text])

    def dir_ctl(self, patch):
        return self.js("(p)=>{ Object.assign(window.__DIR.__st, p); return window.__DIR.__st.perm; }", patch)

    def fslog(self):
        return self.js("()=>window.__FSLOG.map(e=>({ev:e.ev,file:e.file,bytes:e.bytes,marker:e.marker,t:Math.round(e.t)}))")

    def save_direct(self, name=None):
        return self.js("(n)=>saveMeetingDirect(n||undefined)", name)

    def set_title(self, t):
        """Change the meeting title the way the UI does, triggering the save chain."""
        return self.js("(t)=>{ state.meeting.title = t; saveState(); return state.meeting.title; }", t)

    def type_title(self, t):
        """Same but through the debounced queueSave (400ms) path."""
        return self.js("(t)=>{ state.meeting.title = t; queueSave(); }", t)

    def badge(self):
        return self.js("""()=>{ const el=document.getElementById('saveDot');
            return el ? {glyph:el.textContent, warn:el.classList.contains('warn'), title:el.title} : null; }""")

    def open_file_name(self):
        return self.js("()=>openFileName()")

    def state(self):
        return self.js("()=>JSON.parse(JSON.stringify(state))")

    # ---- reload / re-attach --------------------------------------------
    # A real FileSystemHandle is structured-cloneable; our fake is not, so the
    # app's own idbSet() silently fails for it.  Stub idbGet/idbSet (they are
    # plain function declarations, i.e. window properties) with an equivalent
    # that survives a reload through localStorage, then drive reattachFile()
    # exactly as DOMContentLoaded does.
    IDB_STUB = """()=>{
        window.idbSet = async (k,v)=>{
            localStorage.setItem('__fake_idb_'+k, v ? (v.name || '1') : '');
            return true; };
        window.idbGet = async (k)=>{
            const s = localStorage.getItem('__fake_idb_'+k);
            if(!s) return null;
            if(k === 'folder') return window.__DIR || null;
            return (window.__DIR && window.__DIR.__handleFor) ? window.__DIR.__handleFor(s) : null; };
        return true; }"""

    def install_idb_stub(self):
        return self.js(self.IDB_STUB)

    def reload_with_folder(self, files):
        """Reload the page, restore the fake folder + its files, then run the
        startup re-attach path (ensureFolder -> reattachFile -> refreshFileList)."""
        self.page.reload(wait_until="domcontentloaded", timeout=90000)
        self.page.wait_for_timeout(900)
        self.attach_folder()
        for n, t in files.items():
            self.dir_set(n, t)
        self.install_idb_stub()
        self.js("()=>ensureFolder(false).then(reattachFile).then(refreshFileList)")
        self.page.wait_for_timeout(600)


def head(title):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def ok(cond, msg):
    print(("  PASS  " if cond else "  FAIL  ") + msg)
    return bool(cond)
