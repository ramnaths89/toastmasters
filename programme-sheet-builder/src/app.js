/* ================= Segment presets =================
   Durations are Rama's club standard (V21), cross-checked against the live
   13 Aug 2026 sheet: 4 min for SAA call-to-order / TME Welcome / President's
   Opening Address, 1 min for any "returns control to TME" row, 4 min per
   evaluation slot, and 3 min for each combined timer's-report-plus-vote row.
   The blank template's segments total exactly 150 min, so a 7:00 PM start
   lands on the 9:30 PM target with no balancing. Change a duration here and
   updateEndCheck() will start complaining — retune the two FLEXIBLE nominals
   (Break, Table Topics) to absorb it, that is what they are for. */

/* Voting runs on Slido, one room code per vote, numbered in the order they
   happen on the night: prepared speeches, then table topics, then evaluations. */
/* Voting link and the three room codes are CLUB settings, not constants: another
   club runs its own Slido account and its own codes, entered in Club Setup.
   (This used to say a "club-setup .md file" carries them; that importer was
   removed in V35 and the fields have been ordinary form inputs ever since.) Held in module-level variables rather than read from state,
   because newSegment() runs inside defaultState() while `state` is still in its
   temporal dead zone - touching it there throws. syncVotingFromState() pushes
   state back into these whenever a meeting is loaded or the setup is imported. */
let VOTE_LINK = 'https://slido.com';
let VOTE_CODES = {speechvote:'NSE_1', ttvote:'NSE_2', evalvote:'NSE_3'};
/* "Voting Link: https://slido.com | Enter code: NSE_1" - the label was added in
   V33 at Rama's request; the bare URL read as a footnote, not an instruction. */
const votingNote = key => {
  const link = (VOTE_LINK || '').trim();
  const code = String((VOTE_CODES[key] || '')).trim();
  if (!link && !code) return '';
  return 'Voting Link: ' + VOTE_LINK + ' | Enter code: ' + (VOTE_CODES[key] || '');
};
function syncVotingFromState(){
  const v = state && state.meeting && state.meeting.voting;
  if(!v) return;
  if(v.link) VOTE_LINK = v.link;
  if(v.codes) VOTE_CODES = Object.assign({}, VOTE_CODES, v.codes);
}
/* Rewrite the notes on vote rows already in the running order. */
function applyVotingToSegments(){
  state.segments.forEach(sg=>{
    const voteKey = (PRESETS[sg.presetKey] || {}).voteKey;
    if(voteKey) sg.sub = votingNote(voteKey);
  });
}

const PRESETS = {
  custom:        {label:'Custom Item', durMin:5},
  registration:  {label:'Registration & Fellowship', durMin:30, noHolder:true},
  calltoorder:   {label:'SAA Calls Meeting to Order', sub:'Introduction of Guests and Theme', durMin:4, roleKey:'saa'},
  welcome:       {label:'TME Welcome Remarks', sub:'Introduction of Role Players', durMin:4, roleKey:'tmod'},
  langeval:      {label:'Language Evaluator Introduces the Word of the Day', durMin:3, roleKey:'langeval'},
  president:     {label:'Club President Opening Address', durMin:4, roleKey:'president'},
  returncontrol: {label:'Club President Returns Control to TME', durMin:1, roleKey:'tmod'},
  speech:        {label:'Speech', durMin:8, hasSignal:true, signalMin:5, signalMid:6, signalMax:7, isSpeech:true, signalGroup:'Prepared Speech'},
  /* The three combined timer's-report-and-vote rows. Held by the Timer, who
     gives the report the vote follows — the old pevoting was noHolder and
     printed a bare em dash while its two siblings named the Timer. */
  speechvote:    {label:"Call for Timer's Report | Voting for Best Speaker", voteKey:'speechvote', durMin:3, roleKey:'timer'},
  ttvote:        {label:"Call for Timer's Report | Voting for Best Table Topics Speaker", voteKey:'ttvote', durMin:3, roleKey:'timer'},
  evalvote:      {label:"Call for Timer's Report | Voting for Best Speech Evaluation", voteKey:'evalvote', durMin:3, roleKey:'timer'},
  breaktime:     {label:'Break Time', durMin:15, flexible:true, flexMin:10, flexMax:18, noHolder:true},
  ttmasterintro: {label:'TME Introduces Table Topics Master', durMin:1, roleKey:'tmod'},
  tabletopics:   {label:'Conduct Table Topics Session', durMin:17, flexible:true, flexMin:12, flexMax:20,
                  hasSignal:true, signalMin:1, signalMid:1.5, signalMax:2, roleKey:'ttmaster', signalGroup:'Table Topics', signalSuffix:'per speaker'},
  ttreturn:      {label:'Table Topics Master Returns Control to TME', durMin:1, roleKey:'tmod'},
  peintro:       {label:'TME Introduces Project Evaluation Segment', durMin:4, roleKey:'tmod'},
  evaluation:    {label:'Evaluation', durMin:4, hasSignal:true, signalMin:2, signalMid:2.5, signalMax:3, isEvaluation:true, signalGroup:'Evaluation'},
  reports:       {label:'TME Calls for Reports', durMin:4, noHolder:true},
  awards:        {label:'Award Presentation', durMin:3, roleKey:'tmod',
                  sub:'Best Speaker | Table Topics | Evaluator'},
  closing:       {label:"Club President's Closing Address", durMin:4, roleKey:'president'},
  /* fixedHolder seeds holderOverride, so the sheet prints "All" but the field
     stays editable. The photographer role still owns the row's on/off tick. */
  photo:         {label:'Photo Taking Session', durMin:5, roleKey:'photographer', fixedHolder:'All'},
  adjourn:       {label:'Club President Adjourns Meeting', durMin:0, roleKey:'president'},
  /* Superseded by the three combined rows above, kept only so a meeting saved
     before V21 still resolves its presetKey on load. Not offered in Add. */
  timerreport:   {label:"Call for Timer's Report", durMin:2, roleKey:'timer'},
  voting:        {label:'Voting for Best Speaker', durMin:2, noHolder:true},
  ttvoting:      {label:'Voting for Best Table Topics Speaker', durMin:4, noHolder:true},
  pevoting:      {label:"Call for Timer's Report / Voting for Best Project Evaluator", durMin:10, noHolder:true},
};

