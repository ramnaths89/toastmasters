/* ================= Sheet builder =================
   interactive=true adds drag grips, row tools and inline edit fields —
   used only in the builder preview. Downloads/prints get the clean sheet. */
let editingSegId = null;

/* ---- inline edit-row field builders (rendered inside the preview iframe) ---- */
function fldTextML(seg, field, label, ph){
  return `<label class="re-f"><span>${label}</span>
    <textarea rows="2" placeholder="${esc(ph||'')}"
      oninput="parent.liveEdit('${seg.id}','${field}',this.value)">${esc(seg[field]||'')}</textarea></label>`;
}
function fldText(seg, field, label, ph){
  return `<label class="re-f"><span>${label}</span>
    <input type="text" value="${esc(seg[field]||'')}" placeholder="${esc(ph||'')}"
      oninput="parent.liveEdit('${seg.id}','${field}',this.value)"></label>`;
}
function fldNum(seg, field, label){
  const v = field === 'signalMid' ? midOf(seg) : seg[field];
  /* data-f makes the input addressable so syncEditRowInputs can push derived
     values (slot -> lights) back into the OPEN row without rebuilding it. */
  return `<label class="re-f re-n"><span>${label}</span>
    <input type="number" min="0" step="0.5" inputmode="decimal" value="${v}" data-f="${field}"
      oninput="parent.liveEdit('${seg.id}','${field}',this.value)"></label>`;
}
const lightsGrid = seg => `<div class="re-grid re-g4">`
  + fldNum(seg,'durMin','Slot (min)') + fldNum(seg,'signalMin','Green')
  + fldNum(seg,'signalMid','Amber')   + fldNum(seg,'signalMax','Red') + `</div>`;

function editRowHTML(seg, evPartner){
  let body = '';
  if(seg.isSpeech){
    const pathOpts = ['<option value="">— pathway —</option>'].concat(
      PATHWAYS_DATA.paths.map(p=>`<option value="${p.abbr}"${seg.pathway===p.abbr?' selected':''}>${p.abbr} — ${p.name}</option>`)).join('');
    const lvlOpts = ['<option value="">—</option>'].concat(
      [1,2,3,4,5].map(l=>`<option value="${l}"${String(seg.pLevel)===String(l)?' selected':''}>L${l}</option>`)).join('');
    body = `
      <div class="re-grid">
        ${fldText(seg,'speakerName','Speaker','Speaker name')}
        <label class="re-f"><span>Evaluator</span>
          <input type="text" value="${esc(evPartner?evPartner.holderOverride:'')}" placeholder="TBD"
            ${evPartner?`oninput="parent.liveEdit('${evPartner.id}','holderOverride',this.value)"`:'disabled'}></label>
      </div>
      <div class="re-grid re-g3">
        <label class="re-f"><span>Pathway</span>
          <select onchange="parent.catalogEdit('${seg.id}','pathway',this.value)">${pathOpts}</select></label>
        <label class="re-f"><span>Level</span>
          <select onchange="parent.catalogEdit('${seg.id}','pLevel',this.value)">${lvlOpts}</select></label>
        <label class="re-f"><span>Project</span>
          ${projectComboHTML(seg, 'sheet')}</label>
      </div>
      <div class="re-grid">
        ${fldText(seg,'speechTitle','Speech title','Speech title')}
      </div>
      ${lightsGrid(seg)}`;
  } else if(seg.isEvaluation){
    body = `
      <div class="re-grid">
        ${fldText(seg,'speakerName','Evaluating (speaker)','Speaker name')}
        ${fldText(seg,'holderOverride','Evaluator','TBD')}
      </div>
      ${lightsGrid(seg)}`;
  } else {
    const holderFld = seg.noHolder ? '' :
      fldText(seg,'holderOverride','Holder', seg.roleKey ? (state.roles[seg.roleKey] || 'TBD') : 'TBD');
    let timing = seg.flexible
      ? `<div class="re-grid re-g3">${fldNum(seg,'durMin','Nominal')}${fldNum(seg,'flexMin','Flex min')}${fldNum(seg,'flexMax','Flex max')}</div>`
      : (seg.hasSignal
          ? `<div class="re-grid re-g4">${fldNum(seg,'durMin','Duration')}${fldNum(seg,'signalMin','Green')}${fldNum(seg,'signalMid','Amber')}${fldNum(seg,'signalMax','Red')}</div>`
          : `<div class="re-grid">${fldNum(seg,'durMin','Duration (min)')}</div>`);
    body = `
      <div class="re-grid">${fldText(seg,'title','Title','Segment title')}${holderFld}</div>
      <div class="re-grid">${fldTextML(seg,'sub','Sub-note','Detail line printed under the title')}</div>
      ${timing}`;
  }
  return `<div class="row-edit">${body}</div>`;
}
/* One builder for every green/amber/red triplet on the sheet:
   three adjoining colour blocks with the time inside each. */
/* Thirty seconds past the red light is the disqualification bell — the point a
   speaker is out of qualifying time. It follows the red light wherever that
   lands, so it is derived here rather than stored (Rama, V21). */
const BELL_GRACE_MIN = 0.5;
function signalBoxes(green, amber, red, extra){
  const r = Number(red) || 0;
  return `<span class="sig-boxes">`
    + `<span class="b bg">${fmtSignalTime(green)}</span>`
    + `<span class="b by">${fmtSignalTime(amber)}</span>`
    + `<span class="b br">${fmtSignalTime(r)}</span>`
    + `</span>`
    + (r ? `<span class="sig-bell" title="Bell — 30 seconds past the red light, the end of qualifying time">🔔 ${fmtSignalTime(r + BELL_GRACE_MIN)}</span>` : '')
    + (extra ? `<span class="sig-suffix">${extra}</span>` : '');
}
/* ================= Project combobox =================
   Replaces <datalist>, which gave click-to-browse OR type-to-filter depending
   on how the field was poked and hid the timing meta the moment you typed.
   This is a real combobox: ▾ opens the whole catalog, typing narrows it on
   name AND meta (so "L3", "elective", "humor" all work), ↑↓ + Enter pick.
   It renders in the builder pane AND inside the preview iframe, so every
   handler is reached through `parent.` and works off the element's own
   document — in the top window `parent === window`, so one markup fits both. */

/* Catalog size as the user experiences it: what the ▾ list can actually offer. */
const PICKABLE_PROJECT_COUNT = ALL_PROJECTS.filter(
  n => !(PATHWAYS_DATA.projects[n]||{}).legacy).length;

/* Ordered choices: the chosen pathway+level first, then the rest of the catalog. */
function projectChoices(seg){
  const inLevel = (seg.pathway && seg.pLevel) ? projectsFor(seg.pathway, seg.pLevel) : [];
  const seen = new Set(inLevel.map(p=>p.n));
  /* An Education Series title says which series it belongs to instead of
     required/elective — "elective" is true but useless when the member has to
     give one of them, and the series is what they actually need to recognise. */
  const head = inLevel.map(p=>({
    n: p.n,
    meta: `${p.s || (p.e ? 'elective' : 'required')} · ${timingLabel(p.n)}`,
    here: true }));
  /* A `legacy` project still resolves a duration for meetings saved before it was
     superseded, but it is never offered as a choice. Evaluation and Feedback was split
     into (1st Speech) and (2nd Speech) because the project IS two speeches and the sheet
     has to say which one tonight is; the un-suffixed name would otherwise sit in the
     catalog beside both halves and read like a third option. Filtered HERE rather than
     dropped from PATHWAYS_DATA.projects, because projectInfo() is what gives an
     already-saved meeting its 5-7 min and its note. */
  const rest = ALL_PROJECTS.filter(n=>!seen.has(n) && !(PATHWAYS_DATA.projects[n]||{}).legacy).map(n=>{
    const series = seriesOf(n);
    const where = series ? null : (seg.pathway ? levelOfProjectIn(seg.pathway, n) : null);
    const tag = series ? series : (where ? `${seg.pathway} L${where.level}` : 'other path');
    return { n, meta: `${tag} · ${timingLabel(n)}`, here: false };
  });
  return head.concat(rest);
}
/* handler: 'card' → the speech card in the form pane; 'sheet' → the inline edit row. */
function projectComboHTML(seg, handler){
  const opts = projectChoices(seg).map(r=>
    `<div class="cbx-opt${r.n===seg.project?' sel':''}${r.here?' here':''}" role="option"
       data-val="${esc(r.n)}" data-search="${esc((r.n + ' ' + r.meta).toLowerCase())}"
       onmousedown="parent.cbxPick(event,this)"
      ><span class="cbx-n">${esc(r.n)}</span><span class="cbx-m">${esc(r.meta)}</span></div>`).join('');
  return `<div class="cbx" data-cbx="${seg.id}" data-handler="${handler}">
    <input type="text" class="cbx-input" role="combobox" aria-expanded="false" autocomplete="off"
      value="${esc(seg.project)}" placeholder="Click ▾ or type to search all ${PICKABLE_PROJECT_COUNT} projects…"
      onfocus="parent.cbxOpen(this)" onclick="parent.cbxOpen(this)"
      oninput="parent.cbxFilter(this)" onkeydown="parent.cbxKey(event,this)"
      onblur="parent.cbxBlur(this)">
    <button type="button" class="cbx-btn" tabindex="-1" aria-label="Show all projects"
      onmousedown="parent.cbxToggle(event,this)">▾</button>
    <div class="cbx-list" role="listbox">${opts}
      <div class="cbx-empty">No project matches — press Enter to keep what you typed.</div>
    </div>
  </div>`;
}

const cbxRoot = el => el.closest('.cbx');
function cbxShow(root, query){
  const terms = String(query||'').toLowerCase().split(/\s+/).filter(Boolean);
  let shown = 0, first = null;
  root.querySelectorAll('.cbx-opt').forEach(o=>{
    const ok = !terms.length || terms.every(t => o.dataset.search.includes(t));
    o.classList.toggle('hide', !ok);
    if(ok){ shown++; if(!first) first = o; }
  });
  root.querySelector('.cbx-empty').style.display = shown ? 'none' : 'block';
  return first;
}
function cbxMark(root, opt){
  root.querySelectorAll('.cbx-opt.act').forEach(o=>o.classList.remove('act'));
  if(!opt) return;
  opt.classList.add('act');
  opt.scrollIntoView({block:'nearest'});
}
/* Flip the list above the field when there isn't room below it in this document. */
function cbxPlace(root){
  const win = root.ownerDocument.defaultView;
  const box = root.getBoundingClientRect();
  root.classList.toggle('up', (win.innerHeight - box.bottom) < 200 && box.top > 220);
}
function cbxOpen(input){
  const root = cbxRoot(input);
  if(!root || root.classList.contains('open')) return;
  root.classList.add('open');
  input.setAttribute('aria-expanded','true');
  cbxPlace(root);
  cbxShow(root, '');                                   /* opening always shows everything */
  cbxMark(root, root.querySelector('.cbx-opt.sel') || root.querySelector('.cbx-opt'));
}
function cbxClose(root){
  if(!root) return;
  root.classList.remove('open','up');
  const input = root.querySelector('.cbx-input');
  if(input) input.setAttribute('aria-expanded','false');
}
function cbxFilter(input){
  const root = cbxRoot(input);
  if(!root) return;
  if(!root.classList.contains('open')){ root.classList.add('open'); cbxPlace(root); }
  cbxMark(root, cbxShow(root, input.value));
}
function cbxToggle(e, btn){
  e.preventDefault();                                  /* keep focus in the input */
  const root = cbxRoot(btn), input = root.querySelector('.cbx-input');
  if(root.classList.contains('open')) cbxClose(root);
  else { input.focus(); cbxOpen(input); }
}
function cbxPick(e, opt){
  e.preventDefault();                                  /* fire before blur */
  cbxCommit(cbxRoot(opt), opt.dataset.val);
}
function cbxKey(e, input){
  const root = cbxRoot(input);
  if(!root) return;
  const open = root.classList.contains('open');
  if(e.key === 'ArrowDown' || e.key === 'ArrowUp'){
    e.preventDefault();
    if(!open) return cbxOpen(input);
    const opts = Array.from(root.querySelectorAll('.cbx-opt:not(.hide)'));
    const i = opts.indexOf(root.querySelector('.cbx-opt.act'));
    cbxMark(root, opts[e.key === 'ArrowDown' ? Math.min(opts.length-1, i+1) : Math.max(0, i-1)]);
  } else if(e.key === 'Enter'){
    e.preventDefault();
    const act = open && root.querySelector('.cbx-opt.act:not(.hide)');
    cbxCommit(root, act ? act.dataset.val : input.value);  /* Enter on no match keeps the typed text */
  } else if(e.key === 'Escape'){
    if(!open) return;
    e.preventDefault(); e.stopPropagation();
    cbxClose(root);
  } else if(e.key === 'Tab'){
    cbxClose(root);
  }
}
/* Committing re-renders and destroys this node, so a pick's blur lands on a
   detached element — isConnected keeps it from committing a second time. */
function cbxBlur(input){
  const root = cbxRoot(input);
  setTimeout(()=>{
    if(!root || !root.isConnected) return;
    cbxClose(root);
    const seg = state.segments.find(s=>s.id === root.dataset.cbx);
    if(seg && input.value !== seg.project) cbxCommit(root, input.value);
  }, 0);
}
function cbxCommit(root, value){
  const id = root.dataset.cbx;
  cbxClose(root);
  if(root.dataset.handler === 'sheet') catalogEdit(id, 'project', value);
  else updSpeechProject(id, value);
}

function buildSheetHTML(interactive){
  const m = state.meeting;
  const {rows} = computeSchedule();
  const evals = activeSegments().filter(s=>s.isEvaluation);
  const speeches = activeSegments().filter(s=>s.isSpeech);
  const openRoles = openRoleLabels();

  const excoBlock = (title, rowsTxt) => `<div class="exco-block"><h3>${title}</h3>` +
    parsePipeRows(rowsTxt).map(([role,name,sub])=>`
    <div class="exco-item"><div class="exco-role">${esc(role)}</div><div class="exco-name">${esc(name)}</div>${sub?`<div class="exco-sub">(${esc(sub)})</div>`:''}</div>`).join('') + '</div>';

  const linkRows = parsePipeRows(state.linksText).map(([label,url,shown])=>`
    <div class="exco-item"><div class="exco-role">${esc(label)}</div><a href="${esc(url)}" target="_blank">${esc(shown||url)}</a></div>`).join('');
  /* Free-typed, one line per announcement — not pipe-delimited like the blocks
     above it, since there's no second field to split on. Blank lines between
     announcements are kept as visual breaks; the block itself is omitted
     entirely when empty rather than printing a bare "Announcements" heading. */
  const announceLines = state.announcementsText.split('\n');
  const announceRows = announceLines.map(l=>l.trim()).some(Boolean)
    ? announceLines.map(l=>l.trim() ? `<div class="announce-line">${esc(l.trim())}</div>` : '<div class="announce-gap"></div>').join('')
    : '';
  /* Built from the catalog rather than a free-text field so it can never drift:
     active paths first, then a perforated rule, then the retired ones. */
  const active = PATHWAYS_DATA.paths.filter(p=>!p.retired);
  const retired = PATHWAYS_DATA.paths.filter(p=>p.retired);
  const pathRows =
    active.map(p=>`<div><b>${esc(p.abbr)}</b> — ${esc(p.name)}</div>`).join('')
    + (retired.length ? `<div class="path-sep">Retired paths</div>` : '')
    + retired.map(p=>`<div class="path-retired"><b>${esc(p.abbr)}</b> — ${esc(p.name)}</div>`).join('');

  /* Emitted twice — once per printed page (see the .ref-pane note in sheet.css). */
  const paneInner = `
      ${excoBlock('Executive Committee', state.execText)}
      ${excoBlock('District Officers', state.districtText)}
      <div class="exco-block links"><h3>Links</h3>${linkRows}</div>
      <div class="exco-block path-legend"><h3>Pathways</h3>${pathRows}</div>
      ${announceRows ? `<div class="exco-block announcements"><h3>Announcements</h3>${announceRows}</div>` : ''}`;

  const tableRows = rows.map(({seg,clock}, idx)=>{
    const rowClasses = [(idx % 2 === 1) ? 'alt' : '', seg.flexible ? 'flex-row' : ''].filter(Boolean).join(' ');
    const rowAttrs = interactive ? ` data-seg-id="${seg.id}"` : '';

    /* ---- inline edit mode ---- */
    if(interactive && editingSegId === seg.id){
      const partner = seg.isSpeech ? evals[speeches.findIndex(s=>s.id===seg.id)] : null;
      return `
          <tr class="${rowClasses} row-editing"${rowAttrs}>
            <td class="time">${clock}</td>
            <td class="item" colspan="2">
              ${editRowHTML(seg, partner)}
              <div class="re-actions">
                <button class="re-done" onclick="parent.setEditingSeg(null)">✓ Done</button>
                <button class="re-del" onclick="parent.removeSeg('${seg.id}')">✕ Remove segment</button>
              </div>
            </td>
          </tr>`;
    }

    const h = holderFor(seg);
    const titleHtml = `<span class="item-title">${esc(titleFor(seg))}</span>`;

    let subHtml = '';
    if(seg.isSpeech){
      const dots = signalBoxes(seg.signalMin, midOf(seg), seg.signalMax);
      subHtml = `<span class="poetts">` + speechPOETTS(seg).map(r =>
          `<span class="rr-label">${esc(r.label)}</span>`
          + `<span class="rr-name">${r.tbd ? '<span class="tbd-inline">TBD</span>' : esc(r.value)}`
          + `${r.k === 'timing' && seg.signalMax ? dots : ''}</span>`
        ).join('') + `</span>`;
    } else if(seg.flexible){
      subHtml = `<span class="item-sub"><span class="flex-badge">FLEXIBLE</span>${seg.flexMin}&ndash;${seg.flexMax} min &middot; nominal ${seg.durMin} min${seg.sub?' &middot; '+esc(seg.sub).replace(/\n/g,' &middot; '):''}</span>`;
    } else if(seg.sub){
      const tail = seg.hasSignal?(' &middot; '+fmtSignalTime(seg.signalMin)+'&ndash;'+fmtSignalTime(seg.signalMax)+' min'):'';
      /* A newline in the sub-note is a line break on the sheet - the Award
         Presentation row lists its three awards this way (V27). */
      subHtml = `<span class="item-sub">${esc(seg.sub).replace(/\n/g,'<br>')}${tail}</span>`;
    } else if(seg.hasSignal){
      subHtml = `<span class="item-sub">${fmtSignalTime(seg.signalMin)}&ndash;${fmtSignalTime(seg.signalMax)} min</span>`;
    }


    /* The TME introduces the role players here — list every one of them. */
    const rolePlayersHtml = (seg.presetKey === 'welcome')
      ? `<span class="role-roster">` + rolePlayerLines().map(r =>
          `<span class="rr-label">${esc(r.label)}</span>` +
          `<span class="rr-name">${r.tbd ? '<span class="tbd-inline">TBD</span>' : esc(r.name)}</span>`
        ).join('') + `</span>` : '';

    let signalHtml = '';
    if(seg.hasSignal && !seg.isSpeech){
      signalHtml = `<span class="signal-line">` + signalBoxes(seg.signalMin, midOf(seg), seg.signalMax,
        seg.signalSuffix ? esc(seg.signalSuffix) : '') + `</span>`;
    }

    /* h.rows = a row run by two people (Timer then TME on the vote rows) -
       names only, one per line. */
    const holderHtml = h.rows
      ? `<span class="holder-pair">` + h.rows.map(r =>
          `<span class="hp-line">${r.tbd ? '<span class="tbd">TBD</span>' : esc(r.name)}</span>`
        ).join('') + `</span>`
      : h.tbd ? `<span class="tbd">TBD</span>`
      : (h.text === '—' || seg.noHolder) ? '&mdash;' : esc(h.text);

    const tools = interactive ? `<span class="row-tools">
        <button onclick="parent.moveSeg('${seg.id}',-1)" title="Move up">▲</button>
        <button onclick="parent.moveSeg('${seg.id}',1)" title="Move down">▼</button>
        <button class="rt-edit" onclick="parent.setEditingSeg('${seg.id}')" title="Edit this row here">✎ Edit</button>
        <button onclick="parent.removeSeg('${seg.id}')" title="Remove">✕</button>
      </span>` : '';
    const grip = interactive ? `<span class="drag-grip" title="Drag to reorder">⠿</span>` : '';

    return `
          <tr class="${rowClasses}"${rowAttrs}>
            <td class="time">${grip}${clock}</td>
            <td class="item">
              ${tools}
              ${titleHtml}
              ${subHtml}
              ${rolePlayersHtml}
              ${signalHtml}
            </td>
            <td class="holder">${holderHtml}</td>
          </tr>`;
  }).join('');

  /* Working aid, not part of the sheet. "Roles still open ... please fill before the
     meeting" is addressed to whoever is BUILDING the agenda. Rama: "it's unprofessional
     if it makes it into production for guests and members." Gated on `interactive`, so it
     survives in the live preview and appears in NOTHING that leaves the tab - the HTML
     download, the PDF, the JPG, and the hidden iframe that measures the pane fit. */
  const openRolesHtml = (interactive && openRoles.length)
    ? `<div class="theme-strip">Roles still open: ${openRoles.map(r=>`<b>${esc(r)}</b>`).join(', ')} — please fill before the meeting.</div>`
    : '';

  return `<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(m.clubName)} — Programme Sheet</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@500;600;700;800&family=Source+Sans+3:wght@400;600;700&display=swap" rel="stylesheet">
<style>${SHEET_CSS}</style>
</head><body class="th-${esc(state.theme||'classic')}${interactive?' interactive':''}">
${interactive ? `<div class="print-fab"><button class="print-btn" onclick="window.print()">🖨 <span class="label">Print / Save PDF</span></button></div>` : ''}
<div class="page-wrap"><div class="page">
  <header>
    <div class="head-text">
      <p class="club">${esc(m.clubName)}</p>
      <p class="clubnum">${esc(m.orgLine || ('Club Number: ' + m.clubNumber))}</p>
      ${m.title ? `<p class="meeting-title">${esc(m.title)}</p>` : ''}
      <div class="meta-row">
        ${m.dateDisplay ? `<div><b>Date:</b> ${esc(m.dateDisplay)}</div>` : ''}
        <div><b>Time:</b> ${fmtClock(parseTimeToMin(m.startTime))} &ndash; ${fmtClock(parseTimeToMin(m.endTime))}</div>
        ${m.location ? `<div><b>Location:</b> ${esc(m.location)}</div>` : ''}
      </div>
      ${m.cadence ? `<p class="cadence">${esc(m.cadence)}</p>` : ''}
    </div>
  </header>
  <div class="body-grid">
    <main>
      ${openRolesHtml}
      <div class="schedule-note"><span class="flex-badge">FLEXIBLE</span> segments can compress or stretch within their stated range so the meeting still lands on its published start/end time. Every other segment keeps the fixed time shown.${interactive?' <b>Tip:</b> hover a row → <b>✎ Edit</b> to change it right here; drag the ⠿ grip to reorder.':''}</div>
      <table>
        <thead><tr><th class="col-time">Time</th><th>Programme Item</th><th class="col-holder">Appointment Holder</th></tr></thead>
        <tbody>${tableRows}</tbody>
      </table>
    </main>
    <aside class="ref-pane">
      <div class="pane-brand"><img src="data:image/png;base64,${LOGO_B64}" alt="Toastmasters International"></div>
      <div class="pane-body">${paneInner}</div>
    </aside>
  </div>
  <footer>
    <span>${esc(m.clubName)} &middot; Club ${esc(m.clubNumber)} &middot; ${esc(m.footerNote)}</span>
    <span>Prepared ${todayStr()}</span>
  </footer>
</div></div>
</body></html>`;
}

