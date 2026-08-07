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

/* Ordered choices: the chosen pathway+level first, then the rest of the catalog. */
function projectChoices(seg){
  const inLevel = (seg.pathway && seg.pLevel) ? projectsFor(seg.pathway, seg.pLevel) : [];
  const seen = new Set(inLevel.map(p=>p.n));
  const head = inLevel.map(p=>({
    n: p.n, meta: `${p.e ? 'elective' : 'required'} · ${timingLabel(p.n)}`, here: true }));
  const rest = ALL_PROJECTS.filter(n=>!seen.has(n)).map(n=>{
    const where = seg.pathway ? levelOfProjectIn(seg.pathway, n) : null;
    const tag = where ? `${seg.pathway} L${where.level}` : 'other path';
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
      value="${esc(seg.project)}" placeholder="Click ▾ or type to search all ${ALL_PROJECTS.length} projects…"
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

  const openRolesHtml = openRoles.length
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
<div class="print-fab"><button class="print-btn" onclick="window.print()">🖨 <span class="label">Print / Save PDF</span></button></div>
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
  queueSave();
}
function updatePreview(){
  clearTimeout(previewTimer);
  previewTimer = setTimeout(renderPreviewNow, 150);
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
  if(!el) return;
  el.textContent = isWarn ? '!' : '✓';
  el.title = text;
  el.setAttribute('aria-label', text);
  el.classList.toggle('warn', !!isWarn);
}
function flashSaved(){
  const el = document.getElementById('saveDot');
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
const IMAGE_WIDTH = 900;
const IMAGE_SCALE = 3;
/* Rama shares the sheet on WhatsApp; a 2.6 MB export was unusable. Render big,
   then step DOWN until the JPEG fits this budget. Resolution is dropped before
   quality only when quality alone cannot get there, because on fine type a wider
   image at lower quality still reads better than a small crisp one.
   200 KB (V24) -> 300 KB (V25) -> 450 KB (V26).
   The budget was never the real problem. The ladder tried the WIDEST size first
   and dropped quality to make it fit, so every rise in budget bought more pixels
   at the same grainy quality 0.44 - at 450 KB it went to 2250px and looked no
   cleaner. Grain is bits-per-pixel, not bytes: 5.6 MP at 450 KB is ~0.6 bpp and
   crisp text wants nearer 1.0. So the export is now CAPPED in resolution and the
   budget is spent on quality instead. */
const IMAGE_TARGET_BYTES = 450 * 1024;
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

function sheetFileStem(){
  return (state.meeting.title || 'programme-sheet')
    .replace(/[^a-z0-9]+/gi,'_').replace(/^_+|_+$/g,'') || 'programme-sheet';
}

/* Rasterise the clean sheet once; the PNG, JPG and mobile-PDF paths all use it. */
async function renderSheetCanvas(){
  const h2c = await loadHtml2Canvas();
  let frame = null;
  try{
    frame = document.createElement('iframe');
    frame.setAttribute('aria-hidden','true');
    frame.style.cssText = 'position:fixed;left:-10000px;top:0;border:0;visibility:hidden;'
      + 'width:' + IMAGE_WIDTH + 'px;height:300px;';
    document.body.appendChild(frame);

    /* srcdoc (not document.write) so there is a real load event to wait on. */
    await new Promise((res, rej)=>{
      frame.onload = res;
      frame.onerror = ()=>rej(new Error('frame'));
      frame.srcdoc = buildSheetHTML(false);
    });

    const idoc = frame.contentDocument;
    /* Strip the on-screen paper furniture — drop shadow, rounded corners, the
       grey desk behind the page — so the PNG is just the sheet. */
    const fix = idoc.createElement('style');
    fix.textContent = 'html,body{background:#fff!important;margin:0!important;padding:0!important}'
      + '.page-wrap{padding:0!important;display:block!important}'
      + '.page{box-shadow:none!important;border-radius:0!important;max-width:none!important;width:100%!important}'
      + '.print-fab{display:none!important}'
      /* Images and the phone PDF are deliverables like print, so they follow the
         print rule and drop the FLEXIBLE explainer too. It stays on the live
         preview, which is where it actually helps. */
      + '.schedule-note{display:none!important}';
    idoc.head.appendChild(fix);

    /* Webfonts must be in before rasterising or the type falls back to Arial. */
    if(idoc.fonts && idoc.fonts.ready){
      await Promise.race([idoc.fonts.ready, new Promise(r=>setTimeout(r, 4000))]);
    }
    await new Promise(r=>setTimeout(r, 120));

    const page = idoc.querySelector('.page');
    const h = Math.ceil(page.getBoundingClientRect().height);
    frame.style.height = (h + 40) + 'px';
    await new Promise(r=>setTimeout(r, 60));

    return await h2c(page, {
      scale: IMAGE_SCALE,
      backgroundColor: '#ffffff',
      useCORS: true,
      logging: false,
      width: IMAGE_WIDTH,
      height: h,
      windowWidth: IMAGE_WIDTH,
      windowHeight: h,
    });
  }finally{
    if(frame) frame.remove();
  }
}

/* Stepwise halving beats one big jump — a single drawImage down to 45% aliases
   the 9.5px pane type into mush, three gentle steps do not. */
function downscaleCanvas(src, targetW){
  let cur = src;
  while(cur.width > targetW * 2){
    const c = document.createElement('canvas');
    c.width = Math.max(targetW, Math.round(cur.width / 2));
    c.height = Math.round(cur.height * (c.width / cur.width));
    const x = c.getContext('2d');
    x.imageSmoothingEnabled = true; x.imageSmoothingQuality = 'high';
    x.drawImage(cur, 0, 0, c.width, c.height);
    cur = c;
  }
  if(cur.width === targetW) return cur;
  const c = document.createElement('canvas');
  c.width = targetW;
  c.height = Math.round(cur.height * (targetW / cur.width));
  const x = c.getContext('2d');
  x.imageSmoothingEnabled = true; x.imageSmoothingQuality = 'high';
  x.fillStyle = '#ffffff'; x.fillRect(0, 0, c.width, c.height);
  x.drawImage(cur, 0, 0, c.width, c.height);
  return c;
}

/* Returns the LARGEST encoding that fits the budget, or the smallest we can make
   if nothing does — never silently ships something enormous. */
async function encodeJpegUnder(canvas, target){
  /* Capped, and quality-first within each width: the first fit at the widest
     allowed size is the HIGHEST quality that fits there, not the lowest. */
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
  const btn = document.getElementById('dlBtn');
  if(!btn) return;
  if(on){ btn.disabled = true; btn.dataset.label = btn.dataset.label || btn.textContent; btn.textContent = '⏳'; }
  else  { btn.disabled = false; btn.textContent = btn.dataset.label || '⭳'; }
}

function exportFailed(err, alt){
  showBanner('Could not build the file (' + ((err && err.message) || 'unknown') + '). ' + alt, true);
}

async function downloadImage(){
  busyBtn(true);
  try{
    const canvas = await renderSheetCanvas();
    const out = await encodeJpegUnder(canvas, IMAGE_TARGET_BYTES);
    if(!out) throw new Error('encode');
    saveBlob(out.blob, sheetFileStem() + '.jpg');
    const kb = Math.round(out.blob.size / 1024);
    showBanner('Saved a ' + out.w + '\u00d7' + out.h + ' JPG (' + kb + ' KB).'
      + (out.blob.size > IMAGE_TARGET_BYTES
          ? ' That is over the 200 KB target — the sheet is unusually long this week.' : ''), false);
  }catch(err){
    exportFailed(err, 'the HTML download still works.');
  }finally{ busyBtn(false); }
}

/* PDF built here in the page, for phones. iOS cannot drive the print dialog from
   a hidden iframe. Since V29 nothing routes through the print dialog at all -
   its destination setting silently decided the file size - so this builds every
   PDF, on every device. This paints the rendered canvas onto A4 pages at
   the same 1 cm margin the print stylesheet uses, slicing it wherever the page
   ends. Text is an image in this file, but at 3x it is comfortably readable. */
async function downloadPdfImage(){
  busyBtn(true);
  try{
    /* Same resolution cap as the JPG export. Uncapped this embedded 2700px
       slices at q0.9 - a 1.3 MB file for two A4 pages. 1500px at 0.80 is the
       setting already proven clean on the JPG, and lands ~450 KB. */
    const full = await renderSheetCanvas();
    const canvas = full.width > MAX_EXPORT_WIDTH ? downscaleCanvas(full, MAX_EXPORT_WIDTH) : full;
    const M_PT = 10 * 72/25.4, PW_PT = 595.28, PH_PT = 841.89;
    const imgWpt = PW_PT - M_PT*2;
    const pxPerPt = canvas.width / imgWpt;
    const sliceH = Math.floor((PH_PT - M_PT*2) * pxPerPt);
    const cut = document.createElement('canvas');
    const ctx = cut.getContext('2d');
    const pages = [];
    for(let y = 0; y < canvas.height; y += sliceH){
      const h = Math.min(sliceH, canvas.height - y);
      cut.width = canvas.width; cut.height = h;
      ctx.fillStyle = '#ffffff'; ctx.fillRect(0, 0, cut.width, cut.height);
      ctx.drawImage(canvas, 0, y, canvas.width, h, 0, 0, canvas.width, h);
      const blob = await new Promise(r => cut.toBlob(r, 'image/jpeg', 0.80));
      if(!blob) throw new Error('encode');
      const hPt = h / pxPerPt;
      pages.push({ bytes: new Uint8Array(await blob.arrayBuffer()),
                   pxW: cut.width, pxH: h,
                   wPt: imgWpt, hPt, xPt: M_PT, yPt: PH_PT - M_PT - hPt });
    }
    saveBlob(pdfFromJpegs(pages), sheetFileStem() + '.pdf');
    showBanner('Saved as a ' + pages.length + '-page A4 PDF.', false);
  }catch(err){
    exportFailed(err, 'try the JPG option instead.');
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
function meetingPayload(){
  return JSON.stringify({app:'nse-programme-sheet', v:28,
    savedAt:new Date().toISOString(), state}, null, 2);
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
function suggestedFileName(){
  const d = new Date();
  const two = n => String(n).padStart(2, '0');
  const now = two(d.getHours()) + two(d.getMinutes());
  return clubInitials() + '-ProgSheet-' + meetingDateStamp() + '-' + now + FILE_EXT;
}
function tidyFileName(name){
  name = String(name || '').replace(/[\\/:*?"<>|]+/g, '-').trim();
  if(!name) return '';
  if(!/\.json$/i.test(name)) name += FILE_EXT;
  return name;
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
  return true;
}

async function writeHandle(h, text){
  const w = await h.createWritable();
  await w.write(text);
  await w.close();
}

/* --- save --- */
async function saveMeeting(){
  if(!FS_SUPPORTED) return downloadMeetingJSON();
  try{
    if(!await ensureFolder(true)) await linkFolder();
    if(!folderHandle) return;
    if(!fileHandle){
      const name = tidyFileName(prompt('Save this meeting as:', suggestedFileName()));
      if(!name) return;
      fileHandle = await folderHandle.getFileHandle(name, {create:true});
    }
    await writeHandle(fileHandle, meetingPayload());
    await refreshFileList();
    setSaveStatus('Saved to ' + fileHandle.name + ' - autosaving there', false, true);
    flashSaved();
    showBanner('Saved ' + fileHandle.name + '. Every change from here autosaves into that file.', false);
  }catch(err){
    if(err && err.name === 'AbortError') return;      /* user closed the picker */
    showBanner('Could not save to the folder (' + ((err && err.message) || 'unknown')
      + '). Your work is still held in this browser.', true);
  }
}
async function saveMeetingAs(){
  fileHandle = null;
  await saveMeeting();
}
/* Autosave into the open file. Silent by design - it runs on every keystroke's
   debounce, so it must never nag; a failure downgrades the badge instead. */
function queueFileSave(){
  if(!fileHandle) return;
  clearTimeout(fileSaveTimer);
  fileSaveTimer = setTimeout(async ()=>{
    try{
      if(!await handleUsable(folderHandle, false)) throw new Error('permission');
      await writeHandle(fileHandle, meetingPayload());
    }catch(e){
      setSaveStatus('Autosaving to this browser only - reconnect the folder to resume saving to '
        + fileHandle.name, true, true);
    }
  }, 1200);
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
function applyMeetingText(text, label){
  let parsed;
  try{ parsed = JSON.parse(text); }
  catch(e){ showBanner((label||'That file') + ' is not readable JSON.', true); return false; }
  if(!adoptState(parsed)){
    showBanner((label||'That file') + ' is not a programme-sheet meeting - nothing was changed.', true);
    return false;
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
  saveBlob(new Blob([meetingPayload()], {type:'application/json'}), suggestedFileName());
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
function toggleDownloadMenu(e){
  if(e) e.stopPropagation();
  const m = document.getElementById('dlMenu'), b = document.getElementById('dlBtn');
  const open = m.classList.toggle('open');
  b.setAttribute('aria-expanded', open ? 'true' : 'false');
}
function closeDownloadMenu(){
  const m = document.getElementById('dlMenu'), b = document.getElementById('dlBtn');
  if(!m) return;
  m.classList.remove('open');
  if(b) b.setAttribute('aria-expanded','false');
}
function pickDownload(kind){
  closeDownloadMenu();
  if(kind === 'html') return downloadSheet();
  /* Desktop goes through the print dialog, which keeps real selectable text.
     Phones cannot, so they get the canvas-built PDF instead. */
  /* Always the in-page PDF, desktop included (V29). Routing desktop through the
     print dialog meant the file's size depended on which destination the user
     picked there - and "Microsoft Print to PDF" rasterises every page at 300dpi
     for a 1.4 MB result. The browser dialog is browser chrome; a web page cannot
     preselect a destination or even see which one is chosen. So Download > PDF
     no longer opens a dialog at all and always lands ~450 KB. Chrome's own
     "Save as PDF" is still the better file - smaller AND with selectable text -
     and the printer button below is how you reach it. */
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
document.addEventListener('click', closeDownloadMenu);
document.addEventListener('keydown', e=>{
  if(e.key !== 'Escape') return;
  closeDownloadMenu();
  const h = document.getElementById('helpOverlay');
  if(h && h.classList.contains('open')) closeHelp();
});

/* ================= Form binding ================= */
function bindMeeting(key, val){ state.meeting[key] = val; updatePreview(); }
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
  const card = document.querySelectorAll('#speechList .sc-preview')[speechSegs().indexOf(seg)];
  if(card) card.innerHTML = cardPreviewHTML(seg);
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

function renderSpeechCards(){
  const container = document.getElementById('speechList');
  if(!container) return;
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
    return `<div class="speech-card" data-sp-id="${seg.id}" draggable="false"
        ondragstart="spDragStart(event,'${seg.id}')" ondragover="spDragOver(event,'${seg.id}')"
        ondragleave="spDragLeave(event)" ondrop="spDrop(event,'${seg.id}')" ondragend="spDragEnd(event)">
      <div class="sc-head">
        <span class="sc-grip" title="Drag to reorder speakers" onmousedown="dragArm(this)">⠿</span>
        <span class="sc-badge">Speech ${i+1}</span>
        <span class="sc-name">${esc(seg.speakerName || '—')}</span>
        <button class="sc-remove" title="Remove this speech and its evaluation" onclick="removeSpeechSlot('${seg.id}')">✕</button>
      </div>
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
      ${mismatchNote}${timingNote}${altBtn}
    </div>`;
  }).join('') || '<div class="hint">No speeches yet — add one below.</div>';
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

function addSpeechSlot(){
  const speeches = speechSegs();
  const sp = newSegment('speech');
  const lastSp = speeches[speeches.length-1];
  state.segments.splice(lastSp ? state.segments.indexOf(lastSp)+1 : state.segments.length, 0, sp);

  const evals = evalSegs();
  const ev = newSegment('evaluation');
  const lastEv = evals[evals.length-1];
  state.segments.splice(lastEv ? state.segments.indexOf(lastEv)+1 : state.segments.length, 0, ev);

  renderFormPane();
  updatePreview();
}
function removeSpeechSlot(id){
  const i = speechSegs().findIndex(s=>s.id===id);
  if(i < 0) return;
  const ev = evalSegs()[i];
  state.segments = state.segments.filter(s=>s.id!==id && (!ev || s.id!==ev.id));
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
function addSeg(){
  const seg = newSegment(document.getElementById('addSegType').value);
  state.segments.push(seg);
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
    if(p.sub && /^(speechvote|ttvote|evalvote)$/.test(seg.presetKey)){
      seg.title = p.label;
      seg.sub = p.sub;
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

/* ================= Print / download (clean sheet only) ================= */
function downloadSheet(){
  const blob = new Blob([buildSheetHTML(false)], {type:'text/html'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = (state.meeting.title || 'programme-sheet').replace(/[^a-z0-9]+/gi,'_').replace(/^_+|_+$/g,'') + '.html';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(()=>URL.revokeObjectURL(url), 2000);
}

/* ================= Init ================= */
function syncFormInputs(){
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
  ensureFolder(false).then(refreshFileList).catch(()=>refreshFileList());
  const hl = document.getElementById('hdrLogo');
  if(hl) hl.src = 'data:image/png;base64,' + LOGO_B64;
  const restored = loadState();
  const c1 = syncLanguageEvaluatorSegment(), c2 = syncRoleSegments();
  if(c1 || c2) rebalanceFlexSilent();
  applyPaneWidth();
  initSplitter();
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