let segIdCounter = 1;
function newSegment(presetKey){
  const p = PRESETS[presetKey] || PRESETS.custom;
  return {
    id: 'seg' + (segIdCounter++),
    presetKey,
    title: p.label,
    sub: p.voteKey ? votingNote(p.voteKey) : (p.sub || ''),
    speakerName: '',
    holderOverride: p.fixedHolder || '',
    roleKey: p.roleKey || '',
    noHolder: !!p.noHolder,
    durMin: p.durMin,
    flexible: !!p.flexible,
    flexMin: p.flexMin || 0,
    flexMax: p.flexMax || 0,
    hasSignal: !!p.hasSignal,
    signalMin: p.signalMin || 0,
    signalMid: p.signalMid != null ? p.signalMid : ((p.signalMin||0) + (p.signalMax||0))/2,
    signalMax: p.signalMax || 0,
    /* The green→red window width, remembered independently of the current values.
       Re-deriving it each keystroke lets an intermediate slot of "1" clamp both
       lights to 0 and destroy the span for good. */
    signalSpan: Math.max(0, (p.signalMax||0) - (p.signalMin||0)),
    /* true once the user types into green/amber/red — stops the slot auto-split
       from overwriting their choice. */
    signalsManual: false,
    signalGroup: p.signalGroup || '',
    signalSuffix: p.signalSuffix || '',
    isSpeech: !!p.isSpeech,
    isEvaluation: !!p.isEvaluation,
    /* Pathways linkage (speech segments) */
    pathway: '',
    pLevel: '',
    project: '',
    speechTitle: '',
  };
}

/* ================= Default state ================= */
function defaultState(){
  const s = {
    meeting: {
      clubName: 'Nee Soon East Toastmasters Club',
      clubNumber: '00002548',
      /* Initials for the saved-file name, e.g. NSE-ProgSheet-2026-08-13-1930.
         Derived from clubName when blank, so a club that never sets it still
         gets something sane. */
      clubInitials: 'NSE',
      /* Printed in place of a bare club number under the club name, and the
         standing meeting cadence at the foot of the banner. Club constants like
         the venue - hardcoded on Rama's instruction (V26), editable in Club
         Setup, and they survive a Reset. Update the Area/Division at the
         District realignment, not per meeting. */
      orgLine: 'District: 80 | Division: Y | Area Y1 | Club Number: 2548',
      cadence: 'We meet every 2nd and 4th Thursday of the month from 7:00PM to 9:30PM',
      title: '',
      dateDisplay: '',
      location: 'Nee Soon East Community Club, 1 Yishun Ave 9, #04-01 (Culinary Studio), Singapore 768893',
      startTime: '19:00',
      endTime: '21:30',
      footerNote: 'District 80, Division Y, Area 01',
      /* Club's voting service and its three room codes, chronological: prepared
         speeches, then table topics, then evaluations. */
      voting: {link:'https://slido.com',
               codes:{speechvote:'NSE_1', ttvote:'NSE_2', evalvote:'NSE_3'}},
      /* Base name for the saved .json AND for every download, without extension.
         Blank means "use the suggested name", which is what a fresh meeting wants;
         type anything here (or in the Save dialog) and that wins from then on. */
      fileName: '',
    },
    /* Blank by default — the sheet is a template, not last month's meeting.
       Every empty role renders as a TBD chip and is listed as still open. */
    roles: {
      tmod: '', president: '', ttmaster: '', ttevaluator: '',
      langeval: '', timer: '', ahcounter: '', photographer: '', saa: '',
    },
    /* Unticked = this role isn't running today: it drops off the roster and its
       own agenda items are switched off (kept in state, not deleted). */
    /* langeval starts UNTICKED: the club's standard meeting runs without one
       (Rama's live sheets), and since V24 ticking it adds the Word of the Day
       row - which would put the default template 3 min over its exact 150. */
    roleActive: {
      tmod: true, president: true, ttmaster: true, ttevaluator: true,
      langeval: false, timer: true, ahcounter: true, photographer: true, saa: true,
    },
    /* [{key:'cr1', label:'Zoom Master'}] — the club's own roles. Empty in the
       template: this is a per-club addition, not part of the standard meeting. */
    customRoles: [],
    /* Club officers for the current term, hardcoded on Rama's instruction (V21)
       and taken from his live 13 Aug 2026 sheet. These are NOT meeting-specific:
       they hold for the whole term, so unlike the roster they belong in the
       defaults and must survive a Reset. The V13 "no names in the template"
       rule still governs everything that changes weekly — roles, speakers,
       evaluators, meeting title and date all stay blank.
       Refresh these at the club's AGM / handover. */
    execText: [
      'President|<President Name>',
      'VP Education|<VP Education Name>',
      'VP Membership|<VP Membership Name>',
      'VP Public Relations|<VP Public Relations Name>',
      'Secretary|<Secretary Name>',
      'Treasurer|<Treasurer Name>',
      'Sergeant at Arms|<Sergeant at Arms Name>',
      'Immediate Past President|<Immediate Past President Name>',
    ].join('\n'),
    districtText: [
      'Division Director|<Division Director Name>|<Their Club>',
      'Area Director|<Area Director Name>|<Their Club>',
    ].join('\n'),
    linksText: [
      'Toastmasters Intl.|https://www.toastmasters.org|www.toastmasters.org',
      'Our Club|https://www.facebook.com/groups/neesooneast|facebook.com/groups/neesooneast',
    ].join('\n'),
    /* Free text, one announcement per line — meeting-specific, so unlike Exco/
       District/Links (venue constants) this starts blank every time, same as the
       roster fields. Typed manually; nothing here is derived or catalog-driven. */
    announcementsText: '',
    paneWidth: 50,
    theme: 'classic',
    segments: [],
  };

  const seg = [];
  seg.push(newSegment('registration'));
  seg.push(newSegment('calltoorder'));
  seg.push(newSegment('welcome'));
  seg.push(newSegment('president'));
  seg.push(newSegment('returncontrol'));

  /* FOUR empty speech slots: no speaker, no pathway, no project. Picking a
     project fills the timing in from the catalog.
     Four, not three, because four is what the club now runs and what makes the
     standard durations land on 9:30 PM exactly — see the PRESETS note. */
  seg.push(newSegment('speech'));
  seg.push(newSegment('speech'));
  seg.push(newSegment('speech'));
  seg.push(newSegment('speech'));

  seg.push(newSegment('speechvote'));
  seg.push(newSegment('breaktime'));
  seg.push(newSegment('ttmasterintro'));
  seg.push(newSegment('tabletopics'));
  seg.push(newSegment('ttreturn'));
  seg.push(newSegment('ttvote'));
  seg.push(newSegment('peintro'));

  /* One evaluation per speech, paired by index — speakerName mirrors across
     as soon as a speaker is typed into the card above. */
  seg.push(newSegment('evaluation'));
  seg.push(newSegment('evaluation'));
  seg.push(newSegment('evaluation'));
  seg.push(newSegment('evaluation'));

  seg.push(newSegment('evalvote'));
  seg.push(newSegment('awards'));
  seg.push(newSegment('closing'));
  seg.push(newSegment('photo'));
  seg.push(newSegment('adjourn'));
  s.segments = seg;
  return s;
}