/* ================= Preview ================= */
let previewTimer = null;

function renderPreviewNow(){
  const iframe = document.getElementById('previewFrame');
  const doc = iframe.contentDocument;
  const scrollY = iframe.contentWindow ? iframe.contentWindow.scrollY : 0;
  doc.open();
  doc.write(buildSheetHTML(true));
  doc.close();
  attachPreviewInteractions(doc);
  if(scrollY) iframe.contentWindow.scrollTo(0, scrollY);
  updateEndCheck();
  queuePaneFitCheck();
  queueSave();
}
function updatePreview(){
  clearTimeout(previewTimer);
  previewTimer = setTimeout(renderPreviewNow, 150);
}

/* ================= Print fit: does the reference pane survive Ctrl+P? (V36) ===
   The PRINTED pane is position:fixed, one page tall, with overflow:hidden, so it
   can repeat identically on every page. The cost is that anything past the bottom
   is CUT - no page 3, no warning - and what sits at the bottom is Announcements,
   the only block on the sheet written the same week it is read. Rama has lost it
   in the post more than once.
   The PDF and JPG downloads do NOT have this problem: they rasterise the pane
   separately and repaint it per page, so a long pane flows. That makes the honest
   advice "use Download instead", not "write less", and it is why this is a notice
   rather than another round of compaction. Compaction was tried in V30 and the
   remaining overrun cases need 281 mm of material in a 234 mm column.

   MEASUREMENT. The builder runs in screen media, so the print layout has to be
   reproduced deliberately: render buildSheetHTML(false) into a hidden iframe sized
   to the A4 page BOX - 190 x 277 mm at 96 dpi, i.e. A4 less the sheet's own 1 cm
   margins - and then retarget every @media print block in the sheet's own
   stylesheet to 'all' through the CSSOM. position:fixed then resolves against the
   same box the printer hands it. Checked against real print emulation across five
   loads x five themes: worst disagreement 0.01 mm.

   This is the one place where mutating the CSSOM is sound. The EXPORT path must
   never do it: html2canvas clones the style NODES and re-parses the original CSS
   text, so a CSSOM mutation measures right and renders wrong. Here nothing is
   rendered - the frame is measured and destroyed. */
/* PRINT_W_MM / PRINT_H_MM / PX_PER_MM are declared with the export geometry
   further down this file - the same page box, and they must stay the same page
   box, so they are shared rather than restated. Both are const in this one script
   block, so a second declaration here is a hard SyntaxError that takes the whole
   app down; that is how this was caught. */
/* Everything the pane's height depends on, and nothing else. The pane carries the
   Exco, the District officers, the Links, the (static) Pathways legend and the
   Announcements - no part of it moves when a speech or a segment does. Gating on
   this is what keeps a measurement that costs an iframe off the keystroke path. */
function paneFitSignature(){
  return [state.execText, state.districtText, state.linksText,
          state.announcementsText, state.theme].join('\u0000');
}
/* Three separate facts, and conflating any two of them has cost a defect each:
     sig      - the signature the NUMBER describes. Renders only against this.
     trusted  - whether the fonts had settled when it was taken. An untrusted
                number is shown (it is the best available) but is re-measured.
     mm       - the number itself. Never blanked; staleness is decided by sig. */
let paneFit = { sig: null, mm: null, lineMm: null, trusted: false,
                running: false, dismissed: '', fails: 0, provisional: 0 };
let paneFitTimer = null;
/* After this many consecutive failures the check gives up for the session. The
   first version retried whenever the measured signature did not match the current
   one, which is correct while measurements SUCCEED and an unbounded 700ms loop
   building iframes forever the moment one stops. */
const PANE_FIT_MAX_FAILS = 3;
/* And a separate, smaller budget for runs that SUCCEEDED but without fonts. On a
   file:// page with no network the Google Fonts link never resolves, so
   document.fonts.ready never settles and every run is provisional - which counted
   as success, reset the failure budget, and left the signature permanently
   unmatchable. The result was a full offscreen sheet render on every keystroke
   anywhere in the builder, forever. After this many tries the fallback-metric
   number is accepted and stamped; it is what that machine will print anyway. */
const PANE_FIT_MAX_PROVISIONAL = 3;

/* Resolve when the frame is usable, not when every subresource has landed. The
   sheet links Google Fonts; on a machine with no network that link can stall the
   load event for twelve seconds. Whatever the fonts do, the measurement then
   reflects the metrics the PRINTER would use in that same state, which is the
   only self-consistent answer available. */
function framePrintReady(frame, html){
  return new Promise(resolve=>{
    let done = false;
    const finish = ()=>{ if(!done){ done = true; resolve(); } };
    frame.onload = finish;
    setTimeout(finish, 3000);
    frame.srcdoc = html;
  });
}

async function measurePaneFit(){
  if(typeof document.createElement !== 'function') return null;
  const frame = document.createElement('iframe');
  frame.setAttribute('aria-hidden', 'true');
  frame.setAttribute('tabindex', '-1');
  frame.style.cssText = 'position:fixed;left:-10000px;top:0;border:0;visibility:hidden;'
    + 'width:' + (PRINT_W_MM * PX_PER_MM) + 'px;height:' + (PRINT_H_MM * PX_PER_MM) + 'px;';
  document.body.appendChild(frame);
  try{
    await framePrintReady(frame, buildSheetHTML(false));
    const idoc = frame.contentDocument;
    if(!idoc) return null;
    for(const ss of idoc.styleSheets){
      let rules;
      try{ rules = ss.cssRules; }catch(e){ continue; }   /* cross-origin sheet */
      for(const r of rules){
        if(r.type === CSSRule.MEDIA_RULE && /print/.test(r.conditionText)) r.media.mediaText = 'all';
      }
    }
    /* Whether the fonts settled is reported, not swallowed. Fallback metrics give
       different line heights from Montserrat and Source Sans 3, so a verdict
       reached without them is provisional and must not be cached. */
    let fontsReady = true;
    if(idoc.fonts && idoc.fonts.ready){
      fontsReady = await Promise.race([
        idoc.fonts.ready.then(()=>true),
        new Promise(r=>setTimeout(()=>r(false), 1200))]);
    }
    await new Promise(r=>setTimeout(r, 60));
    const aside = idoc.querySelector('aside.ref-pane');
    const body  = idoc.querySelector('.pane-body');
    if(!aside || !body || !body.children.length) return null;
    const last = body.children[body.children.length - 1];
    const overMm = (last.getBoundingClientRect().bottom - aside.getBoundingClientRect().bottom) / PX_PER_MM;
    /* Self-calibrating headroom. "One more line will be cut" only means something
       if the line height comes from the sheet as it is actually set, so it is
       measured here rather than written down - every print-density tune since V21
       would otherwise have quietly invalidated a hardcoded threshold. Fall back to
       the announcement line only if there is no last row to measure. */
    const probe = body.querySelector('.announce-line') || body.querySelector('.exco-item')
               || body.querySelector('.path-legend div');
    const lineMm = probe ? probe.getBoundingClientRect().height / PX_PER_MM : 3.5;
    return { mm: overMm, lineMm: lineMm, fontsReady: fontsReady };
  }catch(e){
    return null;          /* never let a diagnostic break the builder */
  }finally{
    frame.remove();
  }
}

/* Debounced and signature-gated. A run in flight is not cancelled - it is allowed
   to finish and then re-checked against the signature, so an edit made mid-measure
   cannot leave a stale number on screen. */
function queuePaneFitCheck(){
  /* Repaint first, whatever happens next: renderPrintNotice() hides a measurement
     that no longer describes the sheet on screen. Saying nothing beats saying
     something that was true two edits ago - a clipping warning still up after the
     announcements have been deleted teaches the user to ignore the next one. This
     runs even after the check has given up, or a stale notice would be the LAST
     thing it ever said. */
  renderPrintNotice();
  if(paneFit.fails >= PANE_FIT_MAX_FAILS) return;
  clearTimeout(paneFitTimer);
  paneFitTimer = setTimeout(runPaneFitCheck, 700);
}
async function runPaneFitCheck(){
  const sig = paneFitSignature();
  /* Was: return early whenever the signature matched the last measured one. That
     is right on its own, but an earlier version also blanked paneFit.mm on every
     change, so typing an announcement and deleting it again inside the 700ms
     debounce left mm null with the signature back where it started - and the
     shortcut then made sure it was never measured again. Nothing is blanked now
     and the guard tests the ANSWER, not just the question. */
  if((sig === paneFit.sig && paneFit.trusted) || paneFit.running) return;
  paneFit.running = true;
  let ok = false;
  try{
    const r = await measurePaneFit();
    if(r){
      /* Stamp the signature EITHER WAY. An untrusted number still describes THIS
         sheet, and leaving sig null to force a re-measure also switched off the
         staleness gate that decides whether to show it at all - so the previous
         sheet's number was painted against the new one and never chased. Trust is
         tracked on its own flag, which is what schedules the retry. */
      paneFit.mm = r.mm; paneFit.lineMm = r.lineMm; paneFit.sig = sig;
      paneFit.trusted = !!r.fontsReady;
      paneFit.provisional = r.fontsReady ? 0 : paneFit.provisional + 1;
      if(!r.fontsReady && paneFit.provisional >= PANE_FIT_MAX_PROVISIONAL) paneFit.trusted = true;
      ok = true;
    }
  }finally{
    paneFit.running = false;
  }
  paneFit.fails = ok ? 0 : paneFit.fails + 1;
  renderPrintNotice();
  /* Chase only if this run produced a number AND there is something left to chase:
     the sheet moved on while the frame was loading, or the fonts have not settled
     and the provisional budget is not spent. Retrying a failure on a 700ms timer
     is a loop with no exit, and so is retrying an unsettleable font. */
  if(ok && (paneFitSignature() !== paneFit.sig || !paneFit.trusted)) queuePaneFitCheck();
}

function dismissPrintNotice(){
  /* String(), because paneFit.sig is null for a provisional measurement (fonts
     not settled) and '' === null is false - the notice came straight back. */
  paneFit.dismissed = String(paneFit.sig);
  renderPrintNotice();
}
function renderPrintNotice(){
  const el = document.getElementById('printNotice');
  if(!el) return;
  const mm = paneFit.mm, line = paneFit.lineMm || 3.5;
  let cls = '', msg = '';
  /* A measurement of a different sheet is worse than no measurement, and that is
     true of a provisional one too - the gate used to skip itself whenever sig was
     null, which was exactly the provisional case. */
  if(paneFit.sig !== paneFitSignature()){
    el.hidden = true; el.textContent = ''; return;
  }
  if(mm == null){ /* not measured yet */ }
  else if(mm > 0){
    cls = 'over';
    msg = 'Printing this with Ctrl+P would cut about ' + Math.ceil(mm) + ' mm off the bottom of '
        + 'the reference pane — the Announcements go first. Use ⭳ Download → PDF, which flows the '
        + 'pane down the page properly, or shorten the Exco, Links or Announcements.';
  } else if(mm > -line){
    cls = 'near';
    msg = 'The reference pane is within one line of the bottom of the printed page. One more '
        + 'announcement and Ctrl+P would cut it off. ⭳ Download → PDF is unaffected.';
  }
  if(!msg || paneFit.dismissed === String(paneFit.sig)){ el.hidden = true; el.textContent = ''; return; }
  el.className = 'print-notice ' + cls;
  el.textContent = msg;
  const x = document.createElement('button');
  x.type = 'button'; x.className = 'pn-x'; x.textContent = '×';
  x.setAttribute('aria-label', 'Dismiss this notice');
  x.onclick = dismissPrintNotice;
  el.appendChild(x);
  el.hidden = false;
}
/* Update only the clock column in-place — used while typing in an inline edit row
   so the field being typed into is never destroyed. */
function refreshPreviewTimes(){
  const doc = document.getElementById('previewFrame').contentDocument;
  if(!doc) return;
  const {rows} = computeSchedule();
  doc.querySelectorAll('tbody tr[data-seg-id]').forEach((tr, i)=>{
    const td = tr.querySelector('td.time');
    if(!td || !rows[i]) return;
    const grip = td.querySelector('.drag-grip');
    td.textContent = rows[i].clock;
    if(grip) td.insertBefore(grip, td.firstChild);
  });
}

function setEditingSeg(id){
  editingSegId = id;
  renderPreviewNow();
  if(id){
    const doc = document.getElementById('previewFrame').contentDocument;
    const row = doc.querySelector(`tr.row-editing`);
    if(row){
      row.scrollIntoView({block:'center'});
      const first = row.querySelector('input');
      if(first) first.focus();
    }
  }
}
/* Text/number field inside an edit row: update state without re-rendering the row */
function liveEdit(id, field, value){
  const seg = state.segments.find(s=>s.id===id);
  if(!seg) return;
  /* Editing the Language Evaluator's own row writes back to the role field. */
  if(seg.presetKey === 'langeval' && field === 'holderOverride'){
    state.roles.langeval = value;
    const el = document.getElementById('r-langeval');
    if(el) el.value = value;
  }
  seg[field] = ['durMin','flexMin','flexMax','signalMin','signalMid','signalMax'].includes(field)
    ? (value === '' ? 0 : parseFloat(value)) : value;
  if(['signalMin','signalMid','signalMax'].includes(field)) markSignalsManual(seg);
  else if(field === 'durMin'){
    /* The slot drives the lights here exactly as it does in both panes; the
       open row's own light inputs are then refreshed in place - rebuilding the
       row would destroy the field being typed into. */
    autoSignalsFromSlot(seg);
    syncEditRowInputs(seg);
  }
  if(field === 'speakerName' && seg.isSpeech) mirrorSpeakerToEvaluation(seg);
  /* The speaker's name lives on the SPEECH segment; the evaluation's copy only
     mirrors it. Editing "Evaluating (speaker)" on an evaluation row therefore
     writes back to the paired speech, or the two rows drift apart and the pane
     card (which reads the speech) never hears about the change. */
  if(field === 'speakerName' && seg.isEvaluation){
    const i = evalSegs().findIndex(e=>e.id===seg.id);
    const sp = i>=0 ? speechSegs()[i] : null;
    if(sp) sp.speakerName = value;
  }
  syncSheetMirrors(seg);
  refreshPreviewTimes();
  renderFormPane();
  updateEndCheck();
  queueSave();
}

/* Push slot-derived light values into the OPEN in-sheet edit row (never the
   focused field) - the third editing surface's version of syncCardTimingInputs. */
function syncEditRowInputs(seg){
  const doc = document.getElementById('previewFrame').contentDocument;
  if(!doc) return;
  const row = doc.querySelector('.row-edit');
  if(!row) return;
  [['durMin',seg.durMin],['signalMin',seg.signalMin],['signalMid',midOf(seg)],['signalMax',seg.signalMax]].forEach(([f,v])=>{
    const el = row.querySelector(`input[data-f="${f}"]`);
    if(el && doc.activeElement !== el) el.value = v;
  });
}

/* While an edit row is open the rest of the sheet is static HTML, so rows that
   DERIVE from the one being edited go stale until ✎ Done triggers the full
   rebuild. Two rows do derive: the paired evaluation (its title and holder come
   from the speech) and the paired speech (its POETTS speaker/evaluator lines
   come from the evaluation). Patch exactly those, in place. */
function syncSheetMirrors(seg){
  const doc = document.getElementById('previewFrame').contentDocument;
  if(!doc) return;
  const patchPoetts = (tr, label, name) => {
    const lab = [...tr.querySelectorAll('.poetts .rr-label')]
      .find(l => l.textContent.trim().toUpperCase().startsWith(label));
    if(lab && lab.nextElementSibling)
      lab.nextElementSibling.innerHTML = name ? esc(name) : '<span class="tbd-inline">TBD</span>';
  };
  const patchHolder = (tr, name) => {
    const td = tr.querySelector('td.holder');
    if(td) td.innerHTML = name ? esc(name) : '<span class="tbd">TBD</span>';
  };
  if(seg.isSpeech){
    const i = speechSegs().findIndex(x=>x.id===seg.id);
    const ev = evalSegs()[i];
    if(!ev || ev.id === editingSegId) return;
    const tr = doc.querySelector(`tbody tr[data-seg-id="${ev.id}"]`);
    if(!tr) return;
    const t = tr.querySelector('.item-title');
    if(t) t.textContent = titleFor(ev);
    patchHolder(tr, ev.holderOverride);
  } else if(seg.isEvaluation){
    const i = evalSegs().findIndex(x=>x.id===seg.id);
    const sp = speechSegs()[i];
    if(!sp || sp.id === editingSegId) return;
    const tr = doc.querySelector(`tbody tr[data-seg-id="${sp.id}"]`);
    if(!tr) return;
    patchPoetts(tr, 'SPEAKER', seg.speakerName);
    patchPoetts(tr, 'EVALUATOR', seg.holderOverride);
    patchHolder(tr, sp.holderOverride || sp.speakerName);
  }
}
/* Pathway / level / project inside an edit row: needs a re-render (options change) */
function catalogEdit(id, field, value){
  const seg = state.segments.find(s=>s.id===id);
  if(!seg) return;
  if(field === 'project'){ applyProjectChoice(seg, value); }
  else {
    seg[field] = value;
    if(seg.project && !levelOfProjectIn(seg.pathway, seg.project)) seg.project = '';
  }
  renderFormPane();
  renderPreviewNow();
}

function attachPreviewInteractions(doc){
  let dragRowId = null;
  doc.querySelectorAll('tbody tr[data-seg-id]').forEach(tr=>{
    const grip = tr.querySelector('.drag-grip');
    if(grip) grip.addEventListener('mousedown', ()=> tr.setAttribute('draggable','true'));
    tr.addEventListener('dragstart', (e)=>{
      dragRowId = tr.dataset.segId;
      e.dataTransfer.effectAllowed = 'move';
      try{ e.dataTransfer.setData('text/plain', dragRowId); }catch(_){}
      tr.classList.add('row-dragging');
    });
    tr.addEventListener('dragover', (e)=>{
      if(!dragRowId || tr.dataset.segId === dragRowId) return;
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
      const rect = tr.getBoundingClientRect();
      const below = (e.clientY - rect.top) > rect.height / 2;
      tr.classList.toggle('drop-below', below);
      tr.classList.toggle('drop-above', !below);
    });
    tr.addEventListener('dragleave', ()=> tr.classList.remove('drop-above','drop-below'));
    tr.addEventListener('drop', (e)=>{
      e.preventDefault();
      const below = tr.classList.contains('drop-below');
      tr.classList.remove('drop-above','drop-below');
      if(!dragRowId || tr.dataset.segId === dragRowId) return;
      const from = state.segments.findIndex(s=>s.id===dragRowId);
      if(from < 0) return;
      const [item] = state.segments.splice(from,1);
      const to = state.segments.findIndex(s=>s.id===tr.dataset.segId);
      if(to < 0){ state.segments.splice(from,0,item); return; }
      state.segments.splice(below ? to+1 : to, 0, item);
      dragRowId = null;
      renderFormPane();
      renderPreviewNow();
    });
    tr.addEventListener('dragend', ()=>{
      tr.removeAttribute('draggable');
      dragRowId = null;
      doc.querySelectorAll('.drop-above,.drop-below,.row-dragging').forEach(x=>
        x.classList.remove('drop-above','drop-below','row-dragging'));
    });
  });
}

function updateEndCheck(){
  const {endMin} = computeSchedule();
  const targetMin0 = parseTimeToMin(state.meeting.endTime);
  let targetMin = targetMin0; if(targetMin <= parseTimeToMin(state.meeting.startTime)) targetMin += 1440;
  const el = document.getElementById('endCheck');
  if(endMin === targetMin){
    el.textContent = `Ends ${fmtClock(endMin)} — matches target ${fmtClock(targetMin0)}`;
    el.className = 'end-check ok';
  } else {
    const diff = endMin - targetMin;
    el.textContent = `Ends ${fmtClock(endMin)} — ${diff>0?'+':''}${diff} min vs target ${fmtClock(targetMin0)}`;
    el.className = 'end-check warn';
  }
}

/* ================= Save status ================= */
let baseStatus = 'Saved in this browser';
/* ================= Save indicator =================
   This used to be a text span in the toolbar whose wording changed on every
   autosave ("Autosaving…" -> "Saved ✓" -> back again). The toolbar is a
   flex-wrap row, so each change re-measured and nudged the buttons — Rama was
   getting bumped mid-edit (V21).
   It is now a fixed badge pinned to the top-left, outside the document flow and
   a CONSTANT 26px whatever the state, so nothing on the page can ever move
   because of it. The state lives in colour + a single glyph, and the wording
   moved to the tooltip where it costs no layout. */
function setSaveStatus(text, isWarn, makeBase){
  const el = document.getElementById('saveDot');
  if(makeBase) baseStatus = text;
  /* flashSaved() guarded against this; setSaveStatus did not, so the several
     places that paint a cheerful status directly could still bury a live
     warning under a green tick. */
  if(!isWarn && typeof saveWarning === 'string' && saveWarning) return;
  if(!el) return;
  el.textContent = isWarn ? '!' : '✓';
  el.title = text;
  el.setAttribute('aria-label', text);
  el.classList.toggle('warn', !!isWarn);
}
/* Sticky until something clears it deliberately. flashSaved() used to reset the
   dot to a green tick on the very next keystroke, so every file-save failure -
   permission revoked, disk full, folder gone, file locked - showed for one frame
   and then read as "saved" forever while the file rotted. That was the single
   most dangerous behaviour in the whole save system: the screen disagreeing with
   the disk, confidently. */
let saveWarning = '';
function setSaveWarning(text){
  saveWarning = text || '';
  if(saveWarning) setSaveStatus(saveWarning, true, false);
}
function clearSaveWarning(){
  if(!saveWarning) return;
  saveWarning = '';
  /* Repaint immediately. Clearing the variable alone left the badge showing an
     error that had already been resolved until the user typed again - and a user
     who has just seen a save error is precisely the one who stops typing to
     check. Pessimistic lying is still lying. */
  setSaveStatus(baseStatus || 'Autosaving', false);
}
function flashSaved(){
  const el = document.getElementById('saveDot');
  if(saveWarning) return;                    /* the disk is unhappy; do not lie */
  setSaveStatus('Saved just now · ' + baseStatus, false);
  if(!el) return;
  /* A scale pulse only — transform is composited, so it cannot reflow. */
  el.classList.add('pulse');
  clearTimeout(flashSaved._t);
  flashSaved._t = setTimeout(()=>el.classList.remove('pulse'), 420);
}

/* ================= Save as image =================
   Rendered from the SAME clean sheet the print and download paths use, in an
   offscreen iframe so the builder's own stylesheet cannot leak into it.
   Scale 3 over the 900px sheet gives a 2700px-wide PNG — roughly 300dpi across
   an A4 width, which is what keeps the 9.5px pane type readable. */
