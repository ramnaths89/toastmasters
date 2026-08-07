import os
APP = "file://" + os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "index.html"))
import asyncio, re
from playwright.async_api import async_playwright

URL = APP
res = []
def ck(name, ok, extra=""):
    res.append((ok, name, extra))
    print(("PASS  " if ok else "FAIL  ") + name + (("  | " + str(extra)) if extra else ""))

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width":1500,"height":950})
        errs=[]
        pg.on("console", lambda m: errs.append(m.text) if (m.type=="error" and "ERR_CONNECTION" not in m.text and "net::" not in m.text) else None)
        pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.goto(URL)
        await pg.evaluate("localStorage.clear()")
        await pg.reload()
        await pg.wait_for_timeout(700)

        # ---------- blank template ----------
        html = await pg.evaluate("document.documentElement.outerHTML")
        # V21 split the old blanket "no names" rule in two. Club officers hold for the
        # whole term, so they are hardcoded and SHOULD appear. Anything that changes
        # week to week -- roles, speakers, evaluators -- must still start blank.
        MEETING_NAMES = ["Alex Tan","Priya Menon","Wei Ling","Jordan Ng","Dana Poh","Riley Ong"]
        OFFICERS = ["<President Name>","<VP Education Name>","<VP Membership Name>",
                    "<VP Public Relations Name>","<Secretary Name>","<Treasurer Name>",
                    "<Sergeant at Arms Name>","<Immediate Past President Name>"]
        hits=[n for n in MEETING_NAMES if n in html]
        ck("no meeting-participant names in the builder DOM", not hits, hits)

        frame = pg.frames[1]
        sheet = await frame.evaluate("document.body.innerText")
        hits2=[n for n in MEETING_NAMES if n in sheet]
        ck("no meeting-participant names on the rendered sheet", not hits2, hits2)
        miss=[n for n in OFFICERS if n not in sheet]
        ck("club officers hardcoded onto the sheet", not miss, miss)
        ck("district officers keep their club field",
           sheet.count("<Their Club>") == 2, sheet.count("<Their Club>"))

        ck("roles all blank in state", await pg.evaluate(
            "Object.values(state.roles).every(v=>v==='')"))
        ck("no speaker names in state", await pg.evaluate(
            "state.segments.every(s=>!s.speakerName)"))
        ck("no projects preset", await pg.evaluate(
            "state.segments.filter(s=>s.isSpeech).every(s=>!s.project && !s.pathway)"))
        ck("meeting title/date blank", await pg.evaluate(
            "!state.meeting.title && !state.meeting.dateDisplay"))
        ck("club identity kept", await pg.evaluate(
            "state.meeting.clubName.includes('Nee Soon East') && !!state.meeting.location"))
        ck("exco posts carry their officer", await pg.evaluate(
            "state.execText.includes('VP Education|<VP Education Name>')"))
        ck("every exco line has a name", await pg.evaluate(
            "state.execText.split('\\n').every(l=>/\\|\\s*\\S/.test(l))"))
        ck("TBD chips render on sheet", "TBD" in sheet)
        ck("role inputs prompt TBD when blank", await pg.evaluate(
            "[...document.querySelectorAll('.roles-grid input[type=text]')].every(i=>i.placeholder==='TBD')"))
        ck("every text field carries a placeholder prompt", await pg.evaluate(
            "[...document.querySelectorAll('.form-pane input[type=text], .form-pane textarea')].every(i=>i.placeholder.length>0)"))

        # ---------- end time still lands ----------
        endtxt = await pg.evaluate("document.getElementById('endCheck').textContent")
        endcls = await pg.evaluate("document.getElementById('endCheck').className")
        ck("schedule still ends on target", "ok" in endcls, endtxt)

        # ---------- V21: club standard timings ----------
        STD = {'calltoorder':4,'welcome':4,'president':4,'returncontrol':1,'ttreturn':1,
               'evaluation':4,'speechvote':3,'ttvote':3,'evalvote':3}
        durs = await pg.evaluate(
            "(()=>{const o={};state.segments.forEach(s=>{(o[s.presetKey]=o[s.presetKey]||[]).push(s.durMin)});return o;})()")
        bad = {k:durs.get(k) for k,v in STD.items()
               if not durs.get(k) or any(d != v for d in durs[k])}
        ck("club standard durations applied", not bad, bad)
        ck("four speech slots and four evaluations", await pg.evaluate(
            "state.segments.filter(s=>s.isSpeech).length===4 && state.segments.filter(s=>s.isEvaluation).length===4"))
        ck("total run is exactly 150 min", await pg.evaluate(
            "state.segments.reduce((t,s)=>t+(Number(s.durMin)||0),0)===150"))

        # the three combined timer's-report + voting rows, in meeting order
        votes = await pg.evaluate(
            "state.segments.filter(s=>/vote$/.test(s.presetKey)).map(s=>[s.presetKey,s.title,s.sub,s.roleKey])")
        ck("three combined timer/voting rows", len(votes)==3, [v[0] for v in votes])
        ck("vote rows are chronological NSE_1/2/3",
           [v[2] for v in votes] == ["https://slido.com | Enter code: NSE_1",
                                     "https://slido.com | Enter code: NSE_2",
                                     "https://slido.com | Enter code: NSE_3"], [v[2] for v in votes])
        ck("vote row titles combine report + vote",
           all(t.startswith("Call for Timer's Report | Voting for") for _,t,_,_ in votes),
           [v[1] for v in votes])
        ck("vote rows are held by the Timer", all(v[3]=='timer' for v in votes), [v[3] for v in votes])
        ck("slido notes reach the sheet",
           sheet.count("slido.com")==3 and all(c in sheet for c in ("NSE_1","NSE_2","NSE_3")))
        ck("split timer/voting rows are gone from defaults", await pg.evaluate(
            "!state.segments.some(s=>['timerreport','voting','ttvoting','pevoting'].includes(s.presetKey))"))

        # ---------- V22: paired holders + idle speech-title placeholder ----------
        await pg.evaluate("()=>{ bindRole('timer','Casey Lim'); bindRole('tmod','Jordan Ng'); }")
        await pg.wait_for_timeout(400)
        vh = await frame.evaluate("""() => [...document.querySelectorAll('tbody tr')]
            .filter(r => r.innerText.indexOf('Voting for') >= 0)
            .map(r => r.querySelector('td.holder').innerText.split('\\n').filter(Boolean))""")
        # exactly TWO lines per row -- names only, Timer's name first then TME's (V25)
        ck("every voting row names two people on two lines",
           len(vh)==3 and all(len(v)==2 for v in vh), vh[:1])
        ck("voting rows show names only, no role labels",
           all("TIMER" not in v[0].upper() and "TME" not in v[1].upper() for v in vh), vh[:1])
        ck("voting rows carry both names, Timer's first",
           all(v[0].strip()=="Casey Lim" and v[1].strip()=="Jordan Ng" for v in vh), vh[:1])
        ck("a typed override still wins over the pair", await pg.evaluate("""()=>{
             const s = state.segments.find(x=>x.presetKey==='speechvote');
             s.holderOverride = 'Someone Else';
             const h = holderFor(s); s.holderOverride = '';
             return !h.rows && h.text === 'Someone Else'; }"""))
        # V24: Rama reversed the V22 grey title TBD -- every sheet TBD is red again,
        # and the grey prompt moved into the form's placeholder instead.
        ck("no grey idle TBD left on the sheet", await frame.evaluate(
            "document.querySelectorAll('.idle-inline').length===0"))
        ck("blank speech title prints a RED TBD", await frame.evaluate(
            """() => { const t=[...document.querySelectorAll('.poetts .rr-label')]
                         .find(l=>l.textContent.trim().toUpperCase().startsWith('TITLE'));
                       return !!(t && t.nextElementSibling.querySelector('.tbd-inline')); }"""))
        ck("speech-card title input prompts in grey", await pg.evaluate(
            "[...document.querySelectorAll('.speech-card input')].some(i=>i.placeholder==='Speech title')"))
        ck("speech title label no longer says optional", await pg.evaluate(
            "![...document.querySelectorAll('.speech-card label')].some(l=>/optional/i.test(l.textContent) && /title/i.test(l.textContent))"))
        await pg.evaluate("()=>{ bindRole('timer',''); bindRole('tmod',''); }")
        await pg.wait_for_timeout(300)

        # ---------- V25: retired themes ----------
        ck("six themes offered", await pg.evaluate("THEMES.length===6"), await pg.evaluate("THEMES.map(t=>t.key)"))
        ck("the surviving new themes are registered", await pg.evaluate(
            "['retrofuture','handmade'].every(k=>THEMES.some(t=>t.key===k))"))
        ck("retired themes are gone from the picker", await pg.evaluate(
            "!THEMES.some(t=>RETIRED_THEMES.includes(t.key))"))
        # Behaviour, not text: the rendered box must match the artwork's own aspect,
        # because html2canvas ignores object-fit and would stretch it in exports.
        ck("the TI logo keeps its natural aspect", await frame.evaluate(
            """() => { const i=document.querySelector('.pane-brand img');
                       const r=i.getBoundingClientRect();
                       return Math.abs(r.width/r.height - i.naturalWidth/i.naturalHeight) < 0.02; }"""))
        ck("no object-fit declaration is relied on", await pg.evaluate(
            "SHEET_CSS.indexOf('object-fit:')<0"))
        # classic IS the base stylesheet -- it has no body.th-classic block by design
        ck("every non-classic theme has a stylesheet block", await pg.evaluate(
            "THEMES.filter(t=>t.key!=='classic').every(t=>SHEET_CSS.indexOf('body.th-'+t.key)>=0)"))
        ck("every theme styles the brand box with its header", await pg.evaluate(
            """THEMES.filter(t=>t.key!=='classic')
                 .every(t=>SHEET_CSS.indexOf('body.th-'+t.key+' .pane-brand')>=0)"""))
        ck("Bauhaus/Broadsheet/Jetset gone from the picker", await pg.evaluate(
            "!THEMES.some(t=>['bauhaus','broadsheet','jetset'].includes(t.key))"))
        ck("a meeting saved on a retired theme falls back to Classic", await pg.evaluate("""(()=>{
             const raw = JSON.parse(localStorage.getItem(STORE_KEY));
             raw.state.theme = 'overprint';
             localStorage.setItem(STORE_KEY, JSON.stringify(raw));
             loadState();
             const t = state.theme;
             state.theme = 'classic';
             return t === 'classic'; })()"""))

        # ---------- V27: rehomed rows + multi-line sub + capped phone PDF ----------
        ck("TT return-control row is the TME's", await pg.evaluate(
            "(s=>s && s.roleKey==='tmod')(state.segments.find(x=>x.presetKey==='ttreturn'))"))
        ck("Award Presentation is the TME's", await pg.evaluate(
            "(s=>s && s.roleKey==='tmod' && !s.noHolder)(state.segments.find(x=>x.presetKey==='awards'))"))
        awards_sub = await frame.evaluate("""() => {
            const tr = [...document.querySelectorAll('tbody tr')]
              .find(r => r.querySelector('.item-title') && r.querySelector('.item-title').textContent.includes('Award Presentation'));
            const sub = tr && tr.querySelector('.item-sub');
            return sub ? sub.textContent.trim() : null; }""")
        ck("award sub-note is the single pipe-separated line",
           awards_sub == "Best Speaker | Table Topics | Evaluator", awards_sub)
        ck("photo session appointment is All", await frame.evaluate(
            """() => { const tr = [...document.querySelectorAll('tbody tr')]
                 .find(r => r.querySelector('.item-title') && r.querySelector('.item-title').textContent.includes('Photo Taking'));
               return tr && tr.querySelector('td.holder').textContent.trim() === 'All'; }"""))
        pdf_size = await pg.evaluate("""async () => {
            const full = await renderSheetCanvas();
            const canvas = full.width > MAX_EXPORT_WIDTH ? downscaleCanvas(full, MAX_EXPORT_WIDTH) : full;
            const M_PT = 10*72/25.4, PW_PT = 595.28, PH_PT = 841.89;
            const imgWpt = PW_PT - M_PT*2, pxPerPt = canvas.width/imgWpt;
            const sliceH = Math.floor((PH_PT - M_PT*2)*pxPerPt);
            const cut = document.createElement('canvas'); const ctx = cut.getContext('2d');
            const pages = [];
            for(let y=0; y<canvas.height; y+=sliceH){
              const h = Math.min(sliceH, canvas.height-y);
              cut.width = canvas.width; cut.height = h;
              ctx.fillStyle='#fff'; ctx.fillRect(0,0,cut.width,h);
              ctx.drawImage(canvas,0,y,canvas.width,h,0,0,canvas.width,h);
              const blob = await new Promise(r=>cut.toBlob(r,'image/jpeg',0.80));
              pages.push({bytes:new Uint8Array(await blob.arrayBuffer()), pxW:cut.width, pxH:h,
                          wPt:imgWpt, hPt:h/pxPerPt, xPt:M_PT, yPt:PH_PT-M_PT-h/pxPerPt});
            }
            return pdfFromJpegs(pages).size; }""")
        ck("phone PDF lands well under the old 1.3 MB", pdf_size <= 550*1024, f"{pdf_size//1024} KB")

        # ---------- V24: Word of the Day is tick-driven, default unticked ----------
        ck("Language Evaluator starts unticked", await pg.evaluate(
            "state.roleActive.langeval===false"))
        ck("no Word of the Day row by default", await pg.evaluate(
            "!state.segments.some(s=>s.presetKey==='langeval')"))
        await pg.evaluate("toggleRoleActive('langeval', true)")
        await pg.wait_for_timeout(400)
        ck("ticking adds the row with no name yet", await pg.evaluate(
            "state.segments.some(s=>s.presetKey==='langeval')"))
        sheet_le = await frame.evaluate("document.body.innerText")
        ck("Word of the Day prints with a TBD holder", "Word of the Day" in sheet_le)
        await pg.evaluate("toggleRoleActive('langeval', false)")
        await pg.wait_for_timeout(400)
        ck("unticking removes the row again", await pg.evaluate(
            "!state.segments.some(s=>s.presetKey==='langeval')"))

        # ---------- V24: the in-sheet editor is a full third surface ----------
        sp1 = await pg.evaluate("state.segments.find(s=>s.isSpeech).id")
        await frame.evaluate("id => parent.setEditingSeg(id)", sp1)
        await pg.wait_for_timeout(400)
        # sheet -> pane
        await frame.locator(".row-edit input").first.fill("Wired Up")
        await pg.wait_for_timeout(300)
        ck("in-sheet speaker edit reaches the pane card",
           await pg.locator(".speech-card .sc-name").first.inner_text() == "Wired Up")
        # in-sheet slot -> in-sheet lights, without a rebuild
        await frame.locator('.row-edit input[data-f="durMin"]').fill("12")
        await pg.wait_for_timeout(300)
        red_now = await frame.locator('.row-edit input[data-f="signalMax"]').input_value()
        ck("in-sheet slot edit refreshes the row's own lights", red_now=="11", red_now)
        # in-sheet speaker -> paired evaluation row, while still editing
        ev0 = await pg.evaluate("state.segments.filter(s=>s.isEvaluation)[0].id")
        ev_title = await frame.evaluate("""id => {
            const tr = document.querySelector('tbody tr[data-seg-id="'+id+'"]');
            return tr ? tr.querySelector('.item-title').textContent : null; }""", ev0)
        ck("paired evaluation row updates live during the edit",
           bool(ev_title) and "Wired Up" in ev_title, ev_title)
        # pane -> open edit row
        await pg.locator(".speech-card input").first.fill("Pane Wins")
        await pg.wait_for_timeout(500)
        row_val = await frame.locator(".row-edit input").first.input_value()
        ck("pane edit refreshes the open in-sheet row", row_val=="Pane Wins", row_val)
        # evaluation row edit writes the speaker back to the speech
        ev1 = await pg.evaluate("state.segments.filter(s=>s.isEvaluation)[0].id")
        await frame.evaluate("id => parent.setEditingSeg(id)", ev1)
        await pg.wait_for_timeout(400)
        await frame.locator(".row-edit input").first.fill("Mirror Back")
        await pg.wait_for_timeout(300)
        ck("evaluation-row speaker edit writes back to the speech", await pg.evaluate(
            "state.segments.find(s=>s.isSpeech).speakerName==='Mirror Back'"))
        ck("...and the pane card follows",
           await pg.locator(".speech-card .sc-name").first.inner_text() == "Mirror Back")
        await frame.evaluate("() => parent.setEditingSeg(null)")
        await pg.evaluate("()=>{ const s=state.segments.find(x=>x.isSpeech); updSpeech(s.id,'speakerName',''); updSpeech(s.id,'durMin','8'); }")
        await pg.wait_for_timeout(400)

        # ---------- V21: FLEXIBLE note hidden in print ----------
        await frame.page.emulate_media(media="print")
        note_print = await frame.evaluate(
            "getComputedStyle(document.querySelector('.schedule-note')).display")
        # media=None means "leave it alone", NOT "reset" -- passing it here left the whole
        # page in print emulation, which hides .cbx-btn and broke every later combobox step.
        await frame.page.emulate_media(media="screen")
        note_screen = await frame.evaluate(
            "getComputedStyle(document.querySelector('.schedule-note')).display")
        ck("FLEXIBLE note hidden in print", note_print=="none", note_print)
        ck("FLEXIBLE note still shown on screen", note_screen!="none", note_screen)

        # ---------- V21: cards inert until the grip is grabbed ----------
        ck("no card is draggable at rest", await pg.evaluate(
            "![...document.querySelectorAll('.seg-card,.speech-card')].some(c=>c.draggable)"))
        ck("grip arms the card for dragging", await pg.evaluate("""(()=>{
              const grip=document.querySelector('.speech-card .sc-grip');
              grip.dispatchEvent(new MouseEvent('mousedown',{bubbles:true}));
              const armed=grip.closest('.speech-card').draggable;
              document.dispatchEvent(new MouseEvent('mouseup',{bubbles:true}));
              return armed;
            })()"""))
        ck("mouseup disarms it again", await pg.evaluate(
            "!document.querySelector('.speech-card').draggable"))

        # click the middle of a filled field and check the caret landed there
        sp = pg.locator(".speech-card").first.locator("input").first
        await sp.fill("Wolfeschlegelsteinhausenbergerdorff")
        await pg.wait_for_timeout(120)
        box = await sp.bounding_box()
        await pg.mouse.click(box["x"] + box["width"]*0.45, box["y"] + box["height"]/2)
        await pg.wait_for_timeout(120)
        caret = await sp.evaluate("el=>el.selectionStart")
        ck("clicking mid-text places the caret there", 0 < caret < 34, caret)
        await sp.fill("")
        await pg.wait_for_timeout(150)

        # ---------- combobox: card ----------
        ck("no <datalist> left anywhere", await pg.evaluate(
            "document.querySelectorAll('datalist').length===0")
            and await frame.evaluate("document.querySelectorAll('datalist').length===0"))

        cbx = pg.locator(".speech-card").first.locator(".cbx")
        ck("combobox rendered in speech card", await cbx.count()==1)
        n_opts = await cbx.locator(".cbx-opt").count()
        ck("all 64 projects in the list", n_opts==64, n_opts)

        # click the ▾ button -> list opens showing everything
        await cbx.locator(".cbx-btn").click()
        await pg.wait_for_timeout(150)
        ck("▾ opens the list", await cbx.locator(".cbx-list").is_visible())
        vis = await cbx.locator(".cbx-opt:not(.hide)").count()
        ck("▾ shows every project (no filtering)", vis==64, vis)

        # type to narrow
        await cbx.locator(".cbx-input").fill("humor")
        await pg.wait_for_timeout(150)
        vis = await cbx.locator(".cbx-opt:not(.hide)").count()
        shown = await cbx.locator(".cbx-opt:not(.hide) .cbx-n").all_inner_texts()
        ck("typing narrows the list", 0 < vis < 64, f"{vis}: {shown[:4]}")
        ck("filter is case-insensitive substring", all("humor" in s.lower() for s in shown), shown)

        # meta is searchable too
        await cbx.locator(".cbx-input").fill("18")
        await pg.wait_for_timeout(120)
        vis18 = await cbx.locator(".cbx-opt:not(.hide)").count()
        ck("meta (timings) searchable", vis18>0, vis18)

        # keyboard: arrow + enter commits
        await cbx.locator(".cbx-input").fill("vocal variety")
        await pg.wait_for_timeout(120)
        await cbx.locator(".cbx-input").press("ArrowDown")
        await cbx.locator(".cbx-input").press("Enter")
        await pg.wait_for_timeout(300)
        proj = await pg.evaluate("state.segments.find(s=>s.isSpeech).project")
        ck("Enter commits the highlighted project", "Vocal" in proj or "Voice" in proj, proj)
        ck("picking a project pulls its timing", await pg.evaluate(
            "(s=>s.signalMax>0 && s.durMin>0)(state.segments.find(s=>s.isSpeech))"))

        # click-to-pick
        cbx = pg.locator(".speech-card").first.locator(".cbx")
        await cbx.locator(".cbx-btn").click()
        await pg.wait_for_timeout(120)
        await cbx.locator(".cbx-input").fill("Ice Breaker")
        await pg.wait_for_timeout(120)
        await cbx.locator(".cbx-opt:not(.hide)").first.click()
        await pg.wait_for_timeout(300)
        ck("mouse click commits", (await pg.evaluate("state.segments.find(s=>s.isSpeech).project"))=="Ice Breaker")

        # escape closes without committing
        cbx = pg.locator(".speech-card").first.locator(".cbx")
        await cbx.locator(".cbx-input").click()
        await pg.wait_for_timeout(120)
        await cbx.locator(".cbx-input").press("Escape")
        await pg.wait_for_timeout(200)
        ck("Escape closes the list", not await cbx.locator(".cbx-list").is_visible())
        ck("Escape leaves the project untouched",
           (await pg.evaluate("state.segments.find(s=>s.isSpeech).project"))=="Ice Breaker")

        # pathway/level ordering: in-level projects lead
        await pg.evaluate("updSpeechCatalog(state.segments.find(s=>s.isSpeech).id,'pathway','VC')")
        await pg.wait_for_timeout(200)
        await pg.evaluate("updSpeechCatalog(state.segments.find(s=>s.isSpeech).id,'pLevel','3')")
        await pg.wait_for_timeout(250)
        cbx = pg.locator(".speech-card").first.locator(".cbx")
        heres = await cbx.locator(".cbx-opt.here .cbx-n").all_inner_texts()
        firsts = await cbx.locator(".cbx-opt .cbx-n").all_inner_texts()
        ck("chosen pathway+level leads the list", len(heres)>0 and firsts[:len(heres)]==heres, heres)

        # ---------- combobox inside the preview iframe ----------
        await frame.evaluate("""() => {
          const tr = [...document.querySelectorAll('tbody tr[data-seg-id]')]
            .find(r => /Prepared Speech 1/.test(r.innerText));
          parent.setEditingSeg(tr.dataset.segId);
        }""")
        await pg.wait_for_timeout(400)
        icbx = frame.locator(".row-edit .cbx")
        ck("combobox renders inside the sheet edit row", await icbx.count()==1)
        await icbx.locator(".cbx-btn").click()
        await pg.wait_for_timeout(200)
        ck("in-sheet ▾ opens", await icbx.locator(".cbx-list").is_visible())
        await icbx.locator(".cbx-input").fill("Connect with Storytelling")
        await pg.wait_for_timeout(150)
        n = await icbx.locator(".cbx-opt:not(.hide)").count()
        ck("in-sheet typing narrows", 0 < n < 64, n)
        await icbx.locator(".cbx-opt:not(.hide)").first.click()
        await pg.wait_for_timeout(400)
        ck("in-sheet pick commits to state",
           "Storytelling" in (await pg.evaluate("state.segments.find(s=>s.isSpeech).project") or ""),
           await pg.evaluate("state.segments.find(s=>s.isSpeech).project"))

        # ---------- announcements ----------
        ann_js = ("bindText('announcementsText', %s)"
                  % __import__("json").dumps("Club anniversary dinner \u2014 20 Sept, sign up with the SAA\n\nRenewal dues due end of month"))
        await pg.evaluate(ann_js)
        await pg.wait_for_timeout(300)
        sheet2 = await frame.evaluate("document.body.innerText")
        ck("announcement text appears on sheet", "Club anniversary dinner" in sheet2 and "Renewal dues" in sheet2)
        ck("Announcements heading appears once filled", "ANNOUNCEMENTS" in sheet2.upper())
        pos_path = sheet2.upper().find("PATHWAYS")
        pos_ann  = sheet2.upper().find("ANNOUNCEMENTS")
        ck("Announcements sits after Pathways", pos_path != -1 and pos_ann != -1 and pos_ann > pos_path)

        await pg.evaluate("bindText('announcementsText','')")
        await pg.wait_for_timeout(300)
        sheet3 = await frame.evaluate("document.body.innerText")
        ck("empty announcements omits the heading", "ANNOUNCEMENTS" not in sheet3.upper())

        clean_ann = await pg.evaluate("(()=>{ bindText('announcementsText','Test line one'); const h = buildSheetHTML(false); bindText('announcementsText',''); return h; })()")
        ck("clean export includes announcement text when present", "Test line one" in clean_ann)

        # ---------- V21: timing syncs BOTH ways between the two panes ----------
        sp_id = await pg.evaluate("state.segments.find(s=>s.isSpeech).id")
        # Programme Segments is a <details> that starts closed -- its inputs exist but
        # are not visible, so Playwright will not type into them.
        await pg.evaluate("document.getElementById('segSection').open = true")
        await pg.evaluate(f"toggleSeg('{sp_id}')")           # expand its row in Programme Segments
        await pg.wait_for_timeout(200)
        seg_slot  = pg.locator(f'.seg-card[data-seg-id="{sp_id}"] .seg-details input[type=number]').first
        card_slot = pg.locator(f'.speech-card[data-sp-id="{sp_id}"] input[data-f=durMin]')
        await seg_slot.fill("11")
        await pg.wait_for_timeout(250)
        ck("Segments -> Speeches slot sync", await card_slot.input_value()=="11",
           await card_slot.input_value())
        ck("slot auto-splits the lights from either pane", await pg.evaluate(
            f"(s=>s.signalMax===10)(state.segments.find(x=>x.id==='{sp_id}'))"),
            await pg.evaluate(f"state.segments.find(x=>x.id==='{sp_id}').signalMax"))
        await card_slot.fill("9")
        await pg.wait_for_timeout(250)
        ck("Speeches -> Segments slot sync", await seg_slot.input_value()=="9",
           await seg_slot.input_value())
        await card_slot.fill("8")
        await pg.wait_for_timeout(200)

        # ---------- V21: apply the club standard to an existing meeting ----------
        pg.on("dialog", lambda d: asyncio.ensure_future(d.accept()))
        await pg.evaluate("""()=>{
          state.segments.forEach(s=>{ if(s.presetKey==='evaluation') s.durMin = 99; });
          state.roles.tmod = 'Keep Me';
          state.segments.find(s=>s.isSpeech).speakerName = 'Keep Me Too';
        }""")
        await pg.evaluate("applyStandardTimings()")
        await pg.wait_for_timeout(450)
        ck("standard retimes the evaluations", await pg.evaluate(
            "state.segments.filter(s=>s.presetKey==='evaluation').every(s=>s.durMin===4)"))
        ck("standard leaves roles alone", await pg.evaluate("state.roles.tmod==='Keep Me'"))
        ck("standard leaves speakers alone", await pg.evaluate(
            "state.segments.find(s=>s.isSpeech).speakerName==='Keep Me Too'"))

        # a pre-V21 meeting has the timer's report and the vote as two separate rows
        await pg.evaluate("""()=>{
          const i = state.segments.findIndex(s=>s.presetKey==='speechvote');
          state.segments.splice(i, 1, newSegment('timerreport'), newSegment('voting'));
        }""")
        await pg.evaluate("applyStandardTimings()")
        await pg.wait_for_timeout(450)
        ck("legacy split timer/voting rows merge into one", await pg.evaluate(
            "state.segments.filter(s=>s.presetKey==='speechvote').length===1"
            " && !state.segments.some(s=>['timerreport','voting'].includes(s.presetKey))"))
        ck("the merged row picks up its slido note", await pg.evaluate(
            "(s=>!!s && s.sub==='https://slido.com | Enter code: NSE_1')"
            "(state.segments.find(s=>s.presetKey==='speechvote'))"))
        await pg.evaluate("state.roles.tmod=''; state.segments.find(s=>s.isSpeech).speakerName='';")
        await pg.wait_for_timeout(150)

        # ---------- persistence + print cleanliness ----------
        await pg.wait_for_timeout(700)
        await pg.reload(); await pg.wait_for_timeout(700)
        ck("survives reload", "Storytelling" in (await pg.evaluate("state.segments.find(s=>s.isSpeech).project") or ""))
        clean = await pg.evaluate("buildSheetHTML(false)")
        body = clean.split('</style>')[-1]
        ck("clean export has no combobox markup", 'cbx-input' not in body and 'class="cbx' not in body)
        ck("clean export has no edit affordances", 'row-tools' not in body and 'drag-grip' not in body)

        ck("no JS errors", not errs, errs[:4])
        await b.close()

    bad = [r for r in res if not r[0]]
    print(f"\n{len(res)-len(bad)}/{len(res)} passed")
    return 1 if bad else 0

raise SystemExit(asyncio.run(main()))