let state = defaultState();

/* ================= Persistence (localStorage, gracefully degrading) ================= */
/* Bumped v5 -> v6 in V27 at Rama's request: file:// pages all share one
   localStorage origin, so every version of the tool was restoring the same
   saved meeting - opening a fresh V27 resurrected the last meeting built in
   V26 and looked "populated". A new key means V27+ opens clean; the old v5
   data is untouched and still loads in pre-V27 files. This deliberately
   supersedes the earlier "never rename the key" rule, which protected saved
   work that is now exported and done. */
const STORE_KEY = 'nse-programme-builder-v6';
let storageOK = true;
/* When the copy in this browser was last written, read ONCE at load and never
   again. The autosave debounce restamps localStorage within about 400ms of
   startup, so anything that reads this stamp later sees page-load time and
   concludes the browser copy is newer than every real file on disk. */
const startupSavedAt = (function(){
  try{ return Date.parse(JSON.parse(localStorage.getItem(STORE_KEY)).savedAt) || 0; }
  catch(e){ return 0; }
})();

function saveState(){
  /* The FILE is the copy that matters, so it is queued whatever the browser
     store does. Before this, one QuotaExceededError latched storageOK false and
     saveState returned at the top forever - the file silently stopped updating
     too, while the badge complained only about browser storage. Two independent
     copies, two independent failures. */
  try{
    if(storageOK){
      localStorage.setItem(STORE_KEY, JSON.stringify({v:6, savedAt:new Date().toISOString(), state}));
    }
  }catch(e){
    storageOK = false;
    setSaveStatus('Browser storage unavailable — this meeting is only as safe as its file', true, true);
  }
  /* Never overwrite a live warning with a cheerful tick; see setSaveStatus. */
  flashSaved();
  queueFileSave();
}
let saveTimer = null;
function queueSave(){
  clearTimeout(saveTimer);
  saveTimer = setTimeout(saveState, 400);
}
/* Themes retired in V25 (Bauhaus, Broadsheet, Jetset). A meeting saved under one
   of them would otherwise load with a body class no stylesheet answers to and
   render unstyled, so it falls back to Classic on load. */
const RETIRED_THEMES = ['bauhaus','broadsheet','jetset','terminal','overprint','confessional','handmade'];

/* Take a saved payload - from localStorage OR from a .json file on disk - and
   make it the live state. Merging over defaultState() is what lets a meeting
   saved by an older version keep working: fields added since simply take their
   default. Returns false (leaving the current state untouched) if the payload
   is not a meeting, so a wrong file picked from the dropdown cannot wipe your
   work. Accepts either {state:{...}} or a bare state object. */
/* What adoptState() had to repair on the way in, so the caller can say so rather
   than pretend the file was clean. */
let lastAdoptRepairs = [];

const isPlainObject = o => !!o && typeof o === 'object' && !Array.isArray(o);
/* A hand-edited or truncated file can put anything in a numeric field, and NaN
   propagates all the way to the printed sheet before anyone notices. */
function numOr(v, fallback){
  const n = Number(v);
  return (v === '' || v == null || !isFinite(n)) ? fallback : n;
}
const strOr = (v, fallback) => (typeof v === 'string') ? v : (v == null ? fallback : String(v));