const IMAGE_SCALE = 3;
/* Rama shares the sheet on WhatsApp; a 2.6 MB export was unusable. Render big,
   then step DOWN until the JPEG fits this budget. Resolution is dropped before
   quality only when quality alone cannot get there, because on fine type a wider
   image at lower quality still reads better than a small crisp one.
   200 KB (V24) -> 300 KB (V25) -> 450 KB (V26) -> 500 KB (V30, Rama's ceiling for
   all three image/PDF outputs).
   The budget was never the real problem. The ladder tried the WIDEST size first
   and dropped quality to make it fit, so every rise in budget bought more pixels
   at the same grainy quality 0.44 - at 450 KB it went to 2250px and looked no
   cleaner. Grain is bits-per-pixel, not bytes: 5.6 MP at 450 KB is ~0.6 bpp and
   crisp text wants nearer 1.0. So the export is now CAPPED in resolution and the
   budget is spent on quality instead. */
const IMAGE_TARGET_BYTES = 500 * 1024;
/* ~180dpi across an A4 width - past the point where more pixels help a sheet
   that is read on a phone or projected, and the ceiling that lets quality sit at
   0.8+ inside the budget. */
const MAX_EXPORT_WIDTH = 1500;

/* html2canvas is BUNDLED into this file by build_generator.py, not fetched from
   a CDN. Rama exports on whatever wifi the community club has that night, and
   the tool is meant to be one self-contained file — a CDN would have made image
   and PDF export the only features that need the internet.
   (jsPDF used to be bundled too — 364 KB to do one thing, wrap JPEG pages into
   a PDF. pdfFromJpegs() below does that by hand in under 2 KB; V23.) */
function loadHtml2Canvas(){
  return window.html2canvas ? Promise.resolve(window.html2canvas)
                            : Promise.reject(new Error('renderer missing'));
}

/* ================= Minimal PDF writer =================
   A PDF that only ever contains one full-page JPEG per page needs none of a
   general library: a catalog, a page tree, and per page a Page object, a
   one-line content stream that draws the image, and the JPEG itself as a
   DCTDecode XObject (PDFs embed JPEG data as-is). Offsets are byte-exact, so
   this assembles Uint8Array parts rather than strings.
   pages: [{bytes:Uint8Array, pxW, pxH, wPt, hPt, xPt, yPt}] */
function pdfFromJpegs(pages){
  const enc = new TextEncoder();
  const parts = []; const offs = []; let pos = 0;
  const push = x => { const b = (typeof x === 'string') ? enc.encode(x) : x; parts.push(b); pos += b.length; };
  const obj  = txt => { offs.push(pos); push(txt); };

  push('%PDF-1.4\n');
  push(new Uint8Array([0x25, 0xE2, 0xE3, 0xCF, 0xD3, 0x0A]));   /* binary-file marker */

  const kids = pages.map((_, i) => (3 + i*3) + ' 0 R').join(' ');
  obj('1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n');
  obj('2 0 obj\n<< /Type /Pages /Kids [' + kids + '] /Count ' + pages.length + ' >>\nendobj\n');

  pages.forEach((p, i) => {
    const n = 3 + i*3;
    obj(n + ' 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595.28 841.89] '
      + '/Resources << /XObject << /Im0 ' + (n+2) + ' 0 R >> >> /Contents ' + (n+1) + ' 0 R >>\nendobj\n');
    const draw = 'q ' + p.wPt.toFixed(2) + ' 0 0 ' + p.hPt.toFixed(2) + ' '
      + p.xPt.toFixed(2) + ' ' + p.yPt.toFixed(2) + ' cm /Im0 Do Q';
    obj((n+1) + ' 0 obj\n<< /Length ' + draw.length + ' >>\nstream\n' + draw + '\nendstream\nendobj\n');
    offs.push(pos);
    push((n+2) + ' 0 obj\n<< /Type /XObject /Subtype /Image /Width ' + p.pxW + ' /Height ' + p.pxH
      + ' /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length ' + p.bytes.length
      + ' >>\nstream\n');
    push(p.bytes);
    push('\nendstream\nendobj\n');
  });

  const xref = pos;
  push('xref\n0 ' + (offs.length + 1) + '\n0000000000 65535 f \n'
    + offs.map(o => String(o).padStart(10, '0') + ' 00000 n \n').join(''));
  push('trailer\n<< /Size ' + (offs.length + 1) + ' /Root 1 0 R >>\nstartxref\n' + xref + '\n%%EOF');

  return new Blob(parts, {type: 'application/pdf'});
}

/* iOS Safari silently ignores print() called on a hidden iframe — the button
   looked dead on Rama's iPhone (V21). There is no feature test for it, so this
   goes on the user agent. Modern iPads report as Macintosh, hence the touch
   check alongside it. */
const IS_TOUCH_DEVICE = (function(){
  const ua = navigator.userAgent || '';
  const iOS = /iPad|iPhone|iPod/.test(ua) || (/Macintosh/.test(ua) && (navigator.maxTouchPoints||0) > 1);
  return iOS || /Android/i.test(ua);
})();

/* Every download carries the same name as the saved meeting (V30). */
function sheetFileStem(){
  return fileBaseName() || 'programme-sheet';
}

/* ================= Rasterising the sheet (V32) =================
   The exports used to rasterise the SCREEN layout, which is a DIFFERENT DESIGN
   from the printed one, and two of Rama's complaints were the same bug wearing
   two hats:
     - on screen the banner runs the full width and the pane's brand box sits
       BELOW it, so the Toastmasters logo appeared under the masthead in every
       JPG and PDF. On paper the header is inset by the pane width and the brand
       box fills the corner beside it, and the two read as one band. Six versions
       went into that band; the exports never showed it.
     - on screen the pane is an ordinary grid column whose content stops where it
       stops, so slicing that canvas into pages left an empty column on page 2.
       V30 papered over it by repainting the same pane on every page, which is
       what print does but not what Rama wants: he wants it to CONTINUE.
   So the export now renders the print layout instead of imitating it. The print
   rules are not re-declared - they are retargeted in place through the CSSOM,
   every @media print rule set to media "all", so the measurement can never drift
   away from what actually prints. The frame is sized to the A4 content box so
   the millimetre values in that stylesheet mean what they say.
   Two print rules must then be undone, because they are written for a paginated
   medium that a single tall canvas does not have: the pane is position:fixed so
   it repeats per page, and the footer likewise. Both become absolute inside the
   page, and the pane's overflow:hidden comes off so it flows past page one. */
const PRINT_W_MM = 190, PRINT_H_MM = 277;      /* A4 less the sheet's own 1 cm margins */
const PX_PER_MM  = 96 / 25.4;
const PRINT_W_PX = Math.round(PRINT_W_MM * PX_PER_MM);   /* 718 */
const PRINT_H_PX = PRINT_H_MM * PX_PER_MM;               /* 1047.2 */
const MAX_CANVAS_PX = 30000;   /* well inside every browser's single-axis limit */

/* Lift every @media print rule out and hand it back as plain CSS text.
   The first attempt retargeted the rules in place (r.media.mediaText = 'all'),
   which is neat and works for measuring - but html2canvas does not rasterise the
   live DOM. It CLONES it, and it clones the <style> NODES, so the clone re-parses
   the original source text and the mutation is invisible to it. The result was a
   canvas laid out to the SCREEN rules while every measurement said print: the
   masthead lost the club's name and the meta row wrapped to four lines.
   Re-emitting the rules as a real stylesheet is what survives the clone. */
function printRulesText(idoc){
  const out = [];
  for(const sheet of Array.from(idoc.styleSheets)){
    let rules;
    try{ rules = sheet.cssRules; }catch(e){ continue; }   /* cross-origin, skip */
    if(!rules) continue;
    for(const r of Array.from(rules)){
      if(r.type === 4 /* CSSRule.MEDIA_RULE */ && /print/i.test(r.conditionText || '')){
        for(const inner of Array.from(r.cssRules || [])) out.push(inner.cssText);
      }
    }
  }
  return out.join('\n');
}

async function renderSheetCanvas(){
  return (await renderSheetParts()).canvas;
}
/* opts.paginate: pad the sheet to a whole number of A4 pages, so the last page
   runs to the bottom of the paper instead of stopping where the agenda stops -
   and the pane column runs down with it. Only the PDF wants that; a single JPG
   would just gain a band of white. */
async function renderSheetParts(opts){
  const paginate = !!(opts && opts.paginate);
  const h2c = await loadHtml2Canvas();
  let frame = null;
  try{
    frame = document.createElement('iframe');
    frame.setAttribute('aria-hidden','true');
    frame.style.cssText = 'position:fixed;left:-10000px;top:0;border:0;visibility:hidden;'
      + 'width:' + PRINT_W_PX + 'px;height:' + Math.ceil(PRINT_H_PX) + 'px;';
    document.body.appendChild(frame);

    /* srcdoc (not document.write) so there is a real load event to wait on. */
    await new Promise((res, rej)=>{
      frame.onload = res;
      frame.onerror = ()=>rej(new Error('frame'));
      frame.srcdoc = buildSheetHTML(false);
    });

    const idoc = frame.contentDocument;
    const printCss = idoc.createElement('style');
    printCss.textContent = printRulesText(idoc);
    idoc.head.appendChild(printCss);

    const fix = idoc.createElement('style');
    fix.textContent =
        'html,body{background:#fff!important;margin:0!important;padding:0!important}'
      + '.page-wrap{padding:0!important;display:block!important}'
      + '.page{box-shadow:none!important;border-radius:0!important;max-width:none!important;'
        + 'width:100%!important;position:relative!important;overflow:visible!important}'
      /* Un-fix the pane: absolute inside the page, natural height, no clipping,
         so it simply carries on down the sheet and across the page break. */
      /* column-count/columns forced back to auto: an aside that is a multi-column
         context fragments an over-tall .pane-body into an overflow column to the
         RIGHT, and html2canvas paints element borders on the UNION of an element's
         fragments - which is what drew a 1px line down the middle of every export.
         The sheet CSS no longer sets column-count, but a sheet DOWNLOADED from an
         older build carries its own copy of that stylesheet, so the export pins it
         here too. */
      + 'aside.ref-pane{position:absolute!important;top:0!important;left:0!important;'
        + 'right:auto!important;height:auto!important;overflow:visible!important;'
        + 'column-count:auto!important;columns:auto!important}'
      /* Same for the footer, which print pins to the bottom of every page. */
      + 'footer{position:absolute!important;left:0!important;right:0!important;'
        + 'bottom:0!important;top:auto!important}'
      /* The pane is out of flow and free-height now, so the print rule that sizes
         .pane-body to "the page less the brand box" no longer means anything. */
      + '.pane-body{height:auto!important;min-height:calc(100% - var(--print-head))!important}'
      /* The brand box is resized below to match whatever height the banner needs,
         and the sheet pins the logo to height:100% - so a tall banner stretched
         the globe into an egg, which is the V26 squash defect arriving from the
         other side. Sizing by neither axis, with a ceiling on both, keeps the
         artwork's own aspect whatever the box does. html2canvas has no object-fit
         to fall back on. */
      + '.pane-brand img{height:auto!important;width:auto!important;'
        + 'max-height:calc(100% - 4px)!important;max-width:100%!important}'
      + '.print-fab{display:none!important}'
      /* Images and the PDF are deliverables like print, so they follow the print
         rule and drop the FLEXIBLE explainer too. It stays on the live preview,
         which is where it actually helps. */
      + '.schedule-note{display:none!important}';
    idoc.head.appendChild(fix);

    /* Webfonts must be in before rasterising or the type falls back to Arial. */
    if(idoc.fonts && idoc.fonts.ready){
      await Promise.race([idoc.fonts.ready, new Promise(r=>setTimeout(r, 4000))]);
    }
    await new Promise(r=>setTimeout(r, 120));

    const page = idoc.querySelector('.page');
    const aside = idoc.querySelector('aside');
    const foot = idoc.querySelector('footer');

    /* The banner and the brand box are a FIXED --print-head tall with
       overflow:hidden, and the banner's content has quietly outgrown that box -
       measured at 126-129px against 125px in every theme, and worse once the
       venue address wraps. On paper that costs a hairline off the top. Through
       html2canvas it cost the club's NAME: the clone lays the flex content out a
       little taller still, centring pushes the first line above the box, and the
       masthead printed starting at the district line.
       Rama prints the downloaded PDF, so the PDF is the paper. Rather than clip
       it, let the banner take the height it needs and give the brand box beside
       it exactly the same number, which is the whole point of that band. */
    const hdr = idoc.querySelector('header');
    const brand = idoc.querySelector('.pane-brand');
    if(hdr){
      hdr.style.height = 'auto';
      hdr.style.overflow = 'visible';
      if(brand) brand.style.height = 'auto';
      await new Promise(r=>setTimeout(r, 30));
      const hh = Math.ceil(hdr.getBoundingClientRect().height) + 1;   /* +1 for the flex rounding */
      hdr.style.height = hh + 'px';
      if(brand) brand.style.height = hh + 'px';
      /* And size the pane body against the REAL banner height, not the constant.
         .pane-body is 'calc(100% - var(--print-head))' and --print-head is a fixed
         33mm = 124.7px, but the brand box above it has just been set to hh - 142px
         with a meeting title, 118px without. With a title the pane body therefore
         ran 17px past the bottom of the aside, which is what made it overflow, and
         the overflow is what produced the line (see the column-count note in the
         sheet CSS). Measured: bottom 2086.3 against the aside's 2069.4 with a
         title, 2062.3 without - which is exactly why typing one character in the
         Meeting Title field turned the line on. */
      /* setProperty with 'important', not style.minHeight: the fix stylesheet a
         few lines up declares .pane-body{min-height:...!important}, and a plain
         inline style LOSES to an !important declaration. The first version of this
         set it the easy way and the pane body still ran 17px past the aside. */
      const paneBody = idoc.querySelector('.pane-body');
      if(paneBody) paneBody.style.setProperty('min-height', 'calc(100% - ' + hh + 'px)', 'important');
      await new Promise(r=>setTimeout(r, 30));
    }

    /* How tall the sheet actually is. The pane is out of flow now, so a pane
       longer than the agenda would otherwise be cut off at the agenda's end. */
    const natural = ()=>{
      let h = page.scrollHeight;
      if(aside) h = Math.max(h, aside.offsetTop + aside.scrollHeight
        + (foot ? foot.offsetHeight : 0));
      return Math.ceil(h);
    };
    let h = natural();
    let pages = 1;
    if(paginate){
      /* Real pagination, not a blind cut every 277mm. Paper honours
         break-inside:avoid on a row; a canvas sliced at fixed offsets does not,
         so the first row of page two used to arrive sawn in half. Walk down the
         table and, wherever a row straddles a page boundary, push it over with a
         spacer row of exactly the leftover height. Every page then ends on a row
         edge AND is a full page tall, which is what lets the pane column and its
         rule run to the bottom of each one. */
      const rows = Array.from(idoc.querySelectorAll('tbody tr'));
      const topOf = ()=> page.getBoundingClientRect().top;
      /* Paginate to the top of the FOOTER BAND, not to the paper edge. The footer
         is stamped onto every page above the last, and it is opaque, so anything
         that merely ends inside that band never counted as straddling and was
         quietly painted over - it did not reappear overleaf, it was destroyed.
         A whole announcement went missing that way at nearly every page break. */
      const footH = foot ? Math.ceil(foot.getBoundingClientRect().height) : 0;
      const straddles = (el, edge)=>{
        const b = el.getBoundingClientRect(), pt = topOf();
        return (b.bottom - pt) > edge - footH + 0.5 && (b.top - pt) < edge - 0.5;
      };
      let boundary = PRINT_H_PX, guard = 0;
      while(guard++ < 60){
        const pt = topOf();
        if(boundary - footH >= natural()) break;
        const hit = rows.find(r => straddles(r, boundary));
        if(!hit){ boundary += PRINT_H_PX; continue; }
        const b = hit.getBoundingClientRect();
        const gap = boundary - (b.top - pt);
        /* A row taller than a page cannot be rescued; leave it and move on. */
        if(gap <= 0.5 || b.height > PRINT_H_PX){ boundary += PRINT_H_PX; continue; }
        const sp = idoc.createElement('tr');
        sp.className = 'pg-spacer';
        const td = idoc.createElement('td');
        td.setAttribute('colspan', String(Math.max(1, hit.children.length)));
        td.style.cssText = 'height:' + gap + 'px;padding:0;border:none;background:transparent';
        sp.appendChild(td);
        hit.parentNode.insertBefore(sp, hit);
        await new Promise(r=>setTimeout(r, 0));
        boundary += PRINT_H_PX;
      }
      /* The pane needs the same treatment. It is one long column of small blocks
         now that it flows across the break, and a fixed cut lands mid-sentence -
         the first thing on page two was the tail of an announcement. These are
         ordinary blocks, so a margin is enough to push one over. */
      const paneBlocks = Array.from(idoc.querySelectorAll(
        'aside h3, aside .exco-item, aside .announce-line, aside .path-legend div'));
      boundary = PRINT_H_PX; guard = 0;
      while(guard++ < 60){
        const pt = topOf();
        if(boundary - footH >= natural()) break;
        const hit = paneBlocks.find(el => straddles(el, boundary));
        if(!hit){ boundary += PRINT_H_PX; continue; }
        const b = hit.getBoundingClientRect();
        const gap = boundary - (b.top - pt);
        if(gap <= 0.5 || b.height > PRINT_H_PX){ boundary += PRINT_H_PX; continue; }
        /* A spacer element, not margin-top: adjacent margins COLLAPSE, so adding
           the gap to the margin moved the block by gap minus the previous
           block's margin-bottom and left it still straddling by those 2px. */
        const sp = idoc.createElement('div');
        sp.className = 'pg-spacer';
        sp.style.cssText = 'height:' + gap + 'px;margin:0;padding:0;border:0';
        hit.parentNode.insertBefore(sp, hit);
        await new Promise(r=>setTimeout(r, 0));
        /* Re-check the same boundary once: pushing one block can leave the next
           one straddling if the first was short. */
        const again = hit.getBoundingClientRect();
        if((again.top - topOf()) < boundary - 0.5) continue;
        boundary += PRINT_H_PX;
      }

      h = natural();
      pages = Math.max(1, Math.ceil((h - 1) / PRINT_H_PX));
      h = Math.round(pages * PRINT_H_PX);
      page.style.minHeight = h + 'px';
      await new Promise(r=>setTimeout(r, 60));
    }
    /* The pane fills the sheet less the footer strip, so its background and its
       column rule run all the way to the bottom of the last page. */
    if(aside){
      aside.style.bottom = (foot ? foot.offsetHeight : 0) + 'px';
      aside.style.height = 'auto';
      await new Promise(r=>setTimeout(r, 30));
    }
    frame.style.height = (h + 40) + 'px';
    await new Promise(r=>setTimeout(r, 60));

    /* Browsers cap a canvas at 65535px in one dimension and lower on total area.
       At scale 3 a sheet past about 21 pages crossed it, and html2canvas handed
       back a canvas that was simply blank - every page came out empty with only
       the stamped footer on it, and the app reported success. Drop the scale
       rather than ship 23 blank pages, and refuse outright if even 1x will not
       fit. Nobody has a legitimate 30-page programme sheet; the point is that it
       fails loudly. */
    let scale = IMAGE_SCALE;
    while(scale > 1 && h * scale > MAX_CANVAS_PX) scale--;
    if(h * scale > MAX_CANVAS_PX){
      throw new Error('sheet is too long to render (' + Math.round(h / PRINT_H_PX) + ' pages)');
    }
    /* Hand html2canvas a canvas whose 2D context we have already claimed with
       willReadFrequently, so every draw call it makes lands in Skia's CPU backing
       store instead of a GPU texture (V37).
       Why this and not just the downscale: V37's first attempt moved only the
       downscale and page-slicing contexts, and Rama's line survived it. It would:
       html2canvas creates its OWN canvas - `A.canvas = e.canvas || createElement`
       in the bundle - and that is the surface every element rect and glyph is
       drawn onto. It was still GPU-backed.
       The mechanism this targets, measured from his export: a 2px line at a
       constant x, running 100% of the page height through the banner, the notice
       bar and the agenda alike, in a sheet whose DOM is byte-for-byte identical to
       one that renders clean here (same MD5), and which Chrome's own print engine
       renders clean on his machine. Nothing in the document draws it.
       getContext is idempotent in its attributes: the first call fixes them, so
       claiming it here means the library's later plain getContext('2d') returns
       this same CPU-backed context. Sizing is ours too - the bundle only sets
       width/height when it created the canvas itself. */
    const target = document.createElement('canvas');
    target.width = Math.floor(PRINT_W_PX * scale);
    target.height = Math.floor(h * scale);
    target.getContext('2d', CTX2D);
    const canvas = await h2c(page, {
      canvas: target,
      scale: scale,
      backgroundColor: '#ffffff',
      useCORS: true,
      logging: false,
      width: PRINT_W_PX,
      height: h,
      windowWidth: PRINT_W_PX,
      windowHeight: h,
    });

    /* Print puts the footer on every page. The canvas can only hold it once, so
       the PDF gets it as a strip to stamp onto the pages above the last. */
    let footStrip = null;
    if(paginate && foot && pages > 1){
      const fb = foot.getBoundingClientRect();
      const fstrip = document.createElement('canvas');
      fstrip.width = Math.floor(Math.ceil(fb.width) * scale);
      fstrip.height = Math.floor(Math.ceil(fb.height) * scale);
      fstrip.getContext('2d', CTX2D);
      footStrip = await h2c(foot, {
        canvas: fstrip,
        scale: scale,
        backgroundColor: '#ffffff',
        useCORS: true,
        logging: false,
        width: Math.ceil(fb.width),
        height: Math.ceil(fb.height),
        windowWidth: PRINT_W_PX,
        windowHeight: h,
      });
    }
    return {canvas, pages, footStrip};
  }finally{
    if(frame) frame.remove();
  }
}

/* CPU raster, deliberately (V37).
   Rama's exports carry a 2px translucent vertical line down the WHOLE page - over
   the banner, the table head and the paper alike - at a constant x on every page,
   in both the PDF and the JPG. It is not in the layout: every element that spans
   the full height of the export was enumerated (html, body, .page-wrap, .page,
   .body-grid, main, table, tbody, aside.ref-pane, .pane-body) and none has an edge
   anywhere near it, and nothing in the DOM spans the banner AND the agenda. It
   never reproduces here, under software rasterisation, across his exact content,
   real webfonts, and device scale factors 1 to 2.
   That combination is the signature of a GPU tile seam: the sheet is one canvas of
   2154 x ~6300 px, and a high-quality downscale of a texture that large is done
   per tile, so a sub-pixel disagreement at a tile boundary paints a hairline the
   full height of the image.
   willReadFrequently moves the canvas to Skia's CPU backing store, which has no
   tiles. It costs nothing here: these contexts are written once and immediately
   read back by toBlob, which is exactly the access pattern the flag describes. */
const CTX2D = { willReadFrequently: true };
/* Stepwise halving beats one big jump — a single drawImage down to 45% aliases
   the 9.5px pane type into mush, three gentle steps do not. */