function adoptState(parsed){
  const raw = parsed && parsed.state ? parsed.state : parsed;
  if(!raw || !Array.isArray(raw.segments) || !isPlainObject(raw.meeting)) return false;
  const repairs = [];
  const fresh = defaultState();
  /* Assign into FRESH OBJECTS, not into fresh's own sub-objects. The old form
     did state = Object.assign(fresh, raw), which aliased fresh.meeting to
     raw.meeting - so the next line merged raw.meeting onto itself and the
     defaults never arrived. A file carrying a partial meeting block loaded with
     clubName, location, startTime and the rest undefined, the schedule computed
     from NaN, and the next autosave wrote that back permanently. Dormant only
     because V30-V35 files happen to carry every key; it would have fired on the
     first field added in a later version. */
  state = Object.assign({}, fresh, raw);
  state.meeting = Object.assign({}, fresh.meeting, isPlainObject(raw.meeting) ? raw.meeting : {});
  state.roles   = Object.assign({}, fresh.roles,   isPlainObject(raw.roles) ? raw.roles : {});
  state.roleActive = Object.assign({}, fresh.roleActive, isPlainObject(raw.roleActive) ? raw.roleActive : {});
  /* Object.assign(target, 'abc') spreads a STRING into {0:'a',1:'b',2:'c'}, so a
     segments array holding junk used to produce junk segments rather than being
     rejected. Only plain objects survive. */
  const rawSegs = raw.segments.filter(isPlainObject);
  if(rawSegs.length !== raw.segments.length){
    repairs.push((raw.segments.length - rawSegs.length) + ' unreadable segments dropped');
  }
  state.segments = rawSegs.map(sg => {
    const seg = Object.assign(newSegment('custom'), sg);
    /* Presets are the source of truth for behaviour; a file only supplies values. */
    if(!PRESETS[seg.presetKey]) seg.presetKey = 'custom';
    seg.title = strOr(seg.title, '');
    seg.sub = strOr(seg.sub, '');
    seg.speakerName = strOr(seg.speakerName, '');
    seg.holderOverride = strOr(seg.holderOverride, '');
    seg.speechTitle = strOr(seg.speechTitle, '');
    seg.project = strOr(seg.project, '');
    seg.durMin   = Math.max(0, numOr(seg.durMin, 0));
    seg.flexMin  = Math.max(0, numOr(seg.flexMin, 0));
    seg.flexMax  = Math.max(0, numOr(seg.flexMax, 0));
    seg.signalMin = Math.max(0, numOr(seg.signalMin, 0));
    seg.signalMax = Math.max(0, numOr(seg.signalMax, 0));
    seg.signalMid = numOr(seg.signalMid, (seg.signalMin + seg.signalMax) / 2);
    seg.signalSpan = Math.max(0, numOr(seg.signalSpan, seg.signalMax - seg.signalMin));
    return seg;
  });
  /* Two segments sharing an id means every edit, drag and delete hits whichever
     the DOM query finds first. Re-key the duplicates rather than lose a row. */
  const seenIds = new Set();
  let dupes = 0;
  state.segments.forEach(sg=>{
    let id = strOr(sg.id, '');
    if(!id || seenIds.has(id)){ id = 'seg' + (Date.now() % 100000) + '_' + (dupes++); }
    sg.id = id;
    seenIds.add(id);
  });
  if(dupes) repairs.push(dupes + ' duplicate segment ids re-keyed');
  const nSp = state.segments.filter(s=>s.isSpeech).length;
  const nEv = state.segments.filter(s=>s.isEvaluation).length;
  if(nSp !== nEv){
    repairs.push('speech/eval count mismatch (' + nSp + ' vs ' + nEv + ')');
  }
  /* These four are split on newlines and pipes all over the renderer; a non-string
     here threw before anything reached the screen. */
  ['execText','districtText','linksText','announcementsText'].forEach(k=>{
    if(typeof state[k] !== 'string'){ state[k] = strOr(state[k], ''); repairs.push(k + ' was not text'); }
  });
  if(typeof state.theme !== 'string') state.theme = 'classic';
  state.paneWidth = Math.min(80, Math.max(20, numOr(state.paneWidth, 50)));
  /* A file written before V30 has no customRoles; one hand-edited could have
     anything. Keep only well-formed entries so the roster cannot render undefined. */
  state.customRoles = (Array.isArray(raw.customRoles) ? raw.customRoles : [])
    .filter(r => r && typeof r === 'object' && r.key)
    .map(r => ({key: String(r.key), label: String(r.label == null ? '' : r.label)}));
  state.meeting.voting = Object.assign({link:VOTE_LINK, codes:{}},
    (raw.meeting && raw.meeting.voting) || {});
  syncVotingFromState();
  if(RETIRED_THEMES.includes(state.theme)) state.theme = 'classic';
  /* keep new IDs from colliding with restored ones */
  let maxId = 0;
  state.segments.forEach(sg=>{
    const n = parseInt(String(sg.id).replace(/\D/g,''), 10);
    if(!isNaN(n) && n > maxId) maxId = n;
  });
  segIdCounter = maxId + 1;
  lastAdoptRepairs = repairs;
  return true;
}

function loadState(){
  try{
    const raw = localStorage.getItem(STORE_KEY);
    if(!raw) return false;
    const parsed = JSON.parse(raw);
    if(!adoptState(parsed)) return false;
    return parsed.savedAt || true;
  }catch(e){
    storageOK = false;
    return false;
  }
}
function resetToDefaults(){
  const open = openFileName();
  if(!confirm('Reset every field back to the built-in defaults? Your saved version will be discarded.'
      + (open ? '\n\n' + open + ' stays on disk untouched, and this stops saving into it.' : ''))) return;
  try{ localStorage.removeItem(STORE_KEY); }catch(e){}
  /* DETACH THE FILE FIRST. Reset used to leave the open meeting attached, so the
     very next keystroke autosaved the blank template straight over a saved
     meeting - silently, with the green tick showing. The file is the user's work;
     Reset is for starting a new sheet, never for destroying an old one. */
  detachFile('Reset — no longer saving into a file.');
  state = defaultState();
  editingSegId = null;
  expandedSegs.clear();
  applyPaneWidth();
  syncFormInputs();
  renderFormPane();
  renderPreviewNow();
  showBanner('Reset to built-in defaults.', false);
}

/* ================= Helpers ================= */
function parseTimeToMin(t){
  if(!t) return 0;
  const [h,m] = t.split(':').map(Number);
  return h*60 + (m||0);
}
function fmtClock(totalMin){
  totalMin = ((Math.round(totalMin) % 1440) + 1440) % 1440;
  let h = Math.floor(totalMin/60), m = totalMin % 60;
  const ap = h < 12 ? 'AM' : 'PM';
  let h12 = h % 12; if(h12 === 0) h12 = 12;
  return h12 + ':' + String(m).padStart(2,'0') + ' ' + ap;
}
function fmtSignalTime(mins){
  const m = Math.floor(mins), s = Math.round((mins - m) * 60);
  return m + ':' + String(s).padStart(2,'0');
}
function esc(str){
  return String(str == null ? '' : str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function parsePipeRows(text){
  return text.split('\n').map(l=>l.trim()).filter(Boolean).map(l=>l.split('|').map(x=>x.trim()));
}
/* Rows run by two people at once. The Timer gives the report, the TME runs the
   vote that follows, and both need to know the row is theirs — so these print
   both names, one per line, each labelled (Rama, V22).
   Keyed on presetKey rather than a field on the segment, so a meeting saved
   before V22 picks it up on load with no migration. */
const MULTI_HOLDER = {
  speechvote: ['timer','tmod'],
  ttvote:     ['timer','tmod'],
  evalvote:   ['timer','tmod'],
};
function holderFor(seg){
  if(seg.noHolder) return {text:'—', tbd:false};
  /* A typed override still wins — it is the escape hatch for the night someone
     doubles up or a guest steps in. */
  const pair = !seg.holderOverride && MULTI_HOLDER[seg.presetKey];
  if(pair){
    /* Names only, one per line - Timer first, then TME. The role labels were
       printed until V25; Rama: "you don't have to indicate the title ...
       just indicate the names." */
    const rows = pair.filter(roleIsActive).map(k => ({
      name: state.roles[k] || '',
      tbd: !state.roles[k],
    }));
    if(rows.length) return {rows, tbd: rows.every(r=>r.tbd)};
  }
  /* An evaluation is delivered by the evaluator — never fall back to the
     speaker being evaluated, or the sheet claims they evaluated themselves. */
  if(seg.isEvaluation){
    return seg.holderOverride ? {text:seg.holderOverride, tbd:false} : {text:'TBD', tbd:true};
  }
  if(seg.isSpeech){
    if(seg.holderOverride) return {text:seg.holderOverride, tbd:false};
    return seg.speakerName ? {text:seg.speakerName, tbd:false} : {text:'TBD', tbd:true};
  }
  if(seg.holderOverride) return {text:seg.holderOverride, tbd:false};
  if(seg.roleKey){
    const v = state.roles[seg.roleKey];
    return v ? {text:v, tbd:false} : {text:'TBD', tbd:true};
  }
  return {text:'TBD', tbd:true};
}
function speechIndex(seg){
  return state.segments.filter(s=>s.isSpeech).indexOf(seg);
}
/* "Prepared Speech 1: Dynamic Leadership | Level 1 | Evaluation and Feedback" */
function speechHeading(seg){
  const n = speechIndex(seg) + 1;
  const parts = [];
  if(seg.pathway) parts.push(pathFullName(seg.pathway));
  if(seg.pLevel)  parts.push('Level ' + seg.pLevel);
  if(seg.project) parts.push(seg.project);
  return `Prepared Speech ${n}` + (parts.length ? ': ' + parts.join(' | ') : '');
}
function speechTimingRange(seg){
  const mn = Number(seg.signalMin)||0, mx = Number(seg.signalMax)||0;
  if(!mx) return '';
  const whole = (mn % 1 === 0) && (mx % 1 === 0);
  return whole ? `${mn}–${mx} min` : `${fmtSignalTime(mn)}–${fmtSignalTime(mx)} min`;
}
/* POETTS — the order the TME introduces a speaker in:
   Project (in the heading), Evaluator, Timing, Title, Speaker. */
function speechPOETTS(seg){
  const ev = activeSegments().filter(s=>s.isEvaluation)[speechIndex(seg)];
  return [
    {k:'evaluator', label:'Evaluator', value: (ev && ev.holderOverride) || 'TBD', tbd: !(ev && ev.holderOverride)},
    {k:'timing',    label:'Timing',    value: speechTimingRange(seg) || 'TBD', tbd: !speechTimingRange(seg)},
    /* Red like every other TBD. V22 tried a muted grey here; Rama reversed it in
       V24 - "leave the TBD on the program sheet in the original red, it stands
       out more that way." The grey prompt lives in the FORM's placeholder now. */
    {k:'title',     label:'Title',     value: seg.speechTitle ? `\u201c${seg.speechTitle}\u201d` : 'TBD', tbd: !seg.speechTitle},
    {k:'speaker',   label:'Speaker',   value: seg.speakerName || 'TBD', tbd: !seg.speakerName},
  ];
}
/* Kept for the left-pane card preview. */
function speechComment(seg){
  return speechPOETTS(seg).map(r => `${r.label}: ${r.value}`).join(' | ');
}
function titleFor(seg){
  if(seg.isSpeech) return speechHeading(seg);
  if(seg.isEvaluation){
    return seg.speakerName ? ('Evaluation for ' + seg.speakerName) : 'Evaluation';
  }
  return seg.title;
}

/* ================= 2025 Pathways enhancements: Education Series =================
   From Toastmasters International's "Club Officer Guide to the 2025 Pathways
   Enhancements" (effective October 2025). The enhancement REMOVES nothing: every
   project already required in a level stays exactly where it was. What it adds is
   an Education Series presentation at Levels 3, 4 and 5, chosen from a fixed list
   per level, plus meeting-role requirements the club does not schedule from here.

   These are speaking slots like any other, so they belong in the project picker —
   but they are NOT path-specific: a member on any of the eleven paths picks from
   the same list. So they live in their own block and projectsFor() appends them to
   whichever path is selected, rather than being copied into 11 x levels.

   TI: "The Education Series presentations are expected to take 10 to 15 minutes to
   present, which is longer than a typical speech." One figure for all of them. */
const EDU_MIN = 10, EDU_MAX = 15;
const EDU_SERIES = {
  '3': [
    {s:'Successful Club Series', t:[
      'Creating the Best Club Climate',
      'Meeting Roles and Responsibilities',
      'Keeping the Commitment',
      'Going Beyond Our Club']},
  ],
  '4': [
    {s:'Successful Club Series', t:[
      'Finding New Members',
      'Closing the Sale',
      'How to Be a Distinguished Club',
      'Toastmasters Educational Program']},
    {s:'Better Speaker Series', t:[
      'Beginning Your Speech',
      'Concluding Your Speech',
      'Controlling Your Fear',
      'Impromptu Speaking',
      'Selecting Your Topic',
      'Know Your Audience',
      'Organizing Your Speech',
      'Creating an Introduction',
      'Preparation and Practice',
      'Using Body Language']},
  ],
  '5': [
    {s:'Successful Club Series', t:[
      'Moments of Truth',
      'Evaluate to Motivate',
      'Mentoring']},
    {s:'Leadership Excellence Series', t:[
      'Service and Leadership',
      'The Leader as a Coach',
      'Developing a Mission',
      'Motivating People',
      'Building a Team',
      'Delegate to Empower',
      'Resolving Conflict',
      'Visionary Leader',
      'Values and Leadership',
      'Goal Setting and Planning',
      'Giving Effective Feedback']},
  ],
};
/* Registered into PATHWAYS_DATA.projects so timingLabel(), projectInfo() and the
   mismatch check treat them exactly like a catalogue project. A title that somehow
   collided with an existing project would silently retime it, so collisions are
   refused rather than merged. */
const EDU_BY_LEVEL = {};
const EDU_SKIPPED = [];
(function registerEduSeries(){
  /* "A real project" means one a path actually offers at some level. The
     catalogue also carries orphans no level references — "Mentoring" is one, and
     it collides head-on with the Successful Club Series title of the same name.
     Guarding on mere presence silently dropped that title and left the ordinary
     5-7 min entry in its place, so a member picking it got 5/6/7 lights on what
     is a 10-15 min presentation. Only a REFERENCED project is protected; an
     orphan is replaced. A genuine collision is recorded rather than swallowed. */
  const referenced = new Set();
  Object.values(PATHWAYS_DATA.levels).forEach(lv =>
    Object.values(lv).forEach(list => list.forEach(p => referenced.add(p.n))));
  Object.entries(EDU_SERIES).forEach(([lvl, groups])=>{
    EDU_BY_LEVEL[lvl] = [];
    groups.forEach(g=>{
      g.t.forEach(name=>{
        if(referenced.has(name)){ EDU_SKIPPED.push(name); return; }
        PATHWAYS_DATA.projects[name] = {min:EDU_MIN, max:EDU_MAX, series:g.s};
        EDU_BY_LEVEL[lvl].push({n:name, e:true, s:g.s});
      });
    });
  });
  if(EDU_SKIPPED.length && typeof console !== 'undefined'){
    console.warn('Education Series titles clashing with a path project, not added: '
      + EDU_SKIPPED.join(', '));
  }
})();
function eduFor(lvl){ return EDU_BY_LEVEL[String(lvl)] || []; }
/* The series a project belongs to, or '' for an ordinary path project. */
function seriesOf(name){
  const pi = PATHWAYS_DATA.projects[name];
  return (pi && pi.series) || '';
}

/* ================= Pathways catalog lookups ================= */
const ALL_PROJECTS = Object.keys(PATHWAYS_DATA.projects).sort();

function projectsFor(abbr, lvl){
  const own = (PATHWAYS_DATA.levels[abbr] && PATHWAYS_DATA.levels[abbr][String(lvl)]) || [];
  /* Education Series options sit AFTER the path's own projects: they are an extra
     requirement at that level, not a substitute for the project list. */
  return own.concat(eduFor(lvl));
}
function projectInfo(name){
  return PATHWAYS_DATA.projects[name] || null;
}
function timingLabel(name){
  const pi = projectInfo(name);
  if(!pi) return '';
  return pi.min != null ? `${pi.min}–${pi.max} min` : 'no set speech';
}
/* Which level does this project sit at within a given pathway? (null if not in that path) */
function levelOfProjectIn(abbr, projectName){
  if(!abbr) return null;
  for(const lvl of ['1','2','3','4','5']){
    const hit = projectsFor(abbr, lvl).find(p => p.n === projectName);
    if(hit) return {level: lvl, elective: hit.e};
  }
  return null;
}


/* ================= Role players (listed under TME Welcome Remarks) =================
   The TME introduces the supporting role players here. Excludes the TME (who is
   speaking) and the President (who has their own address further down). */
const ROLE_PLAYER_KEYS = [
  ['saa','Sergeant-at-Arms'],
  ['ttmaster','Table Topics Master'],
  ['ttevaluator','Table Topics Evaluator'],
  ['langeval','Language Evaluator'],
  ['timer','Timer'],
  ['ahcounter','Ah-Counter'],
  ['photographer','Photographer'],
];
const ROLE_LABELS = {
  tmod:'Toastmaster of the Day', president:'(Acting) President', ttmaster:'Table Topics Master',
  ttevaluator:'Table Topics Evaluator', langeval:'Language Evaluator', timer:'Timer',
  ahcounter:'Ah-Counter', photographer:'Photographer', saa:'Sergeant-at-Arms',
};

/* ================= Custom roles (V30) =================
   Clubs run roles the built-in nine do not cover — Zoom Master, Joke Master,
   Grammarian where the club splits it off the Language Evaluator, a Contest
   Chief Judge. Each is just a label plus a person, so a custom role is stored the
   same way a built-in one is: the NAME goes in state.roles under its key and the
   tick in state.roleActive, which means every existing consumer (holderFor, the
   roster, the still-open list, the .json round-trip, syncFormInputs) picks it up
   with no special case. Only the LABEL needs its own list, because the built-in
   labels are a constant.
   Keys are 'cr1', 'cr2'... and are never reused within a meeting, so a segment
   pointing at a custom role via roleKey cannot silently re-target if one is
   deleted and another added. */
function customRoles(){ return Array.isArray(state.customRoles) ? state.customRoles : []; }
function nextCustomRoleKey(){
  let max = 0;
  customRoles().forEach(r=>{
    const n = parseInt(String(r.key).replace(/\D/g,''), 10);
    if(!isNaN(n) && n > max) max = n;
  });
  return 'cr' + (max + 1);
}
/* Label + name in one place, for anything that needs to print or list them. */
function customRoleLines(){
  return customRoles()
    .filter(r => r.label && roleIsActive(r.key))
    .map(r => ({key:r.key, label:r.label, name: state.roles[r.key] || '', tbd: !state.roles[r.key]}));
}
/* Built-in labels plus whatever the club has added. */
function roleLabelMap(){
  const m = Object.assign({}, ROLE_LABELS);
  customRoles().forEach(r=>{ if(r.label) m[r.key] = r.label; });
  return m;
}
/* Which agenda items exist ONLY because a role is running. Deliberately NOT the same
   as a segment's roleKey: the TME *holds* Welcome Remarks, Returns Control, and the two
   introductions, but those are meeting infrastructure — they must survive even if the
   TME row is switched off. Same for the President's address. */
const ROLE_OWNED_SEGMENTS = {
  saa:          ['calltoorder'],
  langeval:     ['langeval'],
  ttmaster:     ['ttmasterintro','tabletopics','ttreturn','ttvoting','ttvote'],
  /* ttvoting is the pre-V21 preset name; ttvote is the live combined row. Both
     stay listed so a meeting saved before V21 still hides with the TT Master. */
  /* Deliberately NOT the three vote rows: the club still votes when nobody is
     timing, so unticking Timer must leave those rows standing (holder → TBD). */
  timer:        ['timerreport'],
  photographer: ['photo'],
  tmod: [], president: [], ttevaluator: [], ahcounter: [],
};
function roleIsActive(key){ return state.roleActive ? state.roleActive[key] !== false : true; }

/* Switch owned segments on/off to match the ticked roles. Returns true if anything moved. */
function syncRoleSegments(){
  const off = new Set();
  Object.entries(ROLE_OWNED_SEGMENTS).forEach(([role, presets])=>{
    if(!roleIsActive(role)) presets.forEach(p=>off.add(p));
  });
  let changed = false;
  state.segments.forEach(seg=>{
    const want = off.has(seg.presetKey);
    if(!!seg.disabled !== want){
      seg.disabled = want;
      if(want && editingSegId === seg.id) editingSegId = null;
      changed = true;
    }
  });
  return changed;
}

function rolePlayerLines(){
  const builtIn = ROLE_PLAYER_KEYS.filter(([k]) => roleIsActive(k)).map(([k,label])=>({
    label, name: state.roles[k] || '', tbd: !state.roles[k]
  }));
  /* Custom roles are introduced with the rest of the role players, after them. */
  return builtIn.concat(customRoleLines().map(r=>({label:r.label, name:r.name, tbd:r.tbd})));
}
/* A role that isn't running today is not "still open" — don't chase it. */
function openRoleLabels(){
  return Object.entries(roleLabelMap())
    .filter(([k]) => roleIsActive(k) && !state.roles[k])
    .map(([,label]) => label);
}

/* ================= Auto Language-Evaluator segment =================
   A "Language Evaluator Introduces the Word of the Day" row appears right after
   TME Welcome Remarks whenever a Language Evaluator is named, and disappears
   when the role is cleared. Returns true if the running order changed. */
function syncLanguageEvaluatorSegment(){
  /* Tick-driven since V24 (was name-driven): a ticked Language Evaluator puts
     the row in the agenda immediately, TBD until named, so the printed running
     order and timings are final before the roster is. The 3 min it adds is
     flagged by the end-check and absorbed with Balance. */
  const has = roleIsActive('langeval');
  const idx = state.segments.findIndex(s => s.presetKey === 'langeval');
  if(has && idx < 0){
    const seg = newSegment('langeval');
    const wIdx = state.segments.findIndex(s => s.presetKey === 'welcome');
    state.segments.splice(wIdx >= 0 ? wIdx + 1 : 1, 0, seg);
    return true;
  }
  if(!has && idx >= 0){
    if(editingSegId === state.segments[idx].id) editingSegId = null;
    state.segments.splice(idx, 1);
    return true;
  }
  return false;
}



/* ================= Sheet styles =================
   Each theme is a CSS block in sheet.css scoped under body.th-<key>; every export
   carries all of them, so a downloaded file can even be re-themed by hand. */
const THEMES = [
  {key:'classic',    name:'Classic'},     /* the current TI-brand look */
  {key:'zine',       name:'Zine'},        /* riso screen-print, halftone, art-school poster */
  {key:'swiss',      name:'Swiss'},       /* Müller-Brockmann grid, International Typographic Style */
  {key:'brutalist',  name:'Brutalist'},   /* neo-brutalist landing page, hard borders + shadows */
  {key:'retrofuture',name:'Retro-Futurism'},        /* 1970s space-age, NASA-worm capsules */
];
/* Handmade retired in V31 at Rama's request - five themes now. Its CSS block is
   still in sheet.css so an old saved meeting is not left unstyled while the
   RETIRED_THEMES fallback swaps it to Classic on load. */

/* "4 Aug 2026" — stamped at render time, so the footer always carries the date
   the sheet was actually generated. */
const MONTHS_SHORT = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
function todayStr(){
  const d = new Date();
  return `${d.getDate()} ${MONTHS_SHORT[d.getMonth()]} ${d.getFullYear()}`;
}

/* ================= Timing lights =================
   The slot is clock time; the lights are the speech requirement. One minute of the
   slot is left for the introduction/transition, so red lands at slot − 1 and the
   green→red span is preserved: an 8-minute slot on a 5–7 project gives 5 / 6 / 7. */
const TRANSITION_MIN = 1;

function spanOf(seg){
  if(seg.signalSpan != null && seg.signalSpan !== '') return Math.max(0, Number(seg.signalSpan));
  return Math.max(0, (Number(seg.signalMax)||0) - (Number(seg.signalMin)||0));
}
function autoSignalsFromSlot(seg){
  if(seg.signalsManual) return false;
  const span = spanOf(seg);
  const red = Math.max(0, (Number(seg.durMin)||0) - TRANSITION_MIN);
  const green = Math.max(0, red - span);
  seg.signalMax = red;
  seg.signalMin = green;
  seg.signalMid = Math.round(((green + red) / 2) * 2) / 2;
  return true;
}
/* Slot that fits a green/red pair, leaving the transition minute. */
function slotForSignals(max){ return (Number(max)||0) + TRANSITION_MIN; }

/* Does this speech still match the official project timing? */
function projectTimingMismatch(seg){
  if(!seg.project) return null;
  const info = projectInfo(seg.project);
  if(!info || info.min == null) return null;
  const same = Number(seg.signalMin) === info.min && Number(seg.signalMax) === info.max;
  return same ? null : {min: info.min, max: info.max};
}

/* ================= Pathway naming ================= */
function pathFullName(abbr){
  const p = PATHWAYS_DATA.paths.find(x => x.abbr === abbr);
  return p ? p.name : abbr;
}

/* ================= Schedule computation ================= */
function activeSegments(){ return state.segments.filter(s => !s.disabled); }

function computeSchedule(){
  let cursor = parseTimeToMin(state.meeting.startTime);
  const rows = [], clockById = {};
  for(const seg of activeSegments()){
    const clock = fmtClock(cursor);
    rows.push({seg, clock});
    clockById[seg.id] = clock;
    cursor += Number(seg.durMin) || 0;
  }
  return {rows, clockById, endMin: cursor, endClock: fmtClock(cursor)};
}

function applyFlexBalance(){
  const startMin = parseTimeToMin(state.meeting.startTime);
  let targetMin = parseTimeToMin(state.meeting.endTime);
  if(targetMin <= startMin) targetMin += 1440;
  const flexSegs = activeSegments().filter(s=>s.flexible);
  if(flexSegs.length === 0) return {none:true};
  const fixedSum = activeSegments().filter(s=>!s.flexible).reduce((a,s)=>a+(Number(s.durMin)||0),0);
  const needed = (targetMin - startMin) - fixedSum;
  const weights = flexSegs.map(s => Number(s.durMin) || 1);
  const weightSum = weights.reduce((a,b)=>a+b,0) || flexSegs.length;
  flexSegs.forEach((s,i)=>{
    let share = Math.max(0, Math.round(needed * (weights[i]/weightSum)));
    if(s.flexMax) share = Math.min(s.flexMax, share);
    if(s.flexMin) share = Math.max(s.flexMin, share);
    s.durMin = share;
  });
  const achievedEnd = startMin + fixedSum + flexSegs.reduce((a,s)=>a+(Number(s.durMin)||0),0);
  return {achievedEnd, targetMin, exact: achievedEnd === targetMin};
}
function rebalanceFlexSilent(){ applyFlexBalance(); }

function balanceToEndTime(){
  const r = applyFlexBalance();
  if(r.none){
    showBanner('No flexible segments to adjust — mark a segment (e.g. Break, Table Topics) as flexible first.', true);
    return;
  }
  if(r.exact){
    showBanner(`Balanced — flexible segments adjusted to land exactly on ${fmtClock(r.achievedEnd)}.`, false);
  } else {
    const gap = r.targetMin - r.achievedEnd;
    showBanner(`Flex ranges maxed out — landed on ${fmtClock(r.achievedEnd)}, still ${Math.abs(gap)} min ${gap>0?'short of':'over'} ${fmtClock(r.targetMin)}. Widen a flex range or adjust a fixed segment.`, true);
  }
  renderFormPane();
  updatePreview();
}

/* Amber falls back to the midpoint for anything saved before amber existed. */
function midOf(seg){
  return seg.signalMid != null && seg.signalMid !== ''
    ? Number(seg.signalMid)
    : ((Number(seg.signalMin)||0) + (Number(seg.signalMax)||0)) / 2;
}