function downscaleCanvas(src, targetW){
  let cur = src;
  while(cur.width > targetW * 2){
    const c = document.createElement('canvas');
    c.width = Math.max(targetW, Math.round(cur.width / 2));
    c.height = Math.round(cur.height * (c.width / cur.width));
    const x = c.getContext('2d', CTX2D);
    x.imageSmoothingEnabled = true; x.imageSmoothingQuality = 'high';
    x.drawImage(cur, 0, 0, c.width, c.height);
    cur = c;
  }
  if(cur.width === targetW) return cur;
  const c = document.createElement('canvas');
  c.width = targetW;
  c.height = Math.round(cur.height * (targetW / cur.width));
  const x = c.getContext('2d', CTX2D);
  x.imageSmoothingEnabled = true; x.imageSmoothingQuality = 'high';
  x.fillStyle = '#ffffff'; x.fillRect(0, 0, c.width, c.height);
  x.drawImage(cur, 0, 0, c.width, c.height);
  return c;
}

/* Returns the LARGEST encoding that fits the budget, or the smallest we can make
   if nothing does — never silently ships something enormous. */
async function encodeJpegUnder(canvas, target){
  /* Capped, and quality-first within each width: the first fit at the widest
     allowed size is the HIGHEST quality that fits there, not the lowest.
     Aim 1% under the budget rather than at it (V37). "The first size that fits"
     can fit by 320 bytes, and then any later change that adds a line to the sheet
     ships an over-cap file. Stepping one quality notch down when the top notch
     only just squeaks in costs nothing visible and keeps real headroom. */
  target = Math.floor(target * 0.99);
  const widths = [MAX_EXPORT_WIDTH, 1400, 1300, 1200, 1050].filter(w => w <= canvas.width);
  const qualities = [0.88, 0.84, 0.80, 0.76, 0.70, 0.62, 0.55];
  let last = null;
  for(const w of widths){
    if(w > canvas.width) continue;
    const c = (w === canvas.width) ? canvas : downscaleCanvas(canvas, w);
    for(const q of qualities){
      const blob = await new Promise(r => c.toBlob(r, 'image/jpeg', q));
      if(!blob) continue;
      last = {blob, w: c.width, h: c.height, q};
      if(blob.size <= target) return last;
    }
  }
  return last;
}

function saveBlob(blob, name){
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  /* iOS ignores the download attribute for some types; opening in a tab at
     least gets the user to Share → Save to Files. On desktop a plain download
     is cleaner, and target=_blank there can trip popup blocking. */
  if(IS_TOUCH_DEVICE){ a.target = '_blank'; a.rel = 'noopener'; }
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(()=>URL.revokeObjectURL(url), 4000);
}

function busyBtn(on){
  ['dlBtn','dlBtnM'].forEach(id=>{
    const btn = document.getElementById(id);
    if(!btn) return;
    if(on){
      btn.disabled = true;
      btn.dataset.label = btn.dataset.label || btn.textContent;
      btn.textContent = '⏳';
    } else {
      btn.disabled = false;
      btn.textContent = btn.dataset.label || '⭳';
    }
  });
}

function exportFailed(err, alt){
  showBanner('Could not build the file (' + ((err && err.message) || 'unknown') + '). ' + alt, true);
}

/* JPG is the only image format offered (V31). PNG arrived in V30 and is gone
   again: lossless cannot reach the 500 KB cap on a full sheet at any width where
   the 9.5px pane type is still readable, so it always shipped at about 680 KB
   with an apology attached. One image format that always honours the cap beats
   two where one of them does not. */
async function downloadImage(){
  busyBtn(true);
  try{
    const canvas = await renderSheetCanvas();
    const out = await encodeJpegUnder(canvas, IMAGE_TARGET_BYTES);
    if(!out) throw new Error('encode');
    saveBlob(out.blob, sheetFileStem() + '.jpg');
    const kb = Math.round(out.blob.size / 1024);
    const over = out.blob.size > IMAGE_TARGET_BYTES;
    showBanner('Saved a ' + out.w + '\u00d7' + out.h + ' JPG (' + kb + ' KB).'
      + (over ? ' That is over the 500 KB cap \u2014 the sheet is unusually long this week.' : ''), over);
  }catch(err){
    exportFailed(err, 'the HTML download still works.');
  }finally{ busyBtn(false); }
}

/* ================= PDF =================
   Built in the page on every device. Since V29 nothing routes through the print
   dialog at all: its destination setting silently decided the file size, and
   "Microsoft Print to PDF" rasterised every page at 300dpi for 1.4 MB.
   Since V32 the canvas it slices is already the PRINT layout, padded to a whole
   number of A4 pages, so slicing is now a straight cut every PRINT_H_MM with no
   compositing: the pane runs down the left across the break, the banner and the
   brand box sit together at the top of page one, and the last page runs to the
   bottom of the paper. The only thing stamped on is the footer, which paper
   repeats per page and a single canvas can hold only once. */
async function downloadPdfImage(){
  busyBtn(true);
  try{
    /* Same resolution cap as the JPG export. Uncapped this embedded 2100px
       slices at q0.9 - over a megabyte for two A4 pages. */
    const parts = await renderSheetParts({paginate:true});
    const full = parts.canvas;
    const canvas = full.width > MAX_EXPORT_WIDTH ? downscaleCanvas(full, MAX_EXPORT_WIDTH) : full;
    /* Derived from the page count rather than from the point maths, so the cut
       lands exactly where the layout was padded to. */
    const M_PT = 10 * 72/25.4, PW_PT = 595.28, PH_PT = 841.89;
    const imgWpt = PW_PT - M_PT*2;
    /* Slice height comes from the page GEOMETRY, not from canvas.height / pages:
       html2canvas rounds its output height up - 2108 CSS px for a 2094 px sheet -
       and dividing that by the page count pushed the cut past the boundary the
       layout was paginated to, slicing the first line of page two in half. */
    const cut = document.createElement('canvas');
    const ctx = cut.getContext('2d', CTX2D);
    const buildAt = async (src, strip, q)=>{
      const sliceH = src.width * (PRINT_H_MM / PRINT_W_MM);
      const pxPerPt = src.width / imgWpt;
      const count = Math.max(1, Math.min(parts.pages || 1,
        Math.ceil((src.height - 2) / sliceH)));
      const pages = [];
      for(let i = 0; i < count; i++){
        const y = Math.round(i * sliceH);
        const h = Math.min(Math.round(sliceH), src.height - y);
        if(h <= 0) break;
        cut.width = src.width; cut.height = h;
        ctx.fillStyle = '#ffffff'; ctx.fillRect(0, 0, cut.width, cut.height);
        ctx.drawImage(src, 0, y, src.width, h, 0, 0, src.width, h);
        if(strip && i < count - 1){
          ctx.drawImage(strip, 0, h - strip.height, strip.width, strip.height);
        }
        const blob = await new Promise(r => cut.toBlob(r, 'image/jpeg', q));
        if(!blob) throw new Error('encode');
        const hPt = h / pxPerPt;
        pages.push({ bytes: new Uint8Array(await blob.arrayBuffer()),
                     pxW: cut.width, pxH: h,
                     wPt: imgWpt, hPt, xPt: M_PT, yPt: PH_PT - M_PT - hPt });
      }
      return {pages, blob: pdfFromJpegs(pages)};
    };
    /* Quality first, then resolution. Two pages always fit on the first rung, so
       the middle rungs only ever run on a long sheet - and a three-page sheet
       exhausted the whole ladder and still shipped over the cap, because the
       print layout fills every page edge to edge and carries more ink per page
       than the old screen-layout render did. Dropping the width is what finally
       gets there; 1150px is still around 150dpi across an A4 width. */
    let out = null;
    outer:
    for(const w of [canvas.width, 1300, 1150, 1000]){
      if(w > canvas.width) continue;
      const src = (w === canvas.width) ? canvas : downscaleCanvas(canvas, w);
      const strip = (parts.footStrip && parts.footStrip.width !== src.width)
        ? downscaleCanvas(parts.footStrip,
            Math.max(1, Math.round(parts.footStrip.width * (src.width / full.width))))
        : parts.footStrip;
      for(const q of [0.78, 0.72, 0.66, 0.58, 0.50, 0.44]){
        out = await buildAt(src, strip, q);
        /* 1% under the cap, not at it (V37). The PDF ladder has its own loop and
           was left behind when encodeJpegUnder gained the same margin. "The first
           rung that fits" fitted by 320 bytes on a long sheet, so the very next
           change that adds a line to the agenda would have shipped an over-cap
           file - and the banner would then have told Rama his meeting was
           "unusually long this week" when all that happened was a tighter
           typeface. One quality notch buys the margin back and is invisible. */
        if(out.blob.size <= IMAGE_TARGET_BYTES * 0.99) break outer;
      }
    }
    saveBlob(out.blob, sheetFileStem() + '.pdf');
    const kb = Math.round(out.blob.size / 1024);
    const over = out.blob.size > IMAGE_TARGET_BYTES;
    showBanner('Saved as a ' + out.pages.length + '-page A4 PDF (' + kb + ' KB).'
      + (over ? ' That is over the 500 KB cap — the sheet is unusually long this week.' : ''), over);
  }catch(err){
    /* Not "try the JPG": the JPG goes through the same renderer and fails the
       same way, which is exactly the case that raises this. */
    exportFailed(err, 'Shorten the announcements, or download the HTML and print that.');
  }finally{ busyBtn(false); }
}

/* ================= Meeting files on disk (V28) =================
   Rama wanted Save to put a .json beside the app, then keep autosaving into it,
   with a dropdown of previous meetings to load.

   A file:// page cannot simply write next to itself - nothing in the web
   platform grants that. What it CAN do, in Chrome and Edge, is the File System
   Access API: the user picks the folder ONCE, the browser hands back a
   directory handle, and that handle is stored in IndexedDB so it survives a
   reload. Permission must be re-confirmed from a user gesture after a restart,
   which is why "Reconnect folder" exists in the dropdown.

   Safari and Firefox have no such API. There the same two buttons degrade to a
   plain download and a file picker - the data format is identical, so meetings
   move between browsers untouched.

   Everything below talks only to the STANDARD handle interface
   (getFileHandle / createWritable / entries / queryPermission), so the tests
   drive it with an in-memory fake directory instead of a real folder. */
const FILE_EXT   = '.nse.json';
const IDB_NAME   = 'nse-progsheet-fs', IDB_STORE = 'handles', IDB_FOLDER_KEY = 'folder';
/* The FILE as well as the folder (V35). Only the folder was persisted, so every
   reload silently detached the meeting - the badge still said "autosaving" while
   every edit went to localStorage alone and the file kept yesterday's content.
   Pressing Save the next morning then re-stamped the auto name with the current
   time and made a SECOND file, leaving the folder with no way to tell which was
   real. */
const IDB_FILE_KEY = 'file';
const FS_SUPPORTED = typeof window.showDirectoryPicker === 'function';

let folderHandle = null;    /* FileSystemDirectoryHandle for the meetings folder */
let fileHandle   = null;    /* the meeting we are autosaving into */
let fileSaveTimer = null;

/* --- tiny IndexedDB kv, just for the folder handle --- */
function idbOpen(){
  return new Promise((res, rej)=>{
    const r = indexedDB.open(IDB_NAME, 1);
    r.onupgradeneeded = ()=> r.result.createObjectStore(IDB_STORE);
    r.onsuccess = ()=> res(r.result);
    r.onerror = ()=> rej(r.error);
  });
}
async function idbGet(key){
  try{
    const db = await idbOpen();
    return await new Promise((res, rej)=>{
      const t = db.transaction(IDB_STORE, 'readonly').objectStore(IDB_STORE).get(key);
      t.onsuccess = ()=> res(t.result || null); t.onerror = ()=> rej(t.error);
    });
  }catch(e){ return null; }
}
async function idbSet(key, val){
  try{
    const db = await idbOpen();
    await new Promise((res, rej)=>{
      const t = db.transaction(IDB_STORE, 'readwrite').objectStore(IDB_STORE).put(val, key);
      t.onsuccess = res; t.onerror = ()=> rej(t.error);
    });
    return true;
  }catch(e){ return false; }   /* memory-only for this session; still usable */
}

/* --- payload + naming --- */
/* Who this tab is, for the lifetime of this page. Two tabs on one folder is the
   case the savedAt stamp cannot resolve: both write ISO timestamps, both look
   plausible, and on a synced folder the clock is not even the same clock. An
   identity plus a counter turns "these two files differ" into a statement about
   WHICH ONE IS OLDER, which is the only thing worth acting on. */
/* sessionStorage, not a fresh id per load. sessionStorage is scoped to the TAB and
   survives a reload, which is exactly the identity we want: reloading the page
   after a stalled save is the obvious thing to do, and with a fresh id the write
   that then lands looks like a different tab's - 'other' instead of 'ours-late' -
   and jams the autosave for the session while blaming a tab that does not exist.
   Padded to a fixed width so it cannot come out short: Math.random() can produce
   '0.5', and the id is the only thing standing between 'ours-late' and adopting a
   stranger's write. */
const TAB_ID = (function(){
  const mint = ()=> 'tab-' + (Math.random().toString(36).slice(2) + '0000000000').slice(0, 10);
  try{
    const held = sessionStorage.getItem('nse-ps-tab');
    if(held) return held;
    const made = mint();
    sessionStorage.setItem('nse-ps-tab', made);
    return made;
  }catch(e){ return mint(); }        /* private mode, or storage off */
})();
/* file name -> the writeId this tab last VERIFIED on disk for that file. Per file
   for the same reason the baseline is: one shared counter across two open
   meetings makes every cross-file comparison a lie. */
let writeIdByFile = {};
/* The ALLOCATION counter, separate from the verified one above. A write that fails
   - short write, permission lapse, OneDrive pausing mid-commit - must still burn
   its number, or the next write reuses it over different bytes and two distinct
   payloads carry the same id. classifyDisk compares with a strict <, so a rollback
   between those two is then invisible: exactly the case the counter exists for.
   Allocate from here, promote to writeIdByFile only after the read-back agrees. */
let writeIdNext = (function(){
  try{ return JSON.parse(sessionStorage.getItem('nse-ps-writeid') || '{}') || {}; }
  catch(e){ return {}; }
})();
function persistWriteIds(){
  try{ sessionStorage.setItem('nse-ps-writeid', JSON.stringify(writeIdNext)); }catch(e){}
}
/* The savedAt of the newest payload this tab wrote or read for a file. The counter
   cannot see a rollback to a file that has no counter in it - every meeting saved
   by V35 and earlier, every hand edit, every restore from a backup - and during
   the changeover that is the LIKELIEST rollback there is. The timestamp is the
   weaker signal and it is the only one those files carry. */
let lastSavedAtByFile = {};
/* How far two machines on one synced folder can disagree about the time before it
   means anything. Deliberately large: this number only gates a "look at this"
   message, so being generous costs a missed warning and being tight costs a false
   accusation of rollback against work that is real. */
const CLOCK_SKEW_MS = 5 * 60 * 1000;
/* file name -> {text, writeId, at} of the last content this tab either wrote and
   verified, or read and parsed cleanly. This is what "restore the last good
   version" restores. Deliberately in memory only: a copy in localStorage would
   be a third writer to reconcile, and the whole point is to have one thing we
   are certain about. Capped, because a long session can open many meetings. */
let lastGood = {};
const LAST_GOOD_MAX = 8;
function rememberGood(name, text, writeId, savedAt){
  if(!name || !text) return;
  /* Drop the oldest, but NEVER the file we are attached to. `at` only moves on a
     SUCCESSFUL write or a clean read, so the one file whose writes are currently
     failing - the only file the recovery offer exists for - ages fastest and was
     first out of the door after eight other meetings had been opened. */
  const open = openFileName();
  const keys = Object.keys(lastGood).filter(k => k !== open && k !== name);
  if(Object.keys(lastGood).length >= LAST_GOOD_MAX && !lastGood[name] && keys.length){
    let oldest = keys[0];
    keys.forEach(k => { if(lastGood[k].at < lastGood[oldest].at) oldest = k; });
    delete lastGood[oldest];
  }
  lastGood[name] = { text: text, writeId: writeId || 0,
                     savedAt: savedAt || (readMeta(text) || {}).savedAt || 0, at: Date.now() };
}
function meetingPayload(){
  /* writeId is emitted as 0 and stamped by enqueueWrite from inside the write
     chain - see the note there. A download has no file and no sequence, so 0 is
     the honest value for it. */
  return JSON.stringify({app:'nse-programme-sheet', v:PAYLOAD_VERSION,
    savedAt:new Date().toISOString(), writeId:0, writer:TAB_ID, state}, null, 2);
}
/* String surgery rather than parse-and-reserialise: the payload is ours, the
   field is at a known place, and reserialising a 20 KB document on every
   keystroke's autosave to change one integer is work for nothing.
   Safe against a meeting whose text contains the literal characters
   "writeId": 7 - inside state those quotes are escaped as \\", so the pattern
   below cannot match them. Non-global: the first occurrence is the real one,
   because writeId is emitted before state. */
function stampWriteId(text, id){
  return text.replace(/("writeId":\s*)\d+/, '$1' + id);
}
function readMeta(text){
  try{
    const o = JSON.parse(text);
    if(!o || typeof o !== 'object') return null;
    return { writeId: Number(o.writeId) || 0, writer: (typeof o.writer === 'string' ? o.writer : ''),
             savedAt: Date.parse(o.savedAt) || 0 };
  }catch(e){ return null; }
}
/* What is that text on disk, relative to what we last put there?
     'same'    - byte-identical to our baseline, nothing to say
     'damaged' - not readable JSON, or not a meeting: half-synced, torn, or edited
     'stale'   - readable, but carries a writeId OLDER than one we verified. Only
                 a second writer or a sync rollback produces this, and it is the
                 case a timestamp comparison silently gets wrong.
     'other'   - readable and newer, written by a different tab
     'changed' - readable and different, provenance unknown (a V35 file, a hand
                 edit, a restore from backup) */
/* A file we have just read and parsed cleanly IS a good version, and its writeId
   is the floor for anything we write next. Without the floor, opening a meeting a
   second tab has advanced to id 12 and then saving it as our id 3 looks, to that
   other tab, exactly like a sync rollback - the alarm fires on the one case where
   the user did everything right. */
/* provenanceOnly: take the counters, refuse the content. Used by Save As, where
   the user has just confirmed "the meeting currently in that file will be lost" -
   holding it as the last good copy meant a failed write left the recovery bar
   offering back the very meeting they authorised destroying. */
function adoptDiskProvenance(name, text, provenanceOnly){
  if(!name || !text) return;
  const meta = readMeta(text);
  if(!meta) return;
  writeIdByFile[name] = Math.max(writeIdByFile[name] || 0, meta.writeId || 0);
  writeIdNext[name] = Math.max(writeIdNext[name] || 0, writeIdByFile[name]);
  persistWriteIds();
  lastSavedAtByFile[name] = Math.max(lastSavedAtByFile[name] || 0, meta.savedAt || 0);
  /* Do NOT let a file we have just read replace a copy we hold that is demonstrably
     NEWER. The error message on a rollback says "reopen it from the dropdown", and
     following that advice used to overwrite the good in-memory copy with the
     rolled-back disk text - deleting the safety net by taking the advice. Same for
     answering "keep what is on screen" at reattach and then reopening. */
  /* The counter WINS when both sides have one; the clock is consulted only when
     at least one of them does not. Written as an OR first, which inverted on skew:
     our id 3 stamped 20:04 by our clock "beat" the other machine's id 10 stamped
     20:02 by its slower one, so the copy held for recovery was seven of their
     writes behind the file the user was actually looking at. */
  const held = lastGood[name];
  let heldIsNewer = false;
  if(held){
    if(held.writeId && meta.writeId) heldIsNewer = held.writeId > meta.writeId;
    else heldIsNewer = !!(held.savedAt && meta.savedAt && held.savedAt > meta.savedAt);
  }
  if(heldIsNewer || provenanceOnly) return;
  rememberGood(name, text, meta.writeId || 0, meta.savedAt || 0);
}
function classifyDisk(seen, name){
  if(seen === getBaselineByName(name)) return 'same';
  const meta = readMeta(seen);
  if(!meta) return 'damaged';
  const ours = writeIdByFile[name] || 0;
  if(ours && meta.writeId && meta.writeId < ours) return 'stale';
  /* The counter-less rollback. meta.writeId is 0 for anything V35 or earlier wrote
     - and V35 re-saving a V36 file strips the field - so the strict test above is
     blind to precisely the files most likely to roll back during the changeover.
     It is a SEPARATE verdict, not 'stale', and deliberately carries no Restore
     button. A synced folder is not one clock and the machines on it are not NTP
     tight - a club laptop that has been asleep can be minutes out - so an older
     timestamp is as likely to mean "their clock is behind" as "the file went
     backwards", and only one of those readings makes restoring safe. The counter
     is the evidence that justifies a destructive offer; a timestamp is only ever
     enough to say "look at this before you save over it". */
  if(!meta.writeId && meta.savedAt && lastSavedAtByFile[name]
     && meta.savedAt < lastSavedAtByFile[name] - CLOCK_SKEW_MS) return 'maybe-stale';
  /* Our OWN write, arriving late. OneDrive pauses mid-commit; writeHandle throws;
     resyncBaseline captures the torn text as the baseline; the sync then finishes
     and the disk holds the very bytes we sent. V35 called that "changed outside
     this tab" and refused every autosave from then on, forever, with the only way
     out a manual Save or a reopen. The writer id and the counter identify it
     exactly, and this is the headline OneDrive case. */
  /* STRICTLY greater than the last id we VERIFIED, and no greater than the last we
     ALLOCATED. That window is exactly "a write we started and never saw land", and
     nothing else belongs in it.
     Written as >= ours first, and it opened a hole big enough to lose a meeting
     through: a file whose writeId EQUALS the one we already verified is not our
     late write - we saw that write land - so different bytes under the same id
     mean somebody edited our file. The guard then classified an external edit as
     our own, adopted it, cleared the warning and overwrote it, green tick and all.
     Caught by t12g, which builds "the other tab's copy" by editing ours. */
  if(meta.writer === TAB_ID && meta.writeId > ours
     && meta.writeId <= (writeIdNext[name] || 0)) return 'ours-late';
  if(meta.writer && meta.writer !== TAB_ID) return 'other';
  return 'changed';
}
/* Initials for the filename: the explicit field if set, otherwise the capitals
   of the club name ("Nee Soon East Toastmasters Club" -> NSE, dropping the
   generic Toastmasters/Club words). */
function clubInitials(){
  const set = (state.meeting.clubInitials || '').trim();
  if(set) return set.replace(/[^A-Za-z0-9]+/g, '').toUpperCase().slice(0, 8) || 'TMC';
  const words = (state.meeting.clubName || '').split(/\s+/)
    .filter(w => w && !/^(toastmasters?|club|the|of|and)$/i.test(w));
  return (words.map(w => w[0]).join('').toUpperCase().slice(0, 8)) || 'TMC';
}

/* Turn whatever is in the Date field into a sortable yyyy-mm-dd. It is free
   text - "Thursday, 13 August 2026", "13/08/2026" and "2026-08-13" all appear -
   so parse the shapes we actually see and fall back to today rather than
   inventing a wrong date. */
function meetingDateStamp(){
  const raw = (state.meeting.dateDisplay || '').trim();
  const MON = ['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'];
  const two = n => String(n).padStart(2, '0');
  let m;
  if((m = raw.match(/(\d{4})-(\d{1,2})-(\d{1,2})/)))
    return m[1] + '-' + two(m[2]) + '-' + two(m[3]);
  if((m = raw.match(/(\d{1,2})[\/.](\d{1,2})[\/.](\d{4})/)))      /* d/m/yyyy */
    return m[3] + '-' + two(m[2]) + '-' + two(m[1]);
  if((m = raw.match(/(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})/))){
    const i = MON.indexOf(m[2].slice(0, 3).toLowerCase());
    if(i >= 0) return m[3] + '-' + two(i + 1) + '-' + two(m[1]);
  }
  if((m = raw.match(/([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})/))){       /* August 13, 2026 */
    const i = MON.indexOf(m[1].slice(0, 3).toLowerCase());
    if(i >= 0) return m[3] + '-' + two(i + 1) + '-' + two(m[2]);
  }
  const d = new Date();
  return d.getFullYear() + '-' + two(d.getMonth() + 1) + '-' + two(d.getDate());
}

/* <Initials>-ProgSheet-<meeting date>-<time now>. The time is what stops two
   saves of the same meeting from silently overwriting each other (Rama, V29) -
   the date alone would collide every time you saved a second copy. */
function suggestedFileStem(){
  const d = new Date();
  const two = n => String(n).padStart(2, '0');
  const now = two(d.getHours()) + two(d.getMinutes());
  return clubInitials() + '-ProgSheet-' + meetingDateStamp() + '-' + now;
}

/* ONE name drives the .json, the HTML, the PDF and the images (V30). Before this
   the meeting file was named from the club initials and date while every download
   was named from the meeting TITLE, so a folder held "NSE-ProgSheet-2026-08-13"
   next to "Voices_of_a_Nation.pdf" and nothing lined up. Whatever is typed in the
   Save dialog wins for all of them; blank falls back to the suggestion. */
/* Does this look like a name the app generated, rather than one Rama typed?
   <INITIALS>-ProgSheet-<yyyy-mm-dd>-<hhmm>. It matters because an auto name
   carries a CLOCK TIME, and the whole point of that time is to be the moment you
   saved - V32 stored the first one on state and then offered it back for every
   later save, so the 9:15pm save was called ...-1847 (Rama, V33). A name the user
   typed is never regenerated. */
function isAutoName(stem){
  return /^[A-Za-z0-9]{1,8}-ProgSheet-\d{4}-\d{2}-\d{2}-\d{3,4}$/.test(String(stem||'').trim());
}
function fileBaseName(){
  /* An open file's own name wins, so every download matches the meeting on disk. */
  if(fileHandle && fileHandle.name) return tidyStem(fileHandle.name) || suggestedFileStem();
  const set = tidyStem(state.meeting.fileName || '');
  if(!set || isAutoName(set)) return suggestedFileStem();
  return set;
}
/* Strip the extension and anything a filesystem will not take. Windows also
   rejects a trailing dot or space, which a typed name picks up easily.
   Order matters and cost two bugs: stripping the extension FIRST meant a pasted
   "sheet.pdf " kept its extension (the $ anchor missed it behind the space) and
   saved as sheet.pdf.nse.json. Trim, strip, repeat until it settles, so the
   function is idempotent whatever the input. Returns '' for a name that is only
   punctuation - "////" used to survive as "-" and save a file called -.nse.json. */
function tidyStem(name){
  let s = String(name || '').trim();
  let prev;
  do{
    prev = s;
    s = s.replace(/[\s.]+$/, '').replace(/\.(nse\.json|json|html|pdf|jpe?g|png)$/i, '');
  } while(s !== prev);
  s = s.replace(/[\\/:*?"<>|]+/g, '-').replace(/^[\s.\-]+|[\s.\-]+$/g, '');
  /* Windows still reserves these as device names whatever the extension, and a
     path has a length limit. Both fail at the OS with a generic error that costs
     the user a save and tells them nothing. */
  if(/^(con|prn|aux|nul|com[1-9]|lpt[1-9])$/i.test(s)) s = s + '-meeting';
  return s.slice(0, 120);
}
function tidyFileName(name){
  const stem = tidyStem(name);
  return stem ? stem + FILE_EXT : '';
}

/* --- permissions --- */
async function handleUsable(h, interactive){
  if(!h || !h.queryPermission) return !!h;
  const opts = {mode:'readwrite'};
  if(await h.queryPermission(opts) === 'granted') return true;
  if(!interactive) return false;
  try{ return await h.requestPermission(opts) === 'granted'; }catch(e){ return false; }
}
/* interactive=true may only be called from a click - the browser refuses otherwise. */
async function ensureFolder(interactive){
  if(folderHandle && await handleUsable(folderHandle, interactive)) return true;
  const saved = await idbGet(IDB_FOLDER_KEY);
  if(saved && await handleUsable(saved, interactive)){ folderHandle = saved; return true; }
  return false;
}
async function linkFolder(){
  folderHandle = await window.showDirectoryPicker({mode:'readwrite', id:'nse-progsheet'});
  await idbSet(IDB_FOLDER_KEY, folderHandle);
  /* Do what the warning promises. It said "reconnect the folder from the dropdown
     to resume" and then reconnected nothing, so the warning could never be
     cleared by following its own instructions. */
  if(!fileHandle) await reattachFile();
  return true;
}

/* createWritable() writes to a swap file and only commits on close(), so a crash
   mid-write leaves the ORIGINAL file intact rather than a truncated one. What it
   does not promise is that the bytes that landed are the bytes we sent, so this
   reads the file back and checks the size. A short write is the shape a full disk
   or a revoked permission takes, and it is silent otherwise. */
/* One writer at a time, and the newest enqueued payload wins.
   The 1200ms debounce serialised TIMERS, not WRITES: on a folder that lives in
   OneDrive or on a network share a single round trip outlasts the debounce, two
   writes overlapped, and the OLDER one committed last. The file then held EDIT-1
   while the screen showed EDIT-2, with a green tick and no further writes.
   Proven with a commit log, not theorised. */
let writeSeq = {}, writeChain = Promise.resolve();
/* Values, not closures. Passing () => fileHandle meant the task read the handle
   when it RAN, and confirmSaveDialog nulls the handle on the next synchronous
   line - so the flush before a Save As saw null and quietly did nothing, which
   was the entire point of the flush. */
function enqueueWrite(handle, text, guarded){
  const key = baseKey(handle);
  const mine = (writeSeq[key] = (writeSeq[key] || 0) + 1);
  const run = writeChain.then(async ()=>{
    /* Superseded only by a newer write to the SAME file. */
    if(mine !== writeSeq[key]) return 'superseded';
    if(!handle) return 'detached';
    /* The writeId is allocated HERE, inside the serialised chain, and not at the
       call site. Stamped at call time, two queued writes would carry the same
       number, or arrive out of order - which is exactly the confusion the counter
       exists to detect, reintroduced by the counter itself. */
    const id = Math.max(writeIdNext[key] || 0, writeIdByFile[key] || 0) + 1;
    writeIdNext[key] = id;             /* burned whether or not the write lands */
    persistWriteIds();
    const body = stampWriteId(text, id);
    try{
      await writeHandle(handle, body);
    }catch(e){
      /* Any failure at all leaves the disk in a state we did not author. */
      await resyncBaseline(handle);
      throw e;
    }
    /* Only after the read-back in writeHandle agreed. A number recorded before
       verification would make our own half-landed write look authoritative and
       every later disk read look 'stale'. */
    writeIdByFile[key] = id;
    const stamp = readMeta(body);
    if(stamp) lastSavedAtByFile[key] = Math.max(lastSavedAtByFile[key] || 0, stamp.savedAt || 0);
    rememberGood(key, body, id, stamp ? stamp.savedAt : 0);
    /* The disk and the screen agree again, so an offer about a problem that has
       resolved itself - a torn read during a OneDrive pause gives 'damaged' for
       exactly one debounce - comes down; leaving it up arms a "discard everything
       since" button that stays armed all evening.
       Only for a write that actually LOOKED at the disk first. flushFileSave goes
       straight to the chain with no guard (it has to: it runs on pagehide), and
       letting it retire the offer meant a genuine rollback alarm vanished the
       moment the user switched tabs, unread, having just written over the other
       writer's copy. */
    if(guarded && recoverOffer && recoverOffer.name === key && recoverOffer.kind === 'disk')
      hideRecovery();
    return 'written';
  });
  /* Keep the chain alive whatever happens; the caller handles the rejection. */
  writeChain = run.catch(()=>{});
  return run;
}

/* Per FILE, not global. One shared baseline meant flushing meeting A while
   opening meeting B seeded the baseline from B's disk and then overwrote it with
   A's payload, after which every autosave to B was refused as "changed outside
   this tab" for the rest of the session. The sequence counter had the same shape
   of bug across files. */
let baseline = {};        /* file name -> the exact text we last saw on disk */
const baseKey = h => (h && h.name) || '';
function getBaselineByName(n){ return baseline[n] || ''; }
function getBaseline(h){ return baseline[baseKey(h)] || ''; }
function setBaseline(h, text){ if(h && h.name) baseline[h.name] = text; }
/* After a FAILED write the disk holds something we did not put there and cannot
   describe. Keeping the old baseline made the guard refuse every later autosave
   on a perfectly healthy disk, so the corrupt file could never be repaired and
   the advice on screen ("reopen it") failed too. Forget the baseline instead:
   the next write proceeds and fixes the file. */
/* After a failed write the disk holds something we did not author. Deleting the
   baseline repaired our own corrupt file (the next write proceeds) but also
   switched the two-tab guard OFF, so one transient failure was enough for the
   next autosave to obliterate another tab's meeting with no prompt.
   Re-reading is what does both jobs: if OUR write half-landed, the baseline now
   matches the disk and the next write repairs it; if someone ELSE wrote, the
   baseline matches theirs and the guard fires the moment we differ. */
async function resyncBaseline(h){
  if(!h || !h.name) return;
  try{ baseline[h.name] = await (await h.getFile()).text(); }
  catch(e){ delete baseline[h.name]; }
}

async function writeHandle(h, text){
  const w = await h.createWritable();
  await w.write(text);
  await w.close();
  /* Verify, THEN trust. lastWritten used to be set before this block, so a
     truncated commit left the file corrupt on disk while lastWritten held the
     bytes that never landed - and the external-change guard below then refused
     every later autosave with "that file changed outside this tab". The file was
     destroyed AND unrepairable, on a perfectly healthy disk. Verify first, and
     record what the disk actually came back with. */
  let verified = null;
  try{
    const f = await h.getFile();
    const expect = new Blob([text]).size;
    if(f.size !== expect) throw new Error('wrote ' + f.size + ' of ' + expect + ' bytes');
    /* Size alone passes a same-length stale commit, which is what a cloud-sync
       folder can hand back. The savedAt stamp is unique to every write. */
    const back = await f.text();
    const stamp = (text.match(/"savedAt":\s*"[^"]+"/) || [''])[0];
    if(stamp && back.indexOf(stamp) < 0) throw new Error('the file came back with older content');
    verified = back;
  }catch(e){
    /* A sandbox with no getFile() must not fail every save, but a REAL mismatch
       must not be swallowed either - the earlier filter only re-raised the size
       error, so the content check was dead code from the day it was written. */
    if(/wrote \d+ of|came back with older content/.test((e && e.message) || '')){
      await resyncBaseline(h);
      throw e;
    }
  }
  setBaseline(h, verified == null ? text : verified);
}

/* ================= Recovery (V36) =================
   The deliberate non-goal here is a locking protocol. Two tabs, or one tab and
   OneDrive's sync agent, cannot be serialised from inside a page: the guard read
   and the commit are two round trips with no way to make them one, so any lock
   built on top of them is a lock with a hole in it. What CAN be done is to notice
   afterwards, and to still be holding the last thing we know was good.

   So: keep the last verified text in memory, classify what the disk actually has
   when it stops matching, and offer the good copy back. Nothing is restored
   without being asked. */
let recoverOffer = null;      /* {name, text, why} */
/* "Leave it" has to mean something. The autosave guard re-runs on every keystroke
   and the disk is still damaged, so without this the bar the user just dismissed
   comes straight back, once per debounce, forever. Keyed on the file AND on what
   the disk held when they said no: if the disk changes again, that is new news and
   the offer is made again. */
let recoverDeclined = '';
const declineKey = (name, disk) => name + '#' + (disk || '').length + '#' + (disk || '').slice(0, 120);
function showRecovery(name, text, why, diskSeen, actionLabel, kind){
  recoverOffer = { name: name, text: text, why: why, kind: kind || 'disk',
                   decline: declineKey(name, diskSeen) };
  const el = document.getElementById('recoverBar');
  if(!el) return;
  el.textContent = '';
  const msg = document.createElement('div');
  msg.className = 'rb-msg';
  msg.textContent = why;
  const yes = document.createElement('button');
  yes.type = 'button';
  yes.textContent = actionLabel || 'Restore the last good version';
  yes.onclick = acceptRecovery;
  const no = document.createElement('button');
  no.type = 'button'; no.className = 'ghost';
  no.textContent = 'Leave it';
  no.onclick = dismissRecovery;
  el.appendChild(msg); el.appendChild(yes); el.appendChild(no);
  el.hidden = false;
}
function hideRecovery(){
  recoverOffer = null;
  const el = document.getElementById('recoverBar');
  if(el){ el.hidden = true; el.textContent = ''; }
}
function dismissRecovery(){
  const offer = recoverOffer;
  if(offer) recoverDeclined = offer.decline || '';
  hideRecovery();
  if(offer) showBanner('Left ' + offer.name + ' as it is on disk. The copy in this browser is '
    + 'unchanged, and it is not being written to that file.', true);
}
/* Load the good text onto the screen and let the ordinary save path put it back.
   It is NOT written straight to disk: the file we are recovering from is a file
   something else is writing to, and racing it is how the corruption happened.
   Adopting it on screen means the user sees what they are about to keep, and the
   baseline is resynced first so the next write is not refused by our own guard. */
async function acceptRecovery(){
  const offer = recoverOffer;
  recoverDeclined = '';        /* acted on: any later problem is news again */
  hideRecovery();
  if(!offer) return;
  /* The offer names a file. If this tab has since attached to a DIFFERENT one -
     Save As is the path that does it without detaching - then restoring would put
     the old meeting on screen and the autosave debounce would write it straight
     into the new file, over work that was never in trouble. The bar used to
     survive Save As and this check did not exist. */
  const attached = openFileName();
  if(attached && attached !== offer.name){
    showBanner('Not restored: this tab is now editing ' + attached + ', not ' + offer.name
      + '. Open ' + offer.name + ' from the dropdown first.', true);
    return;
  }
  /* Take a copy of what is being replaced FIRST. applyMeetingText overwrites state
     wholesale and the autosave restamps localStorage 400ms later, so there is
     nothing to go back to afterwards. An earlier version of this told the user to
     "use Undo in the fields", which does not exist and never did - a promise of a
     way back, made at the exact moment the last way back was closing. */
  const before = meetingPayload();
  if(!applyMeetingText(offer.text, offer.name)) return;
  /* Resync BEFORE the autosave debounce can fire, so our own guard does not then
     refuse the repair. This is also what makes the write below happen at all. */
  if(fileHandle && fileHandle.name === offer.name) await resyncBaseline(fileHandle);
  showBanner('Restored the last version of ' + offer.name + ' this tab saved intact, and it '
    + 'is being written back to that file now.', false);
  /* The same bar, pointed the other way. Real, not a form of words. */
  showRecovery(offer.name, before, 'Restored ' + offer.name
    + '. If that was not the copy you wanted, put back what was on screen a moment ago.',
    null, 'Put back what was on screen', 'undo');
}
/* Offer the good copy if we have one, and say plainly that we do not if we do
   not - a warning that implies a safety net that is not there is worse than the
   plain bad news. */
function offerRecovery(name, why, diskSeen){
  if(recoverDeclined && recoverDeclined === declineKey(name, diskSeen)) return;
  const good = lastGood[name];
  if(good && good.text) showRecovery(name, good.text, why + ' This tab still holds the version it '
    + 'last saved intact (' + new Date(good.at).toLocaleTimeString() + ').', diskSeen);
  else showBanner(why + ' This tab has no earlier copy of that file to offer.', true);
}

/* --- advisory lock, same browser only ---
   A second layer, not the answer. file:// pages share one localStorage origin, so
   two tabs of the builder can see each other here even though they can see nothing
   else. It cannot detect another MACHINE on the synced folder, and it cannot make
   the write atomic; it just means the common case - two tabs left open on the same
   meeting - says so out loud instead of quietly losing an evening's edits.
   Advisory on purpose: it warns, it never blocks. A lock that can refuse to save
   is a lock that can lock you out of your own meeting twenty minutes before it. */
const LOCK_PREFIX = 'nse-ps-lock:';
const LOCK_TTL_MS = 15000;     /* a heartbeat older than this is a dead tab */
const LOCK_BEAT_MS = 5000;
/* Both the name and the exact key we claimed. Recomputing the key at release time
   would look it up under whatever folder is attached THEN, and a folder change
   between hold and release would leak the old claim forever. */
let lockTimer = null, lockedName = '', lockedKey = '';
/* Scoped by FOLDER as well as file name. Save filenames are generated from the
   meeting date, so two tabs on two different folders routinely hold same-named
   meetings - and on file:// every build of this tool shares one localStorage
   origin, so a key left by another copy counts too. Without the folder in the key
   those are all false alarms, and a false alarm is how a real one gets ignored. */
function lockKey(name){
  return LOCK_PREFIX + ((folderHandle && folderHandle.name) || '?') + '/' + name;
}
function readLock(name){
  try{ return JSON.parse(localStorage.getItem(lockKey(name)) || 'null'); }
  catch(e){ return null; }
}
function beatLock(){
  if(!lockedKey) return;
  try{ localStorage.setItem(lockedKey, JSON.stringify({tab:TAB_ID, at:Date.now()})); }catch(e){}
}
/* Returns the LIVE FOREIGN claim it displaced, or null. The caller needs that
   return value: once we have written our own heartbeat over the key, reading it
   back tells us about ourselves. Splitting the claim from the warning without
   this made saveMeetingDirect's warning permanently silent - it claimed the lock
   next to the assignment and then asked, at the end, whether anyone held it. */
function holdLock(name){
  const want = name ? lockKey(name) : '';
  const prior = name ? readLock(name) : null;
  const displaced = (prior && prior.tab && prior.tab !== TAB_ID
                     && (Date.now() - (Number(prior.at) || 0)) < LOCK_TTL_MS) ? prior : null;
  /* Compare the KEY, not just the name. Reconnecting a different folder while the
     same meeting is open leaves the name unchanged and the key different, and the
     old claim was then overwritten in place and never removed - it sat in
     localStorage warning a tab legitimately editing the other folder's file. */
  if(lockedKey && lockedKey !== want) releaseLock();
  lockedName = name || '';
  lockedKey = want;
  if(!lockedName) return null;
  beatLock();
  clearInterval(lockTimer);
  lockTimer = setInterval(beatLock, LOCK_BEAT_MS);
  return displaced;
}
function releaseLock(){
  clearInterval(lockTimer); lockTimer = null;
  if(!lockedName) return;
  /* Only ever clear OUR OWN claim. Removing another tab's key would hand it the
     silence this is meant to break. */
  let l = null;
  try{ l = JSON.parse(localStorage.getItem(lockedKey) || 'null'); }catch(e){}
  if(!l || l.tab === TAB_ID){ try{ localStorage.removeItem(lockedKey); }catch(e){} }
  lockedName = ''; lockedKey = '';
}
/* Once per (file, other tab), and never again. The heartbeat rewrites the lock key
   every 5 seconds, which fires a storage event in every other tab of the origin -
   so the first version of this re-raised the alarm on a 5-second timer, forever.
   That put a permanent banner on screen AND kept re-arming the sticky save warning
   the moment each successful autosave cleared it, which is the one channel this
   codebase has protected since V21: a real 'disk full' would have been overwritten
   by the second-tab text within five seconds and never read. */
let toldAboutTabs = {};
function saySecondTab(name, otherTab){
  const k = (lockedKey || name) + '|' + (otherTab || '?');
  if(toldAboutTabs[k]) return;
  toldAboutTabs[k] = true;
  setSaveWarning('Another tab in this browser also has ' + name + ' open. Both are autosaving '
    + 'into it, and the last one to type wins. Close the other tab, or use Save As here.');
  showBanner('Another tab in this browser has ' + name + ' open. Whichever tab types last '
    + 'wins — close one of them.', true);
}
/* Called on every attach. Returns nothing; it is a notice, not a gate. */
function warnIfSecondTab(name){
  const displaced = holdLock(name);
  if(displaced) saySecondTab(name, displaced.tab);
}
/* The INCUMBENT has to be told too. Checking only at attach meant the tab that had
   been open all evening - the one holding the unsaved work - heard nothing, and
   only the newcomer was warned. localStorage fires 'storage' in every OTHER tab of
   the origin, so the claim itself is the notification. */
window.addEventListener('storage', (e)=>{
  if(!lockedKey || !e || e.key !== lockedKey || !e.newValue) return;
  let l = null;
  try{ l = JSON.parse(e.newValue); }catch(err){ return; }
  if(l && l.tab && l.tab !== TAB_ID) saySecondTab(lockedName, l.tab);
});
/* bfcache: pagehide can be a suspend rather than a close, and the tab comes back
   still attached and still autosaving. Without the pageshow half it would come
   back advertising nothing, which is the one state this is meant to prevent.
   Registered BEFORE the pagehide flush further down, so the flush - which must
   start synchronously - is not sitting behind these localStorage calls. */
window.addEventListener('pageshow', (e)=>{
  if(e && e.persisted && fileHandle && fileHandle.name) warnIfSecondTab(fileHandle.name);
});

/* --- the Save dialog (V30) ---
   V29 asked for the filename with window.prompt(). Two problems: a file:// page in
   some browsers suppresses prompt() entirely, so the name silently became the
   default; and it only appeared the FIRST time, leaving no way to rename or to see
   what the meeting was saved as. This is an in-page dialog instead, so it renders
   the same everywhere, shows the folder and the extension, and doubles as the
   phone's "clear save option". */
let saveAsNew = false;
function openSaveDialog(asNew){
  saveAsNew = !!asNew;
  const dlg = document.getElementById('saveDialog');
  const inp = document.getElementById('saveFileName');
  if(!dlg || !inp) return saveMeetingDirect();          /* dialog stripped: fall back */
  /* Renaming an open file means Save As, whatever button was pressed. */
  const current = (!asNew && fileHandle) ? tidyStem(fileHandle.name) : tidyStem(state.meeting.fileName || '');
  /* Re-stamp an auto name with the time NOW; keep a typed one exactly as it is. */
  inp.value = (current && !isAutoName(current)) ? current : suggestedFileStem();
  const where = document.getElementById('saveWhere');
  if(where){
    where.textContent = !FS_SUPPORTED
      ? 'This browser cannot write to a folder, so it will go to your Downloads.'
      : (folderHandle ? 'Saves into the meetings folder you connected.'
                      : 'You will be asked to pick the meetings folder once.');
  }
  dlg.classList.add('open');
  document.body.style.overflow = 'hidden';
  setTimeout(()=>{ inp.focus(); inp.select(); }, 20);
}
function closeSaveDialog(){
  const dlg = document.getElementById('saveDialog');
  if(dlg) dlg.classList.remove('open');
  document.body.style.overflow = '';
}
/* Keeping the typed name on state means the downloads match it too, and it
   survives into the .json so reopening the meeting keeps its name. */
function confirmSaveDialog(){
  const inp = document.getElementById('saveFileName');
  const stem = tidyStem(inp ? inp.value : '');
  if(!stem){
    showBanner('Give the file a name first.', true);
    if(inp) inp.focus();
    return;
  }
  state.meeting.fileName = stem;
  const renamed = fileHandle && tidyStem(fileHandle.name) !== stem;
  if(saveAsNew || renamed){
    /* Cancel the queued autosave with it. Nulling the handle alone left a timer
       that fired into nothing and threw. */
    flushFileSave();
    clearTimeout(fileSaveTimer); fileSaveTimer = null;
    fileHandle = null;
    /* Drop the claim on the file we are leaving. holdLock() would swap it when the
       new file attaches, but only if the save gets that far - a cancelled folder
       picker would otherwise leave this tab warning other tabs off a file it is no
       longer writing to. */
    releaseLock();
    /* And the recovery offer, which names the file we are walking away from.
       detachFile and pickMeetingFile both do this; Save As was the hole, and the
       consequence was the worst one available: click Restore afterwards and the
       old meeting is adopted and autosaved into the NEW file. */
    hideRecovery();
    recoverDeclined = '';
  }
  closeSaveDialog();
  saveMeetingDirect(stem + FILE_EXT);
}
function saveDialogKey(e){
  if(e.key === 'Enter'){ e.preventDefault(); confirmSaveDialog(); }
}

/* --- detaching --- */
function openFileName(){ return (fileHandle && fileHandle.name) || ''; }
/* Stop autosaving into the open file and cancel anything already queued. The
   cancel matters: a debounced write fired 1.2s after a Reset and put the blank
   template into the meeting on disk. */
function detachFile(msg){
  clearTimeout(fileSaveTimer);
  fileSaveTimer = null;
  if(fileHandle && fileHandle.name) delete baseline[fileHandle.name];
  fileHandle = null;
  releaseLock();
  recoverDeclined = '';
  /* The offer belongs to a file we are no longer attached to. Leaving it up would
     let "Restore the last good version" overwrite the screen with a meeting the
     user has just deliberately walked away from. lastGood itself is kept: the
     text is still the last good text if they come back to that file. */
  hideRecovery();
  clearSaveWarning();
  idbSet(IDB_FILE_KEY, null);
  state.meeting.fileName = '';
  setSaveStatus(msg || 'Autosaving to this browser only', false, true);
  refreshFileList();
}

/* --- save --- */
/* The dialog is the front door; this is the part that actually writes. */
async function saveMeetingDirect(name){
  if(!FS_SUPPORTED) return downloadMeetingJSON();
  let displacedTab = null;      /* who held this file when we took it, if anyone */
  try{
    if(!await ensureFolder(true)) await linkFolder();
    if(!folderHandle) return;
    /* Same guard as the autosave. Deleting every row is reachable through the UI,
       and a manual Save then wrote segments:[] straight over a real meeting with
       a cheerful "Saved" banner. */
    if(!Array.isArray(state.segments) || !state.segments.length){
      showBanner('This sheet has no programme items, so it was not saved. '
        + 'Add a segment, or use Reset to start a fresh sheet.', true);
      return;
    }
    /* The same external-change check the autosave does. Without it the warning
       "reopen it, or use Save As" was hollow: plain Save sailed past and
       overwrote the other tab's meeting without a word. */
    if(fileHandle && getBaseline(fileHandle)){
      let seen = null;
      try{ seen = await (await fileHandle.getFile()).text(); }catch(e){}
      if(seen && seen !== getBaseline(fileHandle)){
        /* Name what happened. "Changed outside this tab" is true of a rolled-back
           file and of a torn one too, and in both of those cases "saving now
           replaces the other version" is the reassuring reading of a sentence that
           should be alarming. */
        const kind = classifyDisk(seen, fileHandle.name);
        const what = kind === 'damaged'
            ? openFileName() + ' on disk is not readable as a meeting — it looks torn or '
              + 'half-synced.\n\nSaving now replaces it with what is on screen. Continue?'
          : kind === 'stale'
            ? openFileName() + ' on disk has gone BACKWARDS: it holds an older save than the one '
              + 'this tab already wrote.\n\nSaving now replaces it with what is on screen. Continue?'
          : openFileName() + ' has changed outside this tab since you opened it.\n\n'
              + 'Saving now replaces the other version. Continue?';
        if(!confirm(what)){
          showBanner('Not saved — ' + openFileName() + ' was left as it is.', true);
          if(kind === 'damaged' || kind === 'stale')
            offerRecovery(fileHandle.name, openFileName() + ' on disk is '
              + (kind === 'damaged' ? 'damaged' : 'an older save than this tab already wrote') + '.', seen);
          return;
        }
        /* Deliberately overwriting a file another tab has moved on: take its
           number with us so the write that follows is genuinely the newest one on
           disk, not a lower id that reads as a rollback in the other tab. */
        if(kind === 'other' || kind === 'changed'){
          const meta = readMeta(seen);
          if(meta) writeIdByFile[fileHandle.name] =
            Math.max(writeIdByFile[fileHandle.name] || 0, meta.writeId || 0);
        }
      }
    }
    if(!fileHandle){
      const fname = tidyFileName(name || fileBaseName());
      if(!fname) return;
      /* Ask before replacing somebody else's meeting. getFileHandle with
         create:true is happy to obliterate an existing file without a word, and
         tidyStem collapses several illegal characters to "-", so two differently
         typed names converge more often than you would think. */
      let exists = false, existingText = '';
      try{
        const prior = await folderHandle.getFileHandle(fname);
        exists = true;
        existingText = await (await prior.getFile()).text();
      }catch(e){}
      if(exists && !confirm(fname + ' already exists in that folder.\n\n'
          + 'Replace it? The meeting currently in that file will be lost.')){
        showBanner('Not saved — ' + fname + ' was left alone. Press Save again and give it '
          + 'a different name.', true);
        return;
      }
      fileHandle = await folderHandle.getFileHandle(fname, {create:true});
      /* Claim it HERE, next to the assignment. Only the warning belongs at the end
         of this function; leaving the claim there too meant one transient failure
         in enqueueWrite or refreshFileList jumped to the catch and this tab then
         autosaved into the file all session while advertising nothing. */
      displacedTab = holdLock(fname);
      /* Take the counter of whatever we are replacing. Without this, a Save As over
         a file another tab has advanced to id 37 is stamped id 1, and that tab
         reads the user's deliberate save as a sync rollback and offers to undo it.
         The already-attached path does this a few lines up; this one did not. */
      if(existingText) adoptDiskProvenance(fname, existingText, true);
      await idbSet(IDB_FILE_KEY, fileHandle);
    }
    /* 'superseded' means a NEWER payload for this same file is already queued and
       will land - that is success, not failure. Reporting it as an error told
       people their Save had failed when the disk held their newest work. */
    const r = await enqueueWrite(fileHandle, meetingPayload(), true);
    if(r === 'detached') throw new Error('the file was closed before the write');
    clearSaveWarning();
    await refreshFileList();
    setSaveStatus('Saved to ' + fileHandle.name + ' - autosaving there', false, true);
    flashSaved();
    showBanner('Saved ' + fileHandle.name + '. Every change from here autosaves into that file.', false);
    /* LAST. Raised before the write, the warning and its banner were both wiped
       three statements later by clearSaveWarning() and the success banner - so on
       the one path where the user deliberately attaches to a file another tab is
       holding, they were told nothing at all. */
    if(displacedTab) saySecondTab(fileHandle.name, displacedTab.tab);
  }catch(err){
    if(err && err.name === 'AbortError') return;      /* user closed the picker */
    /* Sticky, not just a banner. A manual Save that wrote nothing used to leave a
       green tick behind - on the one path where the user had explicitly asked to
       save and would reasonably stop worrying about it. */
    setSaveWarning('NOT saved to ' + (openFileName() || 'a file') + ': '
      + ((err && err.message) || 'unknown') + '. Your work is still in this browser.');
    showBanner('Could not save to the folder (' + ((err && err.message) || 'unknown')
      + '). Your work is still held in this browser.', true);
  }
}
function saveMeeting(){ return openSaveDialog(false); }
function saveMeetingAs(){ return openSaveDialog(true); }
/* Autosave into the open file. Silent by design - it runs on every keystroke's
   debounce, so it must never nag; a failure downgrades the badge instead. */
function queueFileSave(){
  if(!fileHandle) return;
  clearTimeout(fileSaveTimer);
  fileSaveTimer = setTimeout(async ()=>{
    try{
      /* A sheet with no running order is not a meeting; it is the shape a failed
         load or a half-finished edit takes, and writing it would overwrite the
         real thing. Refuse rather than autosave a blank. */
      if(!Array.isArray(state.segments) || !state.segments.length){
        return setSaveWarning('Not autosaving — this sheet has no programme items.');
      }
      if(!await handleUsable(folderHandle, false)) throw new Error('permission');
      /* The handle is path-based: rename or delete the file in Explorer and the
         next write cheerfully RECREATES it at the old name, so the user ends up
         with two files and no warning. And a second tab (or another machine on a
         synced folder) writing the same file must not be silently clobbered. */
      const disk = await fileHandle.getFile();
      const seen = await disk.text();
      if(getBaseline(fileHandle) && seen && seen !== getBaseline(fileHandle)){
        /* Was: one message for every kind of difference. A file half-written by a
           sync agent, a file rolled BACK to an older version by one, and a second
           tab saving legitimately are three different events with three different
           right answers, and "reopen it from the dropdown" is actively wrong for
           the first two - reopening loads the damage. */
        const kind = classifyDisk(seen, fileHandle.name);
        /* One if/else chain, and every branch either throws or falls out of the
           block deliberately. The first version wrote the 'ours-late' branch as an
           `else if` pair followed by two more UNCHAINED ifs and an unconditional
           throw at the end - so the branch that exists to let the write proceed
           adopted the baseline and then threw the generic "reopen it from the
           dropdown" anyway. It read as three separate decisions and behaved as
           one. Keep this a single chain. */
        if(kind === 'ours-late'){
          /* Our own write, landed late: OneDrive paused mid-commit, writeHandle
             threw, resyncBaseline captured the torn text, and the sync has now
             finished with the bytes we sent. Adopt and carry on. */
          setBaseline(fileHandle, seen);
          adoptDiskProvenance(fileHandle.name, seen);
          clearSaveWarning();
          if(recoverOffer && recoverOffer.name === fileHandle.name
             && recoverOffer.kind === 'disk') hideRecovery();
        } else if(kind === 'damaged'){
          offerRecovery(fileHandle.name, fileHandle.name + ' on disk is no longer readable as a '
            + 'meeting. Nothing more is being written to it.', seen);
          throw new Error('that file is damaged on disk — nothing was written over it');
        } else if(kind === 'stale'){
          offerRecovery(fileHandle.name, fileHandle.name + ' on disk has gone BACKWARDS: it now '
            + 'holds an older save than the one this tab already wrote and verified. That is a '
            + 'sync agent or a second tab putting an old copy back.', seen);
          throw new Error('that file went backwards on disk — nothing was written over it');
        } else if(kind === 'maybe-stale'){
          /* Timestamps only, no counter to appeal to. Say so and stop; do NOT put
             a Restore button on it. Wall-clock skew between two machines on one
             synced folder is minutes, not seconds, so this verdict is as likely to
             mean "their clock is behind" as "the file went backwards" - and one of
             those two readings makes Restore destroy somebody else's evening. */
          throw new Error(fileHandle.name + ' on disk carries an OLDER timestamp than the copy '
            + 'this tab saved. It has no version counter, so this could be a rollback or just '
            + 'another machine\u2019s clock. Nothing was written over it — open it from the '
            + 'dropdown and look before saving');
        } else {
          throw new Error('that file changed outside this tab — reopen it from the '
            + 'dropdown before saving, or use Save As');
        }
      }
      const r = await enqueueWrite(fileHandle, meetingPayload(), true);
      if(r === 'written') clearSaveWarning();
    }catch(e){
      /* fileHandle can be null by the time this fires - Save As nulls it - and
         dereferencing .name here threw an unhandled TypeError that swallowed the
         real error entirely: no badge, no banner, green tick. */
      setSaveWarning('NOT saved to ' + (openFileName() || 'the file') + ': '
        + ((e && e.message) || 'unknown') + '. Your work is still in this browser.');
    }
  }, 1200);
}

/* Re-attach the meeting that was open when the tab last closed. Permission can
   only be re-requested from a click, so a lapsed grant is reported rather than
   silently swallowed: the user gets one honest line telling them the file is not
   being written to, instead of a green tick that means nothing. */
async function reattachFile(){
  if(!FS_SUPPORTED || !folderHandle) return;
  try{
    const h = await idbGet(IDB_FILE_KEY);
    if(!h) return;
    if(!await handleUsable(folderHandle, false)){
      setSaveWarning('Not saving to ' + (h.name || 'your file') + ' yet — reconnect the folder '
        + 'from the dropdown to resume.');
      return;
    }
    /* Prove the file is still there under that name before claiming it. A file
       renamed or deleted in Explorer would otherwise be RECREATED empty by the
       next autosave, leaving two files and a green tick. */
    const disk = await folderHandle.getFileHandle(h.name);
    /* The file and the browser's copy can disagree after a reload - two tabs, or
       a save that never landed. Attaching and autosaving whatever localStorage
       restored silently replaced the meeting on disk with a different one on the
       first keystroke. Compare the two savedAt stamps and take the NEWER, saying
       which; a file is never overwritten by an older copy without a word. */
    let diskText = '';
    try{ diskText = await (await disk.getFile()).text(); }catch(e){}
    /* startupSavedAt is captured synchronously at load, BEFORE the first autosave
       debounce can restamp localStorage with the current time. Reading it here
       instead meant the browser copy always looked newer than any real file, so
       the file always lost - and lost silently, on the reload that happens every
       morning. */
    let diskAt = 0;
    try{ diskAt = Date.parse(JSON.parse(diskText).savedAt) || 0; }catch(e){}
    /* Guarded. This parse sat outside a try while the one two lines above was
       inside one, so a truncated or half-synced file threw into the outer catch
       and the app announced that the file "is no longer in that folder" - false,
       detached from a file that was right there, and left the corruption
       unrepairable by the very autosave that could have fixed it. A file mid-sync
       IS a half-written file, so this was reachable without any second tab. */
    let sameMeeting = false, diskReadable = false;
    try{
      sameMeeting = JSON.stringify(JSON.parse(diskText).state || {}) === JSON.stringify(state);
      diskReadable = true;
    }catch(e){ diskReadable = false; }
    if(diskText && !diskReadable){
      setSaveWarning(h.name + ' on disk is damaged and could not be read. This meeting is '
        + 'still attached to it, so your next change will overwrite it with what is on screen.');
    }
    if(diskText && diskReadable && !sameMeeting){
      /* A timestamp cannot tell two VERSIONS of one meeting from two DIFFERENT
         meetings, and both were being resolved by silently overwriting the file.
         When the newer one is clearly the file, take it. Otherwise ask. */
      if((diskAt && diskAt > startupSavedAt) || !startupSavedAt){
        if(applyMeetingText(diskText, h.name)){
          showBanner(h.name + ' on disk was newer than the copy in this browser, so the file '
            + 'was loaded. Nothing was overwritten.', false);
        }
      } else if(confirm(h.name + ' on disk does not match the meeting this browser restored.\n\n'
          + 'OK  = load the file and discard what the browser had.\n'
          + 'Cancel = keep what is on screen (the file is replaced when you next type).')){
        applyMeetingText(diskText, h.name);
      } else {
        showBanner('Keeping the version on screen. ' + h.name
          + ' will be replaced the next time you make a change.', true);
      }
    }
    fileHandle = h;
    /* Seed the external-change baseline from what is on disk RIGHT NOW, or the
       guard is blind for the first autosave after every reload - precisely when
       another tab or another machine is most likely to have touched the file. */
    setBaseline(h, diskText);
    /* And the write counter with it. A fresh page starts at 0, so without this
       the first autosave after every reload is stamped id 1 and every other tab
       reads it as a rollback. */
    adoptDiskProvenance(h.name, diskText);
    warnIfSecondTab(h.name);
    setSaveStatus('Editing ' + h.name + ' — autosaving there', false, true);
  }catch(e){
    setSaveWarning('The meeting file that was open is no longer in that folder. '
      + 'Nothing is being written to disk — use Save to choose a file.');
    await idbSet(IDB_FILE_KEY, null);
  }
}

/* --- the dropdown --- */
async function refreshFileList(){
  const sel = document.getElementById('fileSelect');
  if(!sel) return;
  const opts = ['<option value="">Saved meetings…</option>'];
  let names = [];
  if(FS_SUPPORTED && folderHandle && await handleUsable(folderHandle, false)){
    try{
      for await (const [name, h] of folderHandle.entries()){
        if(h.kind === 'file' && /\.json$/i.test(name)) names.push(name);
      }
    }catch(e){ names = []; }
    names.sort((a,b)=> a.localeCompare(b));
    opts.push(...names.map(n =>
      `<option value="f:${esc(n)}"${fileHandle && fileHandle.name === n ? ' selected' : ''}>${esc(n)}</option>`));
    if(!names.length) opts.push('<option value="" disabled>(no saved meetings in that folder yet)</option>');
    opts.push('<option value="__saveas">＋ Save as a new file…</option>');
    opts.push('<option value="__folder">⟳ Choose a different folder…</option>');
  } else if(FS_SUPPORTED){
    opts.push('<option value="__folder">📂 Connect the meetings folder…</option>');
  } else {
    opts.push('<option value="__upload">📂 Open a saved .json file…</option>');
  }
  sel.innerHTML = opts.join('');
}

async function pickMeetingFile(value){
  const sel = document.getElementById('fileSelect');
  /* Flush BEFORE anything replaces state. Opening another meeting 200ms after an
     edit used to discard that edit from the file AND from localStorage, because
     the queued timer fired later and serialised the NEW meeting instead. */
  flushFileSave();
  try{
    if(value === '__folder'){ await linkFolder(); await refreshFileList(); return; }
    if(value === '__saveas'){ await saveMeetingAs(); return; }
    if(value === '__upload'){ return openMeetingJSON(); }
    if(!value.startsWith('f:')) return;
    const name = value.slice(2);
    if(!await ensureFolder(true)) return;
    const h = await folderHandle.getFileHandle(name);
    const text = await (await h.getFile()).text();
    if(!applyMeetingText(text, name)) return;
    fileHandle = h;
    setBaseline(h, text);
    adoptDiskProvenance(name, text);
    hideRecovery();                 /* a stale offer about the file we just left */
    recoverDeclined = '';
    await idbSet(IDB_FILE_KEY, h);
    clearSaveWarning();
    warnIfSecondTab(name);
    setSaveStatus('Editing ' + name + ' - autosaving there', false, true);
    showBanner('Loaded ' + name + '.', false);
  }catch(err){
    if(!err || err.name !== 'AbortError')
      showBanner('Could not open that meeting (' + ((err && err.message) || 'unknown') + ').', true);
  }finally{
    if(sel) await refreshFileList();
  }
}

/* Shared by the folder path and the fallback file picker. */
/* 36: the payload gained writeId and writer. A V35 build reading a V36 file drops
   both on its next save, which is silent - but bumping this at least makes a V36
   build say so when it meets a file some other version has been through. */
const PAYLOAD_VERSION = 36;
function applyMeetingText(text, label){
  let parsed;
  try{ parsed = JSON.parse(text); }
  catch(e){ showBanner((label||'That file') + ' is not readable JSON.', true); return false; }
  /* A file written by a LATER version may carry fields this build drops on the
     next autosave. Loading it is still better than refusing, but say so - a
     silent downgrade is how work disappears. */
  const fileV = Number(parsed && parsed.v);
  const newer = isFinite(fileV) && fileV > PAYLOAD_VERSION;
  if(!adoptState(parsed)){
    showBanner((label||'That file') + ' is not a programme-sheet meeting - nothing was changed.', true);
    return false;
  }
  if(newer){
    showBanner((label||'That file') + ' was saved by a newer version of the builder. It has loaded, '
      + 'but anything this version does not understand will be dropped when it next saves.', true);
  } else if(lastAdoptRepairs.length){
    showBanner((label||'That file') + ' loaded with repairs: ' + lastAdoptRepairs.join('; ') + '.', true);
  }
  editingSegId = null;
  expandedSegs.clear();
  syncLanguageEvaluatorSegment();
  syncRoleSegments();
  applyPaneWidth();
  syncFormInputs();
  renderFormPane();
  renderPreviewNow();
  return true;
}

/* --- fallback for browsers without the API --- */
function downloadMeetingJSON(){
  saveBlob(new Blob([meetingPayload()], {type:'application/json'}), fileBaseName() + FILE_EXT);
  showBanner('Saved a .json copy to your Downloads folder. Open it again with the dropdown.', false);
}
function openMeetingJSON(){
  const inp = document.createElement('input');
  inp.type = 'file'; inp.accept = '.json,application/json';
  inp.onchange = async ()=>{
    const f = inp.files && inp.files[0];
    if(f) applyMeetingText(await f.text(), f.name);
  };
  inp.click();
}

/* ================= Download menu + instructions ================= */
/* Two download buttons now — the toolbar icon on desktop and the labelled one in
   the phone bar (V30). Only one is ever visible, but both are in the DOM, so these
   work off the button that was pressed rather than a fixed id. */
function toggleDownloadMenu(e){
  if(e) e.stopPropagation();
  const btn = e && e.currentTarget && e.currentTarget.closest ? e.currentTarget : null;
  const wrap = btn ? btn.closest('.menu-wrap') : null;
  const m = wrap ? wrap.querySelector('.dl-menu') : document.getElementById('dlMenu');
  if(!m) return;
  const willOpen = !m.classList.contains('open');
  closeDownloadMenu();
  if(willOpen){
    m.classList.add('open');
    if(btn) btn.setAttribute('aria-expanded','true');
  }
}
function closeDownloadMenu(){
  document.querySelectorAll('.dl-menu.open').forEach(m => m.classList.remove('open'));
  document.querySelectorAll('.menu-wrap [aria-haspopup]')
    .forEach(b => b.setAttribute('aria-expanded','false'));
}
function pickDownload(kind){
  closeDownloadMenu();
  if(kind === 'html') return downloadSheet();
  /* Always the in-page PDF, desktop included (V29). Routing desktop through the
     print dialog meant the file's size depended on which destination the user
     picked there - and "Microsoft Print to PDF" rasterises every page at 300dpi
     for a 1.4 MB result. The browser dialog is browser chrome; a web page cannot
     preselect a destination or even see which one is chosen. So Download > PDF
     no longer opens a dialog at all and lands under 500 KB, which is the figure
     the menu promises. Chrome's own "Save as PDF" is still the better file -
     smaller AND with selectable text - and Ctrl+P is how you reach it.
     (The two lines that used to sit above this block described a desktop/phone
     split that V29 replaced, and a printer button that no longer exists - the
     help text says so in as many words. Removed rather than left contradicting
     the paragraph under them.) */
  if(kind === 'pdf')  return downloadPdfImage();
  return downloadImage();
}
function openHelp(){
  document.getElementById('helpOverlay').classList.add('open');
  document.body.style.overflow = 'hidden';
}
function closeHelp(){
  document.getElementById('helpOverlay').classList.remove('open');
  document.body.style.overflow = '';
}
/* The autosave debounce is 1.2s. Closing the tab, switching app on a phone or
   locking the screen inside that window used to drop the last edits from the
   FILE (localStorage still had them, so it looked fine until the file was opened
   somewhere else). Flush on the way out. */
function flushFileSave(){
  if(!fileHandle || !fileSaveTimer) return;
  /* Check the guard BEFORE cancelling the timer. Clearing first meant a
     momentarily empty sheet lost the pending edit rather than deferring it. */
  if(!Array.isArray(state.segments) || !state.segments.length) return;
  clearTimeout(fileSaveTimer);
  fileSaveTimer = null;
  /* Permission can have lapsed since the last write; without this the final flush
     was the one write in the system that never checked, and it reported success
     against a folder it no longer had rights to. */
  /* Start the write NOW, synchronously. Awaiting a permission check first meant
     that at the moment pagehide fired, zero writes had begun - the write started
     ~120ms later, which a real tab close does not wait for. That is the exact
     case this flush exists for. A lapsed permission surfaces as the write's own
     error instead. */
  const target = fileHandle, payload = meetingPayload();
  enqueueWrite(target, payload)
    .catch(e => setSaveWarning('Last change may not have reached '
      + (target.name || 'the file') + '.'));
}
document.addEventListener('visibilitychange', ()=>{ if(document.hidden) flushFileSave(); });
/* flushFileSave FIRST and on its own line: it must start writing synchronously,
   and putting the lock's localStorage calls ahead of it inside one handler would
   push the write behind them. */
window.addEventListener('pagehide', ()=>{ flushFileSave(); releaseLock(); });

document.addEventListener('click', closeDownloadMenu);
document.addEventListener('keydown', e=>{
  if(e.key !== 'Escape') return;
  closeDownloadMenu();
  const s = document.getElementById('saveDialog');
  if(s && s.classList.contains('open')) return closeSaveDialog();
  const h = document.getElementById('helpOverlay');
  if(h && h.classList.contains('open')) closeHelp();
});

/* ================= Form binding ================= */
function bindMeeting(key, val){
  state.meeting[key] = val;
  /* Initials follow the club name until someone types their own. Compare against
     what the OLD name would have produced: if they match, the field was still
     being derived and may keep deriving. Typing "TMC" once stops it for good. */
  if(key === 'clubName') followClubInitials(val);
  updatePreview();
}
/* The capitals of the significant words: "Nee Soon East Toastmasters Club" -> NSE. */
function initialsFromName(name){
  const words = String(name || '').split(/\s+/)
    .filter(w => w && !/^(toastmasters?|club|the|of|and|advanced)$/i.test(w));
  return words.map(w => (w.match(/[A-Za-z0-9]/) || [''])[0]).join('').toUpperCase().slice(0, 8);
}
let lastClubName = null;
function followClubInitials(newName){
  const cur = String(state.meeting.clubInitials || '').trim();
  const derivedFromOld = initialsFromName(lastClubName == null ? newName : lastClubName);
  lastClubName = newName;
  if(cur && cur !== derivedFromOld) return;          /* the user typed their own */
  const next = initialsFromName(newName);
  if(next === cur) return;
  state.meeting.clubInitials = next;
  const el = document.getElementById('f-clubInitials');
  if(el && document.activeElement !== el) el.value = next;
}
function bindTheme(key){
  state.theme = THEMES.some(t=>t.key===key) ? key : 'classic';
  updatePreview();
}
function toggleRoleActive(key, on){
  if(!state.roleActive) state.roleActive = {};
  state.roleActive[key] = !!on;
  const input = document.getElementById('r-' + key);
  if(input) input.disabled = !on;
  const wrap = document.getElementById('rw-' + key);
  if(wrap) wrap.classList.toggle('role-off', !on);
  syncLanguageEvaluatorSegment();
  syncRoleSegments();
  rebalanceFlexSilent();
  renderFormPane();
  renderPreviewNow();
  const dropped = (ROLE_OWNED_SEGMENTS[key] || []).length;
  if(!on && dropped){
    showBanner(`${ROLE_LABELS[key]} switched off — ${dropped} agenda item${dropped>1?'s':''} removed from the programme. Tick it again to bring them back.`, false);
  }
}

function bindRole(key, val){
  state.roles[key] = val;
  if(key === 'langeval' && syncLanguageEvaluatorSegment()){
    rebalanceFlexSilent();
    renderFormPane();
    renderPreviewNow();
    return;
  }
  updatePreview();
}
function bindText(key, val){ state[key] = val; updatePreview(); }

/* The .md save/import experiment (V33-V34) was removed in V35. It round-tripped
   the whole sheet as editable Markdown, which read beautifully and was lossy in
   three places that matter: hand-tuned timing lights, flex ranges, and a custom
   segment's binding to a custom role. A JSON round trip loses nothing. Two
   formats where one autosaves on every keystroke meant the readable one would
   quietly degrade a meeting every time it was reopened, and the first person to
   notice would be the Timer, on the night. One format, exact - Rama's call. */

function bindVoting(key, val){
  if(!state.meeting.voting) state.meeting.voting = {link:'', codes:{}};
  if(key === 'link') state.meeting.voting.link = val;
  else state.meeting.voting.codes[key] = val;
  syncVotingFromState();
  applyVotingToSegments();
  renderSegmentsList();
  updatePreview();
}

/* ================= Custom roles (V30) =================
   A club role the built-in nine do not cover: the user gives it a title and a
   person, and from there it behaves like any other role — it is introduced in the
   roster under TME Welcome Remarks, it prints a red TBD while unnamed, it appears
   in the still-open list, it can be unticked for a night it is not running, and it
   can hold a Custom Item segment.
   The name lives in state.roles[key] rather than on the role object, so it reaches
   holderFor() and the roster with no new code path (see customRoles() in app.js). */
function renderCustomRoles(){
  const box = document.getElementById('customRoles');
  if(!box) return;
  box.innerHTML = customRoles().map(r=>{
    const on = roleIsActive(r.key);
    return `<div class="cr-row${on?'':' role-off'}" id="rw-${r.key}">
      <input type="checkbox" id="rc-${r.key}"${on?' checked':''}
        onchange="toggleRoleActive('${r.key}', this.checked)"
        aria-label="Include this role tonight">
      <input type="text" class="cr-label" placeholder="Role title, e.g. Zoom Master"
        value="${esc(r.label)}" oninput="updCustomRole('${r.key}','label',this.value)">
      <input type="text" id="r-${r.key}" placeholder="TBD" value="${esc(state.roles[r.key]||'')}"
        ${on?'':'disabled'} oninput="bindRole('${r.key}', this.value)">
      <button class="cr-del" title="Remove this role" aria-label="Remove this role"
        onclick="removeCustomRole('${r.key}')">✕</button>
    </div>`;
  }).join('');
}
function addCustomRole(){
  if(!Array.isArray(state.customRoles)) state.customRoles = [];
  const key = nextCustomRoleKey();
  state.customRoles.push({key, label:''});
  state.roles[key] = '';
  if(!state.roleActive) state.roleActive = {};
  state.roleActive[key] = true;
  renderCustomRoles();
  const el = document.querySelector('#rw-'+key+' .cr-label');
  if(el) el.focus();
  updatePreview();
}
function updCustomRole(key, field, value){
  const r = customRoles().find(x=>x.key===key);
  if(!r) return;
  r[field] = value;
  /* Deliberately no re-render: retyping the label would lose the caret. Only the
     sheet needs to know. */
  updatePreview();
}
function removeCustomRole(key){
  const r = customRoles().find(x=>x.key===key);
  const named = r && (r.label || state.roles[key]);
  if(named && !confirm('Remove ' + (r.label || 'this role') + ' from the meeting?')) return;
  state.customRoles = customRoles().filter(x=>x.key!==key);
  delete state.roles[key];
  if(state.roleActive) delete state.roleActive[key];
  /* A segment pointing at a role that no longer exists would print a permanent
     TBD nobody can fill, so hand those rows back to a typed holder. */
  state.segments.forEach(sg=>{ if(sg.roleKey === key) sg.roleKey = ''; });
  renderCustomRoles();
  renderFormPane();
  updatePreview();
}

/* ================= Speeches & Evaluators ================= */
function speechSegs(){ return state.segments.filter(s=>s.isSpeech); }
/* A speech and its evaluation are paired by position — keep the name in step. */
function mirrorSpeakerToEvaluation(seg){
  const i = speechSegs().indexOf(seg);
  const ev = evalSegs()[i];
  if(ev) ev.speakerName = seg.speakerName;
  return i;
}
const cardPreviewHTML = seg => '<b>' + esc(titleFor(seg)) + '</b><br>' + esc(speechComment(seg));
function refreshCardPreview(seg){
  if(!seg) return;
  /* Found by card id, not by index into the .sc-preview list: a collapsed card
     has no preview node, so the index and the speech no longer line up (V31). */
  const el = document.querySelector(`#speechList .speech-card[data-sp-id="${seg.id}"] .sc-preview`);
  if(el) el.innerHTML = cardPreviewHTML(seg);
}
function evalSegs(){ return state.segments.filter(s=>s.isEvaluation); }

/* Shared by the card dropdown and the on-sheet edit row */
function applyProjectChoice(seg, value){
  const name = String(value||'').trim();
  const exact = ALL_PROJECTS.find(n => n.toLowerCase() === name.toLowerCase());
  seg.project = exact || name;
  if(!exact) return;
  // If this project sits at a different level of the chosen pathway, follow it there.
  const where = levelOfProjectIn(seg.pathway, exact);
  if(where) seg.pLevel = where.level;
  const info = projectInfo(exact);
  if(info && info.min != null){
    seg.signalMin = info.min;
    seg.signalMax = info.max;
    seg.signalMid = Math.round(((info.min + info.max) / 2) * 2) / 2;
    seg.signalSpan = info.max - info.min;
    seg.durMin = slotForSignals(info.max);
    seg.signalsManual = false;   /* a fresh project re-links the lights */
  }
}

/* ================= Speech cards: collapsed by default (V31) =================
   Four speeches, each a dozen fields, made the section a wall the moment it was
   opened. Cards now collapse like the Programme Segments rows do, and open one at
   a time; the head carries enough to work from without opening anything - who is
   speaking, and the project or a prompt for it. Nothing is remembered across a
   reload on purpose: this is a view preference, not part of the meeting. */
const expandedSpeeches = new Set();
function toggleSpeech(id){
  expandedSpeeches.has(id) ? expandedSpeeches.delete(id) : expandedSpeeches.add(id);
  renderSpeechCards();
}
/* One line of head summary, so a shut card still says something useful. */
function speechHeadSummary(seg, ev){
  const bits = [];
  bits.push(seg.project ? seg.project : 'no project yet');
  if(seg.durMin) bits.push(seg.durMin + ' min');
  bits.push('Ev: ' + ((ev && ev.holderOverride) || 'TBD'));
  return bits.join(' · ');
}

/* The +/- stepper in the section header. Adding pushes a speech AND its paired
   evaluation; removing takes the LAST pair, so the ones already filled in are
   never the ones that disappear. Four is the club standard and the number the
   blank template's exact 150 minutes is built on, so moving off it will make the
   end-check complain - that is correct, not a bug. */
const MIN_SPEECHES = 1, MAX_SPEECHES = 8;
function stepSpeechCount(delta){
  setSpeechCount(speechSegs().length + delta);
}
function setSpeechCount(n){
  const want = Math.max(MIN_SPEECHES, Math.min(MAX_SPEECHES, Math.round(Number(n) || 0)));
  let have = speechSegs().length;
  if(want === have) return;
  while(have < want){ addSpeechSlot(true); have++; }
  while(have > want){
    const last = speechSegs()[have-1];
    if(!last) break;
    removeSpeechSlot(last.id, true);
    have--;
  }
  rebalanceFlexSilent();
  renderFormPane();
  renderPreviewNow();
  updateSpeechCount();
  showBanner(want + ' prepared speech' + (want===1?'':'es') + ' tonight, each with its own evaluation.'
    + (want === 4 ? '' : ' Check the end time - the club standard is four.'), want !== 4);
}
function updateSpeechCount(){
  const el = document.getElementById('spCount');
  if(el) el.textContent = speechSegs().length;
  const dec = document.getElementById('spDec'), inc = document.getElementById('spInc');
  if(dec) dec.disabled = speechSegs().length <= MIN_SPEECHES;
  if(inc) inc.disabled = speechSegs().length >= MAX_SPEECHES;
}

function renderSpeechCards(){
  const container = document.getElementById('speechList');
  if(!container) return;
  updateSpeechCount();
  const speeches = speechSegs();
  const evals = evalSegs();
  container.innerHTML = speeches.map((seg, i)=>{
    const ev = evals[i];
    const info = seg.project ? projectInfo(seg.project) : null;
    const pathOpts = ['<option value="">— pathway —</option>'].concat(
      PATHWAYS_DATA.paths.map(p=>`<option value="${p.abbr}"${seg.pathway===p.abbr?' selected':''}>${p.abbr} — ${p.name}</option>`)
    ).join('');
    const lvlOpts = ['<option value="">—</option>'].concat(
      [1,2,3,4,5].map(l=>`<option value="${l}"${String(seg.pLevel)===String(l)?' selected':''}>L${l}</option>`)
    ).join('');
    const timingNote = info && info.note ? `<div class="sc-note">${esc(info.note)}</div>` : '';
    const mm = projectTimingMismatch(seg);
    const mismatchNote = mm
      ? `<div class="sc-warn">Lights are ${seg.signalMin}–${seg.signalMax} min but ${esc(seg.project)} officially runs ${mm.min}–${mm.max} min. <button class="ls-relink" onclick="resetToProjectTiming('${seg.id}')">↺ use ${mm.min}–${mm.max}</button></div>`
      : '';
    const altBtn = info && info.alt
      ? `<button class="sc-alt" onclick="applyAltTiming('${seg.id}')" title="Switch to the alternative timing">${esc(info.alt.label)}</button>`
      : '';
    const open = expandedSpeeches.has(seg.id);
    return `<div class="speech-card${open?' open':''}" data-sp-id="${seg.id}" draggable="false"
        ondragstart="spDragStart(event,'${seg.id}')" ondragover="spDragOver(event,'${seg.id}')"
        ondragleave="spDragLeave(event)" ondrop="spDrop(event,'${seg.id}')" ondragend="spDragEnd(event)">
      <div class="sc-head" onclick="toggleSpeech('${seg.id}')">
        <span class="sc-grip" title="Drag to reorder speakers" onmousedown="dragArm(this)" onclick="event.stopPropagation()">⠿</span>
        <span class="sc-badge">Speech ${i+1}</span>
        <span class="sc-name">${esc(seg.speakerName || '—')}</span>
        <span class="sc-sum">${esc(speechHeadSummary(seg, ev))}</span>
        <button class="sc-remove" title="Remove this speech and its evaluation" onclick="event.stopPropagation(); removeSpeechSlot('${seg.id}')">✕</button>
        <span class="caret">${open ? '▴' : '▾'}</span>
      </div>
      <div class="sc-details">${!open ? '' : `
      <div class="row2">
        <div><label>Speaker</label><input type="text" placeholder="Speaker name" value="${esc(seg.speakerName)}" oninput="updSpeech('${seg.id}','speakerName',this.value)"></div>
        <div><label>Evaluator</label><input type="text" placeholder="TBD" value="${esc(ev ? ev.holderOverride : '')}" oninput="updEvaluator(${i}, this.value)"${ev?'':' disabled title="No paired evaluation segment"'}></div>
      </div>
      <div class="sc-projrow">
        <div><label>Pathway</label><select onchange="updSpeechCatalog('${seg.id}','pathway',this.value)">${pathOpts}</select></div>
        <div><label>Level</label><select onchange="updSpeechCatalog('${seg.id}','pLevel',this.value)">${lvlOpts}</select></div>
        <div class="sc-proj"><label>Project <span class="lbl-hint">(every project — click ▾ or type)</span></label>
          ${projectComboHTML(seg, 'card')}
        </div>
      </div>
      <label>Speech title</label>
      <input type="text" placeholder="Speech title" value="${esc(seg.speechTitle)}" oninput="updSpeech('${seg.id}','speechTitle',this.value)">
      <div class="sc-preview">${cardPreviewHTML(seg)}</div>
      <div class="row4">
        <div><label>Slot (min)</label>
          <input type="number" min="0" step="0.5" inputmode="decimal" data-f="durMin"
                 value="${seg.durMin}" oninput="updSpeech('${seg.id}','durMin',this.value)"></div>
        <div><label><span class="dot g"></span> Green at</label>
          <input type="number" min="0" step="0.5" inputmode="decimal" data-f="signalMin"
                 value="${seg.signalMin}" oninput="updSpeech('${seg.id}','signalMin',this.value)"></div>
        <div><label><span class="dot y"></span> Amber at</label>
          <input type="number" min="0" step="0.5" inputmode="decimal" data-f="signalMid"
                 value="${midOf(seg)}" oninput="updSpeech('${seg.id}','signalMid',this.value)"></div>
        <div><label><span class="dot r"></span> Red at</label>
          <input type="number" min="0" step="0.5" inputmode="decimal" data-f="signalMax"
                 value="${seg.signalMax}" oninput="updSpeech('${seg.id}','signalMax',this.value)"></div>
      </div>
      <div class="sc-lightstate">${lightStateHTML(seg)}</div>
      ${mismatchNote}${timingNote}${altBtn}`}</div>
    </div>`;
  }).join('') || '<div class="hint">No speeches yet — use + in the section header.</div>';
}

function lightStateHTML(seg){
  return seg.signalsManual
    ? `<span class="ls-manual">Lights set manually</span> <button class="ls-relink" onclick="relinkSignals('${seg.id}')">↺ follow the slot again</button>`
    : `<span class="ls-auto">Lights follow the slot (red at slot − ${TRANSITION_MIN} min)</span>`;
}
/* Manual edit to any light both flags the segment and re-anchors the span. */
function markSignalsManual(seg){
  seg.signalsManual = true;
  seg.signalSpan = Math.max(0, (Number(seg.signalMax)||0) - (Number(seg.signalMin)||0));
}
/* Push recomputed light values into a card's inputs WITHOUT re-rendering it —
   re-rendering mid-keystroke would destroy the field being typed into. */
function syncCardTimingInputs(seg){
  const card = document.querySelector(`.speech-card[data-sp-id="${seg.id}"]`);
  if(!card) return;
  /* durMin included: editing the slot over in Programme Segments used to leave
     this card showing the old number (Rama, V21). */
  [['durMin', seg.durMin], ['signalMin', seg.signalMin], ['signalMid', midOf(seg)], ['signalMax', seg.signalMax]].forEach(([f,v])=>{
    const el = card.querySelector(`input[data-f="${f}"]`);
    if(el && document.activeElement !== el) el.value = v;
  });
  const st = card.querySelector('.sc-lightstate');
  if(st) st.innerHTML = lightStateHTML(seg);
}
/* The mirror of the above: push a speech's numbers back into its row in the
   Programme Segments list, so the two panes never disagree whichever one you
   typed into. Only touches an expanded card, and never the focused field. */
function syncSegCardInputs(seg){
  const card = document.querySelector(`.seg-card[data-seg-id="${seg.id}"]`);
  if(!card) return;
  const inputs = card.querySelectorAll('.seg-details input[type="number"]');
  const vals = seg.isSpeech || seg.isEvaluation
    ? [seg.durMin]
    : [seg.durMin, seg.signalMin, midOf(seg), seg.signalMax];
  inputs.forEach((el, i) => {
    if(vals[i] != null && document.activeElement !== el) el.value = vals[i];
  });
}
function relinkSignals(id){
  const seg = state.segments.find(s=>s.id===id);
  if(!seg) return;
  seg.signalsManual = false;
  const info = seg.project ? projectInfo(seg.project) : null;
  if(info && info.min != null){
    seg.signalMin = info.min; seg.signalMax = info.max; seg.signalSpan = info.max - info.min;
  }
  autoSignalsFromSlot(seg);
  afterTimingReset();
}
function afterTimingReset(){
  renderSpeechCards();
  updatePreview();
}
function resetToProjectTiming(id){
  const seg = state.segments.find(s=>s.id===id);
  const info = seg && seg.project ? projectInfo(seg.project) : null;
  if(!info || info.min == null) return;
  seg.signalMin = info.min;
  seg.signalMax = info.max;
  seg.signalMid = Math.round(((info.min + info.max)/2) * 2) / 2;
  seg.signalSpan = info.max - info.min;
  seg.durMin = slotForSignals(info.max);
  seg.signalsManual = false;
  afterTimingReset();
}

function updSpeech(id, key, value){
  const seg = state.segments.find(s=>s.id===id);
  if(!seg) return;
  const numeric = ['durMin','signalMin','signalMid','signalMax'];
  seg[key] = numeric.includes(key) ? (value===''?0:parseFloat(value)) : value;
  if(['signalMin','signalMid','signalMax'].includes(key)){
    markSignalsManual(seg);
    syncCardTimingInputs(seg);
  } else if(key === 'durMin'){
    if(autoSignalsFromSlot(seg)) syncCardTimingInputs(seg);
  }
  /* Push the numbers back to this segment's row in Programme Segments — the
     other half of the two-way sync. */
  if(['durMin','signalMin','signalMid','signalMax'].includes(key)) syncSegCardInputs(seg);
  if(key === 'speakerName'){
    const i = mirrorSpeakerToEvaluation(seg);
    const nameEl = document.querySelectorAll('#speechList .sc-name')[i];
    if(nameEl) nameEl.textContent = seg.speakerName || '—';
  }
  refreshCardPreview(seg);
  updatePreview();
}
function updEvaluator(i, value){
  const ev = evalSegs()[i];
  if(ev){
    ev.holderOverride = value;
    refreshCardPreview(speechSegs()[i]);
    updatePreview();
  }
}
function updSpeechCatalog(id, key, value){
  const seg = state.segments.find(s=>s.id===id);
  if(!seg) return;
  seg[key] = value;
  if(seg.project && !levelOfProjectIn(seg.pathway, seg.project)) seg.project = '';
  renderSpeechCards();
  updatePreview();
}
function updSpeechProject(id, value){
  const seg = state.segments.find(s=>s.id===id);
  if(!seg) return;
  applyProjectChoice(seg, value);
  renderSpeechCards();
  updatePreview();
}
function applyAltTiming(id){
  const seg = state.segments.find(s=>s.id===id);
  const info = seg && seg.project && projectInfo(seg.project);
  if(!info || !info.alt) return;
  seg.signalMin = info.alt.min;
  seg.signalMax = info.alt.max;
  seg.signalMid = Math.round(((info.alt.min + info.alt.max) / 2) * 2) / 2;
  seg.signalSpan = info.alt.max - info.alt.min;
  seg.durMin = slotForSignals(info.alt.max);
  seg.signalsManual = false;
  renderSpeechCards();
  updatePreview();
}

/* Reorder speakers: move speech i → j, and move its paired evaluation with it,
   keeping both sets in their existing slots in the running order. */
function reorderSpeech(fromId, toId, after){
  const speeches = speechSegs(), evals = evalSegs();
  const from = speeches.findIndex(s=>s.id===fromId);
  let to = speeches.findIndex(s=>s.id===toId);
  if(from < 0 || to < 0 || from === to) return;
  if(after) to += 1;
  if(to > from) to -= 1;

  const spPos = speeches.map(s => state.segments.indexOf(s));
  const evPos = evals.map(s => state.segments.indexOf(s));

  const spOrder = speeches.slice();
  spOrder.splice(to, 0, spOrder.splice(from, 1)[0]);
  const evOrder = evals.slice();
  if(evals.length === speeches.length){
    evOrder.splice(to, 0, evOrder.splice(from, 1)[0]);
  }
  spPos.forEach((pos, i) => { state.segments[pos] = spOrder[i]; });
  evPos.forEach((pos, i) => { state.segments[pos] = evOrder[i]; });

  renderFormPane();
  renderPreviewNow();
}

let spDragId = null;
function spDragStart(e, id){
  spDragId = id;
  e.dataTransfer.effectAllowed = 'move';
  e.currentTarget.classList.add('dragging');
}
function spDragOver(e, id){
  if(!spDragId || id === spDragId) return;
  e.preventDefault();
  e.dataTransfer.dropEffect = 'move';
  const r = e.currentTarget.getBoundingClientRect();
  const below = (e.clientY - r.top) > r.height/2;
  e.currentTarget.classList.toggle('drop-below', below);
  e.currentTarget.classList.toggle('drop-above', !below);
}
function spDragLeave(e){ e.currentTarget.classList.remove('drop-above','drop-below'); }
function spDrop(e, id){
  e.preventDefault();
  const after = e.currentTarget.classList.contains('drop-below');
  e.currentTarget.classList.remove('drop-above','drop-below');
  if(spDragId && spDragId !== id) reorderSpeech(spDragId, id, after);
  spDragId = null;
}
function spDragEnd(){
  spDragId = null;
  dragDisarm();
  document.querySelectorAll('.speech-card').forEach(c=>c.classList.remove('dragging','drop-above','drop-below'));
}

/* quiet=true is the stepper adding several at once — it redraws once at the end
   rather than after every pair. */
function addSpeechSlot(quiet){
  const speeches = speechSegs();
  const sp = newSegment('speech');
  const lastSp = speeches[speeches.length-1];
  state.segments.splice(lastSp ? state.segments.indexOf(lastSp)+1 : state.segments.length, 0, sp);

  const evals = evalSegs();
  const ev = newSegment('evaluation');
  const lastEv = evals[evals.length-1];
  state.segments.splice(lastEv ? state.segments.indexOf(lastEv)+1 : state.segments.length, 0, ev);

  if(quiet) return;
  renderFormPane();
  updatePreview();
}
function removeSpeechSlot(id, quiet){
  const i = speechSegs().findIndex(s=>s.id===id);
  if(i < 0) return;
  const ev = evalSegs()[i];
  state.segments = state.segments.filter(s=>s.id!==id && (!ev || s.id!==ev.id));
  expandedSpeeches.delete(id);
  if(quiet) return;
  renderFormPane();
  updatePreview();
}

/* ================= Programme Segments list ================= */
const expandedSegs = new Set();
let dragSrcId = null;

function segFieldsHTML(seg){
  if(seg.isSpeech || seg.isEvaluation){
    return `<div class="hint">Speaker, project and evaluator live in <b>Speeches &amp; Evaluators</b> above.</div>
      <label>Slot (min)</label><input type="number" min="0" step="0.5" inputmode="decimal" value="${seg.durMin}" oninput="updateSeg('${seg.id}','durMin',this.value)">`;
  }
  let fields = `
    <label>Title</label>
    <input type="text" placeholder="Segment title" value="${esc(seg.title)}" oninput="updateSeg('${seg.id}','title',this.value)">
    <label>Sub-note (optional) <span class="lbl-hint">(each line prints as its own line)</span></label>
    <textarea rows="2" placeholder="Detail line printed under the title" oninput="updateSeg('${seg.id}','sub',this.value)">${esc(seg.sub)}</textarea>`;
  if(!seg.noHolder){
    fields += `
    <label>Holder ${seg.roleKey ? '(auto from roles; type to override)' : ''}</label>
    <input type="text" placeholder="${seg.roleKey ? (state.roles[seg.roleKey] || 'TBD') : 'TBD'}" value="${esc(seg.holderOverride)}" oninput="updateSeg('${seg.id}','holderOverride',this.value)">`;
  }
  if(seg.flexible){
    fields += `
    <div class="row3">
      <div><label>Nominal (min)</label><input type="number" min="0" step="0.5" inputmode="decimal" value="${seg.durMin}" oninput="updateSeg('${seg.id}','durMin',this.value)"></div>
      <div><label>Flex min</label><input type="number" min="0" step="0.5" inputmode="decimal" value="${seg.flexMin}" oninput="updateSeg('${seg.id}','flexMin',this.value)"></div>
      <div><label>Flex max</label><input type="number" min="0" step="0.5" inputmode="decimal" value="${seg.flexMax}" oninput="updateSeg('${seg.id}','flexMax',this.value)"></div>
    </div>`;
  } else if(seg.hasSignal){
    fields += `
    <div class="row4">
      <div><label>Duration</label><input type="number" min="0" step="0.5" inputmode="decimal" value="${seg.durMin}" oninput="updateSeg('${seg.id}','durMin',this.value)"></div>
      <div><label><span class="dot g"></span> Green</label><input type="number" min="0" step="0.5" inputmode="decimal" value="${seg.signalMin}" oninput="updateSeg('${seg.id}','signalMin',this.value)"></div>
      <div><label><span class="dot y"></span> Amber</label><input type="number" min="0" step="0.5" inputmode="decimal" value="${midOf(seg)}" oninput="updateSeg('${seg.id}','signalMid',this.value)"></div>
      <div><label><span class="dot r"></span> Red</label><input type="number" min="0" step="0.5" inputmode="decimal" value="${seg.signalMax}" oninput="updateSeg('${seg.id}','signalMax',this.value)"></div>
    </div>`;
  } else {
    fields += `<label>Duration (min)</label><input type="number" min="0" step="0.5" inputmode="decimal" value="${seg.durMin}" oninput="updateSeg('${seg.id}','durMin',this.value)">`;
  }
  return fields;
}

function ownerRoleOf(presetKey){
  const hit = Object.entries(ROLE_OWNED_SEGMENTS).find(([,ps]) => ps.includes(presetKey));
  return hit ? hit[0] : null;
}
function renderSegmentsList(){
  const container = document.getElementById('segList');
  if(!container) return;
  const {clockById} = computeSchedule();
  container.innerHTML = state.segments.map((seg) => {
    const open = expandedSegs.has(seg.id);
    const owner = seg.disabled ? ownerRoleOf(seg.presetKey) : null;
    return `<div class="seg-card${seg.flexible?' is-flex':''}${open?' open':''}${seg.disabled?' is-off':''}" data-seg-id="${seg.id}" draggable="false"
        ondragstart="segDragStart(event,'${seg.id}')" ondragover="segDragOver(event,'${seg.id}')"
        ondragleave="segDragLeave(event)" ondrop="segDrop(event,'${seg.id}')" ondragend="segDragEnd(event)">
      <div class="seg-top" onclick="toggleSeg('${seg.id}')">
        <span class="drag-handle" title="Drag to reorder" onmousedown="dragArm(this)" onclick="event.stopPropagation()">⠿</span>
        <span class="seg-badge">${seg.disabled ? 'off' : (seg.flexible ? 'flex' : (seg.hasSignal ? 'timed' : 'fixed'))}</span>
        <span class="seg-title">${esc(titleFor(seg))}${owner?` <span class="off-why">— ${esc(ROLE_LABELS[owner])} not running</span>`:''}</span>
        <span class="seg-time">${seg.disabled ? '—' : (clockById[seg.id] || '')}</span>
        <div class="seg-actions" onclick="event.stopPropagation()">
          <button title="Move up" onclick="moveSeg('${seg.id}',-1)">▲</button>
          <button title="Move down" onclick="moveSeg('${seg.id}',1)">▼</button>
          <button title="Remove" class="danger" onclick="removeSeg('${seg.id}')">✕</button>
        </div>
        <span class="caret">${open ? '▴' : '▾'}</span>
      </div>
      <div class="seg-details">${open ? segFieldsHTML(seg) : ''}</div>
    </div>`;
  }).join('');
}

function renderFormPane(){
  renderSegmentsList();
  renderSpeechCards();
}

function toggleSeg(id){
  expandedSegs.has(id) ? expandedSegs.delete(id) : expandedSegs.add(id);
  renderSegmentsList();
}

/* ================= Drag arming =================
   The cards used to carry draggable="true" on the whole card. In Chrome a
   draggable ancestor swallows the mousedown gesture inside its descendant
   <input>s: the field still takes focus, but you cannot click to place the
   caret and you cannot drag-select — only the arrow keys move you through the
   text. That is exactly what Rama hit (V21).
   So the card is inert by default and is armed for dragging only while the ⠿
   grip is held; every mouseup and dragend disarms it again. Reordering works
   as before, but only from the grip, which is what its tooltip already said. */
function dragArm(grip){
  const card = grip.closest('.seg-card, .speech-card');
  if(card) card.draggable = true;
}
function dragDisarm(){
  document.querySelectorAll('.seg-card[draggable="true"], .speech-card[draggable="true"]')
    .forEach(c => { c.draggable = false; });
}
document.addEventListener('mouseup', dragDisarm);

function segDragStart(e, id){
  dragSrcId = id;
  e.dataTransfer.effectAllowed = 'move';
  e.currentTarget.classList.add('dragging');
}
function segDragOver(e, id){
  e.preventDefault();
  e.dataTransfer.dropEffect = 'move';
  if(id !== dragSrcId) e.currentTarget.classList.add('drag-over');
}
function segDragLeave(e){ e.currentTarget.classList.remove('drag-over'); }
function segDrop(e, targetId){
  e.preventDefault();
  e.currentTarget.classList.remove('drag-over');
  if(!dragSrcId || dragSrcId === targetId) return;
  const from = state.segments.findIndex(s=>s.id===dragSrcId);
  const to = state.segments.findIndex(s=>s.id===targetId);
  if(from < 0 || to < 0) return;
  const [item] = state.segments.splice(from,1);
  state.segments.splice(to,0,item);
  renderFormPane();
  updatePreview();
}
function segDragEnd(){
  dragSrcId = null;
  dragDisarm();
  document.querySelectorAll('.seg-card').forEach(c=>c.classList.remove('dragging','drag-over'));
}

function updateSeg(id, key, value){
  const seg = state.segments.find(s=>s.id===id);
  if(!seg) return;
  seg[key] = ['durMin','flexMin','flexMax','signalMin','signalMid','signalMax'].includes(key)
    ? (value === '' ? 0 : parseFloat(value)) : value;
  if(['signalMin','signalMid','signalMax'].includes(key)) markSignalsManual(seg);
  /* Same slot→lights auto-split the Speeches pane applies, so the two panes
     behave identically instead of diverging depending on where you typed. */
  else if(key === 'durMin' && seg.hasSignal) autoSignalsFromSlot(seg);
  /* Mirror the change into the Speeches & Evaluators card. Without this the
     card kept showing the old slot and lights (Rama, V21). */
  if(seg.isSpeech){
    syncCardTimingInputs(seg);
    refreshCardPreview(seg);
  } else if(seg.isEvaluation){
    const i = evalSegs().findIndex(e => e.id === seg.id);
    if(i >= 0) refreshCardPreview(speechSegs()[i]);
  }
  updatePreview();
  const {clockById} = computeSchedule();
  document.querySelectorAll('#segList .seg-card').forEach((card)=>{
    const sg = state.segments.find(x=>x.id===card.dataset.segId);
    if(!sg) return;
    const timeEl = card.querySelector('.seg-time');
    if(timeEl) timeEl.textContent = sg.disabled ? '—' : (clockById[sg.id] || '');
  });
}
function moveSeg(id, dir){
  const idx = state.segments.findIndex(s=>s.id===id);
  const newIdx = idx + dir;
  if(newIdx < 0 || newIdx >= state.segments.length) return;
  const [item] = state.segments.splice(idx,1);
  state.segments.splice(newIdx,0,item);
  renderFormPane();
  renderPreviewNow();
}
function removeSeg(id){
  if(editingSegId === id) editingSegId = null;
  state.segments = state.segments.filter(s=>s.id!==id);
  expandedSegs.delete(id);
  renderFormPane();
  renderPreviewNow();
}
/* atTop: the copy of this control that sits ABOVE the running order. A pre-
   meeting item - guest registration, a committee huddle, a contest briefing -
   belongs at the front, and scrolling past twenty-five rows to reach the Add
   button and then dragging the new row all the way back up was the whole cost.
   The bar at the foot still appends, so both ends of the meeting are one click. */
function addSeg(atTop){
  const sel = document.getElementById(atTop ? 'addSegTypeTop' : 'addSegType');
  const seg = newSegment(sel.value);
  if(atTop) state.segments.unshift(seg); else state.segments.push(seg);
  expandedSegs.add(seg.id);
  renderSegmentsList();
  updatePreview();
  const card = document.querySelector(`.seg-card[data-seg-id="${seg.id}"]`);
  if(card) card.scrollIntoView({behavior:'smooth', block:'center'});
}

/* ================= Apply the club standard to an existing meeting =================
   New PRESETS durations only reach a meeting that is built fresh, and Reset
   throws away everything Rama has typed. This retimes the segments already in
   the running order to the club standard, in place: durations, the combined
   timer's-report-and-vote titles and their Slido notes, nothing else. Names,
   speakers, evaluators, projects, order and any extra segments are untouched.
   Lights follow the new slot only where they were still following it. */
const STANDARD_KEYS = ['calltoorder','welcome','president','returncontrol','speechvote',
  'ttmasterintro','ttreturn','ttvote','peintro','evaluation','evalvote','awards','closing','photo','adjourn'];
/* Pre-V21 rows that became one of the combined vote rows. */
const VOTE_MIGRATION = { timerreport:'speechvote', voting:'speechvote', ttvoting:'ttvote', pevoting:'evalvote' };

function applyStandardTimings(){
  if(!confirm('Retime this meeting to the club standard?\n\n'
    + 'Durations, the combined timer’s-report/voting rows and their Slido codes are reset.\n'
    + 'Names, speakers, evaluators, projects and the running order are left alone.')) return;

  let retimed = 0, merged = 0;
  const seen = new Set();
  const keep = [];

  state.segments.forEach(seg => {
    /* Fold a pre-V21 split pair down to the single combined row. The first one
       through becomes the combined row; its now-redundant partner is dropped. */
    const target = VOTE_MIGRATION[seg.presetKey];
    if(target){
      if(seen.has(target)){ merged++; return; }
      seen.add(target);
      seg.presetKey = target;
    }
    keep.push(seg);
  });
  state.segments = keep;

  state.segments.forEach(seg => {
    const p = PRESETS[seg.presetKey];
    if(!p || !STANDARD_KEYS.includes(seg.presetKey)) return;
    /* V27 rehomed these rows (ttreturn/awards -> TME, photo -> "All", awards
       grew its three-line sub). Pull a saved meeting up to that without
       touching anything the user typed. */
    if(['ttreturn','awards','photo'].includes(seg.presetKey)){
      seg.roleKey = p.roleKey || '';
      seg.noHolder = !!p.noHolder;
      if(seg.presetKey === 'awards' && !seg.sub) seg.sub = p.sub;
      if(seg.presetKey === 'photo' && !seg.holderOverride) seg.holderOverride = p.fixedHolder;
    }
    const wasAuto = !seg.signalsManual;
    if(seg.durMin !== p.durMin){ seg.durMin = p.durMin; retimed++; }
    /* Only the combined vote rows carry a standard title/sub — everything else
       keeps whatever wording is already on the sheet. */
    if(p.voteKey){
      seg.title = p.label;
      /* Built from the club's current voting link and codes, not from a constant
         baked into PRESETS - another club's codes must survive a retime. */
      seg.sub = votingNote(p.voteKey);
      seg.noHolder = false;
      seg.roleKey = p.roleKey || '';
    }
    if(seg.hasSignal && wasAuto) autoSignalsFromSlot(seg);
  });

  syncRoleSegments();
  renderFormPane();
  updatePreview();
  const {rows} = computeSchedule();
  showBanner(`Retimed to the club standard — ${retimed} segment${retimed===1?'':'s'} changed`
    + (merged ? `, ${merged} timer/voting row${merged===1?'':'s'} merged` : '')
    + `. Check the end time and use ⚖ Balance if it drifted.`, false);
}

/* ================= Banner ================= */
function showBanner(msg, isWarn){
  const b = document.getElementById('banner');
  b.textContent = msg;
  b.style.display = 'block';
  b.style.background = isWarn ? '#fdeeec' : '#e6f3ea';
  b.style.color = isWarn ? '#9c3b33' : '#2e7d46';
  clearTimeout(showBanner._t);
  showBanner._t = setTimeout(()=>{ b.style.display='none'; }, 5000);
}

/* ================= Resizable split ================= */
function applyPaneWidth(){
  const w = Math.min(80, Math.max(20, Number(state.paneWidth) || 50));
  state.paneWidth = w;
  const pane = document.querySelector('.form-pane');
  if(pane) pane.style.flexBasis = w + '%';
}
function initSplitter(){
  const splitter = document.getElementById('splitter');
  const body = document.querySelector('.builder-body');
  if(!splitter || !body) return;
  let dragging = false;
  const onMove = (e)=>{
    if(!dragging) return;
    const rect = body.getBoundingClientRect();
    const pct = ((e.clientX - rect.left) / rect.width) * 100;
    state.paneWidth = Math.min(80, Math.max(20, pct));
    applyPaneWidth();
  };
  const onUp = ()=>{
    if(!dragging) return;
    dragging = false;
    document.body.classList.remove('resizing');
    queueSave();
  };
  splitter.addEventListener('mousedown', (e)=>{
    dragging = true;
    document.body.classList.add('resizing');
    e.preventDefault();
  });
  document.addEventListener('mousemove', onMove);
  document.addEventListener('mouseup', onUp);
  splitter.addEventListener('dblclick', ()=>{ state.paneWidth = 50; applyPaneWidth(); queueSave(); });
}

/* ================= Narrow / phone layout (V30) =================
   Below NARROW_PX the two panes stop being side by side. Splitting a 380px phone
   into a form and a preview left both unusable, and the old rule only capped the
   form at 70vh, which meant the preview was always somewhere below the fold.
   Now it is one column at a time: the form fills the screen, and ✎ Edit / 👁 Preview
   swaps to the sheet. The preview is only rendered when it is actually shown, so a
   phone is not rasterising an iframe it cannot see on every keystroke.
   This is a viewport fact, not a meeting fact, so it is deliberately NOT in state -
   it must not travel in the .json to someone else's desktop. */
const NARROW_PX = 900;
let mobileView = 'edit';
function isNarrow(){ return window.matchMedia('(max-width: ' + NARROW_PX + 'px)').matches; }
function setMobileView(view){
  mobileView = (view === 'preview') ? 'preview' : 'edit';
  document.body.classList.toggle('show-preview', mobileView === 'preview');
  document.querySelectorAll('[data-view]').forEach(b=>{
    const on = b.dataset.view === mobileView;
    b.classList.toggle('on', on);
    b.setAttribute('aria-pressed', on ? 'true' : 'false');
  });
  /* Coming back to the sheet after editing behind it: redraw before it is seen. */
  if(mobileView === 'preview') renderPreviewNow();
  window.scrollTo(0, 0);
}
function initNarrowLayout(){
  setMobileView('edit');
  /* Rotating a phone, or dragging a desktop window narrow, must not strand the
     user on a hidden pane. */
  window.addEventListener('resize', ()=>{
    if(!isNarrow() && mobileView === 'preview') setMobileView('edit');
  });
}

/* ================= Print / download (clean sheet only) ================= */
function downloadSheet(){
  const blob = new Blob([buildSheetHTML(false)], {type:'text/html'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = sheetFileStem() + '.html';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(()=>URL.revokeObjectURL(url), 2000);
}

/* ================= Init ================= */
function syncFormInputs(){
  /* Custom-role rows must exist before the loop below tries to fill them. */
  renderCustomRoles();
  lastClubName = state.meeting.clubName;
  const set = (id, v) => { const el = document.getElementById(id); if(el) el.value = v; };
  set('f-clubName', state.meeting.clubName);
  set('f-clubNumber', state.meeting.clubNumber);
  set('f-clubInitials', state.meeting.clubInitials);
  set('f-orgLine', state.meeting.orgLine);
  set('f-cadence', state.meeting.cadence);
  set('f-title', state.meeting.title);
  set('f-dateDisplay', state.meeting.dateDisplay);
  set('f-location', state.meeting.location);
  set('f-startTime', state.meeting.startTime);
  set('f-endTime', state.meeting.endTime);
  set('f-footerNote', state.meeting.footerNote);
  const th = document.getElementById('f-theme');
  if(th){
    th.innerHTML = THEMES.map(t=>`<option value="${t.key}"${(state.theme||'classic')===t.key?' selected':''}>${t.name}</option>`).join('');
  }
  for(const key of Object.keys(state.roles)){
    set('r-'+key, state.roles[key]);
    const on = roleIsActive(key);
    const cb = document.getElementById('rc-'+key);
    if(cb) cb.checked = on;
    const input = document.getElementById('r-'+key);
    if(input) input.disabled = !on;
    const wrap = document.getElementById('rw-'+key);
    if(wrap) wrap.classList.toggle('role-off', !on);
  }
  const v = state.meeting.voting || {codes:{}};
  set('f-votingLink', v.link || '');
  set('f-voteSpeech', (v.codes||{}).speechvote || '');
  set('f-voteTT', (v.codes||{}).ttvote || '');
  set('f-voteEval', (v.codes||{}).evalvote || '');
  set('f-execText', state.execText);
  set('f-districtText', state.districtText);
  set('f-linksText', state.linksText);
  set('f-announcementsText', state.announcementsText);
}
window.addEventListener('DOMContentLoaded', ()=>{
  /* Hides the Print icon on phones and retargets the PDF entry — iOS Safari
     cannot print from a hidden iframe, so the button was doing nothing there. */
  if(IS_TOUCH_DEVICE) document.body.classList.add('touch-device');
  /* Try to re-attach the meetings folder without a prompt. If the browser has
     forgotten the grant, the dropdown offers to reconnect on click - permission
     can only be re-requested from a user gesture. */
  ensureFolder(false).then(reattachFile).then(refreshFileList).catch(()=>refreshFileList());
  const hl = document.getElementById('hdrLogo');
  if(hl) hl.src = 'data:image/png;base64,' + LOGO_B64;
  const restored = loadState();
  const c1 = syncLanguageEvaluatorSegment(), c2 = syncRoleSegments();
  if(c1 || c2) rebalanceFlexSilent();
  applyPaneWidth();
  initSplitter();
  initNarrowLayout();
  syncFormInputs();
  renderFormPane();
  renderPreviewNow();
  if(!storageOK){
    setSaveStatus('Not saved — browser storage unavailable here', true, true);
  } else if(restored){
    const when = typeof restored === 'string' ? new Date(restored) : null;
    setSaveStatus('Restored' + (when ? ' from ' + when.toLocaleString() : '') + ' · autosaving', false, true);
  } else {
    setSaveStatus('Autosaving to this browser', false, true);
  }
});
