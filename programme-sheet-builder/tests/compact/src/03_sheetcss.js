
const SHEET_CSS = `
  /* Toastmasters International brand palette (Brand Manual 02330-001-0001):
     True Maroon #772432, Loyal Blue #004165, Cool Gray #A9B2B1, Happy Yellow #F2DF74
     Headlines: Gotham / Montserrat (free alt).  Body: Myriad Pro / Source Sans 3 (free alt). */
  :root{
    --maroon: #772432;
    --maroon-dark: #4f1420;
    --blue: #004165;
    --gray: #A9B2B1;
    --yellow: #F2DF74;
    --yellow-deep: #b5892e;
    --cream: #faf8f4;
    --ink: #23282b;
    --ink-soft: #5c6469;
    --line: #e2e1dd;
    --row-alt: #f6f4ef;
    --tbd: #9c3b33;
    --sig-green: #2e7d46;
    --sig-yellow: #d8b400;
    --sig-red: #a4342b;
    --print-pane: 45.6mm;   /* 24% of the 190mm A4 content width, in mm so calc() can use it */
    --print-foot: 6.5mm;
    --print-head: 33mm;
  }
  *{ box-sizing: border-box; }
  html,body{ margin:0; padding:0; }
  body{
    font-family: "Source Sans 3", "Myriad Pro", Arial, "Segoe UI", sans-serif;
    color: var(--ink);
    background: #d9d3c8;
    min-height: 100vh;
  }
  h1,h2,h3,.club,.meeting-title,thead th,.exco-role,aside h3{
    font-family: "Montserrat", "Gotham", Arial, "Segoe UI", sans-serif;
  }

  /* ---------- Fixed print control (top-right of viewport, never in page flow) ---------- */
  .print-fab{
    position: fixed;
    top: 14px;
    right: 14px;
    z-index: 100;
  }
  .print-btn{
    background: var(--maroon);
    color:#fff;
    border:none;
    padding: 8px 14px;
    border-radius: 999px;
    font-family: "Montserrat", Arial, sans-serif;
    font-weight: 600;
    font-size: 12.5px;
    cursor:pointer;
    box-shadow: 0 3px 10px rgba(0,0,0,0.3);
    display:flex;
    align-items:center;
    gap: 6px;
    white-space: nowrap;
  }
  .print-btn:hover{ background: var(--maroon-dark); }

  .page-wrap{
    display:flex;
    justify-content:center;
    padding: 24px 12px 60px;
  }
  .page{
    width: 100%;
    max-width: 900px;
    background: #fff;
    box-shadow: 0 10px 40px rgba(0,0,0,0.22);
    border-radius: 4px;
    overflow: hidden;
  }

  /* ---------- Header ---------- */
  header{
    background: linear-gradient(to bottom, var(--maroon) 0%, var(--maroon-dark) 100%);
    color: #fff;
    padding: 24px 32px 20px;
    display:flex;
    align-items:center;
    gap: 20px;
    border-bottom: 5px solid var(--yellow);
  }
  .head-text{ flex: 1 1 auto; min-width: 0; }
  .head-text .club{
    font-size: 25px;
    font-weight: 700;
    letter-spacing: 0.2px;
    margin: 0 0 3px;
  }
  .head-text .clubnum{
    font-size: 13px;
    opacity: 0.85;
    margin: 0 0 9px;
    letter-spacing: 0.4px;
  }
  .head-text .meeting-title{
    font-size: 17px;
    font-weight: 600;
    font-style: italic;
    color: var(--yellow);
    margin: 0 0 8px;
  }
  .meta-row{
    display:flex;
    flex-wrap: wrap;
    gap: 4px 20px;
    font-size: 13px;
    line-height:1.6;
    opacity: 0.95;
  }
  .meta-row b{ color:var(--yellow); font-weight:600; }
  /* Standing meeting cadence, closing the banner. Quieter than the meta row -
     it is the same every week, so it should read as a footnote, not a fact you
     need to check. */
  .cadence{
    margin: 9px 0 0;
    font-size: 12px;
    font-style: italic;
    opacity: 0.82;
    letter-spacing: 0.2px;
  }

  /* ---------- Body layout ---------- */
  .body-grid{
    display:grid;
    grid-template-columns: 200px 1fr;
  }
  /* The agenda comes first in the source (so phones and screen readers lead with
     it); on a wide screen the pane is placed back into column 1 explicitly. */
  aside{ grid-column: 1; grid-row: 1; }
  main{  grid-column: 2; grid-row: 1; }

  /* ---------- Sidebar ---------- */
  aside{
    background: var(--cream);
    border-right: 1px solid var(--line);
    padding: 0;                 /* .pane-body holds the inset; .pane-brand is full-bleed */
    font-size: 13px;
    color: var(--ink-soft);
  }
  aside h3{
    font-size: 12.5px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    color: var(--maroon);
    border-bottom: 2px solid var(--yellow);
    padding-bottom: 5px;
    margin: 0 0 10px;
    line-height:1.3;
  }
  .exco-block{ margin-bottom: 18px; }
  .exco-item{ margin-bottom: 8px; }
  .exco-role{ font-weight:700; color: var(--ink); font-size: 12px; }
  .exco-name{ font-size: 12.5px; }
  .exco-sub{ font-size: 11.5px; color: var(--ink-soft); font-style: italic; }
  .links a{ color: var(--blue); text-decoration: none; word-break: break-word; }
  .links a:hover{ text-decoration: underline; }
  .path-legend div{ margin-bottom: 4px; line-height: 1.35; font-size: 12.5px; }
  .path-legend b{ color: var(--maroon); }
  .announcements .announce-line{ margin-bottom: 6px; line-height: 1.4; font-size: 12.5px; }
  .announcements .announce-gap{ height: 6px; }
  /* Brand box: the top of the pane carries the same treatment as the title
     banner, so the two together read as one band across the top of the sheet.
     It is ALSO what removed the page-2 gap problem - the pane's top band is now
     meant to be filled on every page, so the pane can stay position:fixed
     (identical on every page) instead of needing per-page copies. */
  .pane-brand{
    background: linear-gradient(to bottom, var(--maroon) 0%, var(--maroon-dark) 100%);
    border-bottom: 5px solid var(--yellow);
    display:flex; align-items:center; justify-content:center;
    padding: 14px 10px;
  }
  /* Sized to the logo's own 296x248 aspect - NOT a square box relying on
     object-fit. html2canvas does not implement object-fit, so a 96x96 box made
     it stretch the artwork to fill the square and the globe came out squashed
     in every JPG/PDF export (Rama, V26). Letting height follow width renders
     identically in the browser and in the exporter. */
  .pane-brand img{ width: 96px; height: auto; display:block; }
  .pane-body{ padding: 18px 16px 26px; }

  /* ---------- Main agenda ---------- */
  main{ padding: 20px 24px 28px; min-width: 0; }
  .theme-strip{
    background: var(--row-alt);
    border-left: 4px solid var(--yellow-deep);
    padding: 8px 14px;
    font-size: 13px;
    color: var(--ink-soft);
    margin-bottom: 14px;
  }
  .schedule-note{
    font-size: 11.8px;
    color: var(--ink-soft);
    margin: -6px 0 14px;
  }
  table{
    width:100%;
    border-collapse: collapse;
  }
  thead th{
    background: var(--maroon);
    color: #fff;
    text-align:left;
    font-size: 11.5px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding: 8px 10px;
  }
  th.col-time{ width: 80px; }
  th.col-holder{ width: 165px; }

  tbody tr{ border-bottom: 1px solid var(--line); }
  tbody tr.alt{ background: var(--row-alt); }
  tbody tr.flex-row{ background: #eef4f7; }
  tbody td{
    padding: 8px 10px;
    vertical-align: top;
    font-size: 13px;
    line-height: 1.42;
  }
  td.time{
    font-weight: 700;
    color: var(--maroon);
    white-space: nowrap;
    font-variant-numeric: tabular-nums;
  }
  td.item .item-title{ font-weight: 700; color: var(--ink); }
  td.item .item-sub{ display:block; color: var(--ink-soft); font-size: 12.3px; margin-top: 2px; }
  .tbd-inline{ color: var(--tbd); font-weight: 700; }
  td.holder{ color: var(--ink); }
  td.holder .tbd{
    color: var(--tbd);
    font-weight: 700;
    font-size: 11.5px;
    letter-spacing: 0.4px;
    border: 1px solid #e3b3ac;
    background: #fdeeec;
    padding: 1px 6px;
    border-radius: 3px;
    display:inline-block;
  }
  /* Two-name holder (Timer then TME on the combined report/vote rows): names
     only, one per line, exactly TWO lines - anything taller here has pushed the
     sheet onto a third page before. */
  .holder-pair{ display:block; }
  .holder-pair .hp-line{ display:block; line-height: 1.35; font-size: 12.5px; }

  .flex-badge{
    display:inline-block;
    color: var(--blue);
    font-weight: 700;
    font-size: 10.5px;
    letter-spacing: 0.4px;
    border: 1px dashed var(--blue);
    background: #eaf2f6;
    padding: 1px 6px;
    border-radius: 3px;
    margin-right: 6px;
  }

  /* Timing lights: three adjoining colour blocks with the time inside each */
  .signal-line{ display:inline-flex; align-items:center; gap:7px; margin-top:4px; }
  .sig-boxes{ display:inline-flex; vertical-align:middle; border-radius:3px; overflow:hidden; }
  .sig-boxes .b{
    padding: 1px 8px;
    font-size: 10.8px;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
    line-height: 1.5;
  }
  .sig-boxes .bg{ background: var(--sig-green);  color: #fff; }
  .sig-boxes .by{ background: var(--sig-yellow); color: #3a3000; }
  .sig-boxes .br{ background: var(--sig-red);    color: #fff; }
  .sig-suffix{ font-size: 10.8px; color: var(--ink-soft); margin-left: 6px; }
  /* Disqualification bell: 30s past red. Deliberately outside .sig-boxes so it
     reads as a separate marker, not a fourth light. */
  .sig-bell{
    display: inline-flex; align-items: center; gap: 3px;
    font-size: 10.8px; font-weight: 700; color: var(--ink-soft);
    margin-left: 7px; white-space: nowrap;
    font-variant-numeric: tabular-nums;
  }

  footer{
    padding: 12px 24px 18px;
    font-size: 11px;
    color: var(--ink-soft);
    border-top: 1px solid var(--line);
    display:flex;
    justify-content: space-between;
    align-items:center;
    flex-wrap: wrap;
    gap: 4px;
  }

  /* ---------- Responsive reflow ----------
     MUST stay 'screen and'. A width media query with no media type also
     matches PRINT, and the A4 page box is 190mm = 718.1px at 96dpi - UNDER
     this 720px breakpoint. So an unscoped block fires on paper: the mobile
     'aside{ border-top:2px solid var(--line) }' drew a grey line above the
     pane and shoved the whole brand box down 2px, so its yellow rule landed
     2px below the banner's and the top band read as misaligned (measured off
     Rama's print preview at 22.6px/mm: 11px grey = 1.84 CSS px, pane pushed
     down 12px = 2.01 CSS px - a dead match for the 2px border).
     Headless page.pdf() does NOT reproduce this - it lays out at the emulated
     viewport width, not the page box - so every automated check passed while
     the real preview was broken. Verified with a !important green border
     injected into this block: absent from the headless PDF, present on paper.
     The 480px block below is scoped for the same reason; it sets
     header{flex-direction:column}, which would wreck the banner outright. */
  @media screen and (max-width: 720px){
    /* On a phone the agenda is what you came for — it leads, and the reference
       blocks (Exco, District Officers, Links, Pathways) follow underneath. */
    .body-grid{ grid-template-columns: 1fr; }
    aside, main{ grid-column: 1; grid-row: auto; }
    aside{
      border-right: none;
      border-top: 2px solid var(--line);
      border-bottom: none;
    }
    header{ padding: 20px 18px 16px; }
    main{ padding: 16px 14px 22px; }
    .head-text .club{ font-size: 19px; }
  }
  @media screen and (max-width: 480px){
    .print-btn span.label{ display:none; }
    .print-btn{ padding: 9px; border-radius: 50%; }
    header{ flex-direction:column; align-items:flex-start; gap:12px; }
    thead th{ font-size: 9px; padding: 7px 6px; }
    th.col-time{ width: 56px; }
    th.col-holder{ width: 110px; }
    tbody td{ font-size: 11px; padding: 6px; }
    td.item .item-sub{ font-size: 10.3px; }
  }

  /* ---------- Interactive builder-preview mode ---------- */
  body.interactive td.item{ position:relative; }
  .row-tools{
    display:none; position:absolute; top:3px; right:3px; gap:2px; z-index:5;
    background:rgba(255,255,255,0.92); border:1px solid var(--line); border-radius:5px; padding:2px;
  }
  body.interactive tbody tr:hover .row-tools{ display:flex; }
  .row-tools button{
    border:none; background:transparent; width:22px; height:22px; cursor:pointer;
    font-size:11px; line-height:1; color:var(--ink-soft); border-radius:3px;
  }
  .row-tools button:hover{ background:var(--cream); color:var(--maroon); }
  body.interactive [contenteditable]{ border-bottom:1px dashed transparent; }
  body.interactive [contenteditable]:hover{ border-bottom:1px dashed var(--gray); cursor:text; }
  body.interactive [contenteditable]:focus{
    outline:2px solid var(--blue); outline-offset:1px; background:#eef4f8; border-bottom:1px dashed transparent;
  }
  @media print{ .row-tools{ display:none !important; } }

  /* Drag & drop directly on sheet rows (interactive mode) */
  body.interactive td.time{ position:relative; padding-left:24px; }
  .drag-grip{
    position:absolute; left:5px; top:9px; cursor:grab; color:var(--gray);
    display:none; font-size:13px; letter-spacing:-1px; user-select:none;
  }
  .drag-grip:active{ cursor:grabbing; }
  body.interactive tbody tr:hover .drag-grip{ display:inline; }
  tr.row-dragging td{ opacity:0.4; }
  tr.drop-above td{ border-top:3px solid var(--blue) !important; }
  tr.drop-below td{ border-bottom:3px solid var(--blue) !important; }
  @media print{ .drag-grip{ display:none !important; } }

  /* ---------- Inline edit row (builder preview only) ---------- */
  tr.row-editing td{ background:#eef4f8 !important; box-shadow:inset 0 0 0 2px var(--blue); }
  .row-edit{ padding:2px 0 6px; }
  .re-grid{ display:grid; grid-template-columns:1fr 1fr; gap:6px 10px; margin-bottom:6px; }
  .re-grid.re-g3{ grid-template-columns:1fr 1fr 1fr; }
  .re-f{ display:flex; flex-direction:column; gap:2px; min-width:0; }
  .re-f > span{
    font-size:9.5px; font-weight:700; text-transform:uppercase; letter-spacing:0.4px;
    color:var(--ink-soft);
  }
  .re-f input, .re-f select{
    font-family:inherit; font-size:12px; padding:4px 6px; border:1px solid var(--gray);
    border-radius:4px; background:#fff; color:var(--ink); width:100%; min-width:0;
  }
  .re-f input:focus, .re-f select:focus{ outline:2px solid var(--blue); outline-offset:0; border-color:var(--blue); }
  .re-f input:disabled{ background:#f2f2f0; color:#999; }
  .re-actions{ display:flex; gap:8px; margin-top:2px; }
  .re-done, .re-del{
    font-family:inherit; font-size:11.5px; font-weight:700; padding:5px 12px;
    border-radius:4px; cursor:pointer; border:1px solid transparent;
  }
  .re-done{ background:var(--blue); color:#fff; }
  .re-done:hover{ background:#00304a; }
  .re-del{ background:#fff; color:var(--tbd); border-color:#e3b3ac; }
  .re-del:hover{ background:#fdeeec; }
  .row-tools .rt-edit{ width:auto; padding:0 7px; font-weight:700; color:var(--blue); }
  @media print{ tr.row-editing td{ box-shadow:none; } }

  /* ---------- Project combobox (click ▾ to browse, type to narrow) ---------- */
  .cbx{ position:relative; width:100%; min-width:0; }
  .cbx .cbx-input{ width:100%; padding-right:26px; }
  .cbx-btn{
    position:absolute; top:0; right:0; height:100%; width:24px; padding:0;
    border:none; background:transparent; cursor:pointer; color:var(--ink-soft);
    font-size:11px; line-height:1;
  }
  .cbx-btn:hover{ color:var(--maroon); }
  .cbx.open .cbx-btn{ color:var(--maroon); transform:rotate(180deg); }
  .cbx-list{
    display:none; position:absolute; z-index:80; left:0; right:0; top:calc(100% + 2px);
    max-height:260px; overflow-y:auto; background:#fff; border:1px solid var(--blue);
    border-radius:5px; box-shadow:0 8px 22px rgba(0,0,0,0.18); padding:3px;
  }
  .cbx.open .cbx-list{ display:block; }
  .cbx.up .cbx-list{ top:auto; bottom:calc(100% + 2px); }
  .cbx-opt{
    display:flex; align-items:baseline; gap:8px; padding:4px 7px; border-radius:4px;
    cursor:pointer; line-height:1.25;
  }
  .cbx-opt.hide{ display:none; }
  .cbx-opt .cbx-n{ flex:1 1 auto; font-size:12.5px; color:var(--ink); }
  .cbx-opt .cbx-m{
    flex:0 0 auto; font-size:10.5px; color:var(--ink-soft); white-space:nowrap;
    font-variant-numeric:tabular-nums;
  }
  /* Projects that sit in the chosen pathway+level lead the list, ruled off from the rest. */
  .cbx-opt.here .cbx-n{ font-weight:700; }
  .cbx-opt.here + .cbx-opt:not(.here){ border-top:1px dashed var(--line); margin-top:3px; padding-top:6px; }
  .cbx-opt.sel{ background:#f3efe6; }
  .cbx-opt.act{ background:var(--blue); }
  .cbx-opt.act .cbx-n, .cbx-opt.act .cbx-m{ color:#fff; }
  .cbx-empty{ display:none; padding:6px 7px; font-size:11.5px; color:var(--ink-soft); font-style:italic; }
  @media print{ .cbx-list, .cbx-btn{ display:none !important; } }

  /* Role-player roster under TME Welcome Remarks */
  /* Role-player roster: appointment names right-aligned against a shared gutter,
     holder names left-aligned, so both columns line up down the block. */
  .role-roster{
    display:grid;
    grid-template-columns: max-content 1fr;
    column-gap: 8px;
    row-gap: 1px;
    margin-top: 4px;
    padding-left: 9px;
    border-left: 2px solid var(--gray);
    font-size: 12px;
    line-height: 1.45;
  }
  .role-roster .rr-label{
    text-align: right;
    font-weight: 600;
    color: var(--ink);
    white-space: nowrap;
  }
  .role-roster .rr-label::after{ content: ':'; }
  .role-roster .rr-name{ text-align: left; color: var(--ink-soft); }

  /* POETTS block on a prepared-speech row: Project (heading), then
     Evaluator · Timing · Title · Speaker — the order the TME introduces in. */
  .poetts{
    display:grid;
    grid-template-columns: max-content 1fr;
    column-gap: 8px;
    row-gap: 1px;
    margin-top: 4px;
    padding-left: 9px;
    border-left: 2px solid var(--yellow-deep);
    font-size: 12px;
    line-height: 1.45;
  }
  .poetts .rr-label{ text-align:right; font-weight:600; color:var(--ink); white-space:nowrap; }
  .poetts .rr-label::after{ content:':'; }
  .poetts .rr-name{ text-align:left; color:var(--ink-soft); }
  .poetts .sig-boxes{ margin-left:8px; }
  .re-grid.re-g4{ grid-template-columns:1fr 1fr 1fr 1fr; }

  /* Pathways legend: retired paths below a perforated rule */
  .path-legend .path-sep{
    margin: 6px 0 5px;
    border-top: 1px dashed var(--gray);
    padding-top: 5px;
    font-size: 9.5px;
    font-style: italic;
    color: var(--ink-soft);
  }
  .path-legend .path-retired{ color: var(--ink-soft); }
  .path-legend .path-retired b{ color: var(--ink-soft); }

  /* ================================================================
     SHEET STYLES — scoped under body.th-<key>. Classic = no overrides.
     Palettes stay in the Toastmasters family: True Maroon #772432,
     Loyal Blue #004165, Cool Gray #A9B2B1, Happy Yellow #F2DF74.
     ================================================================ */

  /* ---- Zine: riso screen-print, halftone, art-school poster ---- */
  body.th-zine{ --cream:#f8f3e6; --row-alt:#f3ecdb; --line:#d8cdb4; }
  body.th-zine .page{ background:#fbf7ec; }
  body.th-zine header, body.th-zine .pane-brand{
    background: var(--maroon);
    /* Softened in V26: was 0.22 alpha on a 5px pitch. A tight high-contrast dot
       screen is the single most compression-hostile thing on the sheet - it cost
       ~15% of the export budget in texture the eye barely reads at that size.
       Still visibly a riso screen, just kinder to the encoder. */
    background-image: radial-gradient(rgba(255,255,255,0.15) 1px, transparent 1px);
    background-size: 7px 7px;
    border-bottom: 5px solid #1e1a17;
  }
  body.th-zine .head-text .club{ text-transform: uppercase; letter-spacing: 1.5px; font-weight: 800; }
  body.th-zine .head-text .meeting-title{ color:#fff; background:#1e1a17; display:inline-block; padding:1px 8px; transform:rotate(-0.6deg); font-style:normal; }
  body.th-zine thead th{ background:#1e1a17; letter-spacing:1.2px; }
  body.th-zine tbody tr{ border-bottom:1.5px dashed #b8a98a; }
  body.th-zine aside h3{ border-bottom:3px double #1e1a17; color:#1e1a17; }
  body.th-zine .item-title{ text-transform: uppercase; letter-spacing: 0.3px; font-size: 12px; }
  body.th-zine footer{ border-top:3px double #1e1a17; }

  /* ---- Swiss: Müller-Brockmann grid, objective typography ---- */
  body.th-swiss{ --cream:#fff; --row-alt:#fff; --line:#1c1c1c; }
  body.th-swiss .page{ background:#fff; }
  body.th-swiss header, body.th-swiss .pane-brand{
    background:#fff; color:#1c1c1c; border-bottom:3px solid #1c1c1c; gap:24px;
  }
  body.th-swiss .head-text .club{ color:#1c1c1c; font-weight:800; letter-spacing:-0.5px; }
  body.th-swiss .head-text .clubnum{ color:#6a6a6a; }
  body.th-swiss .head-text .meeting-title{ color:var(--maroon); font-style:normal; font-weight:700; }
  body.th-swiss .meta-row{ color:#1c1c1c; }
  body.th-swiss .meta-row b{ color:var(--maroon); }
  body.th-swiss thead th{ background:#fff; color:#1c1c1c; border-bottom:3px solid #1c1c1c; text-transform:uppercase; }
  body.th-swiss tbody tr{ border-bottom:1px solid #1c1c1c; }
  body.th-swiss tbody tr.alt{ background:#fff; }
  body.th-swiss td.time{ color:#1c1c1c; }
  body.th-swiss aside{ background:#fff; border-right:1px solid #1c1c1c; }
  body.th-swiss aside h3{ color:#1c1c1c; border-bottom:2px solid #1c1c1c; }
  body.th-swiss .theme-strip{ background:#fff; border-left:4px solid var(--maroon); }
  body.th-swiss .flex-row{ background:#fff !important; }
  body.th-swiss .poetts{ border-left-color:#1c1c1c; }

  /* ---- Brutalist: hard borders, raw blocks, offset shadows ---- */
  body.th-brutalist{ --row-alt:#fff; --line:#111; --cream:#fff; }
  body.th-brutalist .page{ background:#fff; border:3px solid #111; }
  body.th-brutalist header, body.th-brutalist .pane-brand{
    background:var(--yellow); color:#111; border-bottom:3px solid #111;
  }
  body.th-brutalist .head-text .club{ color:#111; text-transform:uppercase; font-weight:800; letter-spacing:-0.5px; }
  body.th-brutalist .head-text .clubnum{ color:#111; }
  body.th-brutalist .head-text .meeting-title{ color:#fff; background:var(--maroon); display:inline-block; padding:2px 10px; font-style:normal; box-shadow:4px 4px 0 #111; }
  body.th-brutalist .meta-row{ color:#111; }
  body.th-brutalist .meta-row b{ color:var(--maroon); }
  body.th-brutalist thead th{ background:#111; }
  body.th-brutalist tbody tr{ border-bottom:2px solid #111; }
  body.th-brutalist td.time{ color:#111; }
  body.th-brutalist aside{ border-right:3px solid #111; }
  body.th-brutalist aside h3{ color:#111; border-bottom:3px solid #111; text-transform:uppercase; }
  body.th-brutalist .theme-strip{ border:2px solid #111; border-left:8px solid var(--maroon); background:#fff; }
  body.th-brutalist .tbd{ border:2px solid #111; border-radius:0; background:var(--yellow); color:#111; }
  body.th-brutalist .sig-boxes{ border:2px solid #111; border-radius:0; }
  body.th-brutalist .flex-badge{ border:2px solid #111; border-radius:0; color:#111; }

  /* ---- Retro-Futurism: 1970s space-age optimism, NASA-worm confidence ----
     Loyal Blue is the ground, Happy Yellow is the light source. Everything is a
     capsule: pill chips, rounded lights, wide-tracked caps. Brand palette only. */
  body.th-retrofuture{ --row-alt:#eef3f7; --line:#c2d6e4; --cream:#f2f7fa; }
  body.th-retrofuture .page{ background:#fbfdfe; }
  body.th-retrofuture header, body.th-retrofuture .pane-brand{
    background: linear-gradient(to bottom, #005a8c 0%, var(--blue) 55%, #00243a 100%);
    border-bottom: 5px solid var(--yellow);
  }
  body.th-retrofuture .head-text .club{
    text-transform:uppercase; letter-spacing:3px; font-weight:800;
    text-shadow: 0 0 14px rgba(242,223,116,0.5);
  }
  body.th-retrofuture .head-text .clubnum{ letter-spacing:2.2px; text-transform:uppercase; color:#bcdcf0; }
  body.th-retrofuture .head-text .meeting-title{ color:var(--yellow); font-style:normal; letter-spacing:1px; }
  body.th-retrofuture .meta-row b{ color:var(--yellow); }
  body.th-retrofuture thead th{ background:var(--blue); letter-spacing:2px; }
  body.th-retrofuture td.time{ color:var(--blue); letter-spacing:0.4px; }
  body.th-retrofuture .item-title{ color:#00243a; }
  body.th-retrofuture tbody tr{ border-bottom:1px solid #c2d6e4; }
  body.th-retrofuture aside{ background:#f2f7fa; }
  body.th-retrofuture aside h3{
    color:var(--blue); border-bottom:2px solid var(--yellow-deep);
    letter-spacing:2px;
  }
  body.th-retrofuture .exco-role{ color:var(--blue); }
  body.th-retrofuture .theme-strip{
    background:#eef3f7; border-left:6px solid var(--yellow); border-radius:0 999px 999px 0;
  }
  body.th-retrofuture .poetts{ border-left-color:var(--blue); }
  body.th-retrofuture .rr-label{ color:var(--blue); }
  body.th-retrofuture .tbd{ border-radius:999px; }
  body.th-retrofuture .flex-badge{ border-radius:999px; border-style:solid; }
  body.th-retrofuture .sig-boxes{ border-radius:999px; }
  body.th-retrofuture .sig-boxes .b{ padding:1px 9px; }
  body.th-retrofuture footer{ border-top:2px solid var(--blue); }

  /* ---- Handmade & Village: kraft paper, warm ink, nothing machine-perfect ----
     Softened maroon on warm stock, humanist serif headings, dashed rules that
     read as hand-ruled. The yellow is dialled to a deeper ochre so it sits with
     the paper rather than glowing off it. */
  body.th-handmade{ --row-alt:#f4ece0; --line:#d8c5aa; --cream:#f8f1e6; --ink:#3b2f26; --ink-soft:#6b5a4a; }
  body.th-handmade .page{ background:#fbf6ec; }
  /* Brand faces, not a serif. The Georgia/Palatino stack read as period costume;
     Rama asked for "a tad more conventional" (V26), so the warmth now comes from
     the paper, the ochre and the dashed rules - not the typography. */
  body.th-handmade header, body.th-handmade .pane-brand{
    background: linear-gradient(to bottom, #8a3a44 0%, #6d2632 100%);
    border-bottom: 5px solid var(--yellow-deep);
  }
  body.th-handmade .head-text .club{ font-weight:700; letter-spacing:0.2px; }
  body.th-handmade .head-text .clubnum{ color:#e8d6c4; letter-spacing:1px; }
  body.th-handmade .head-text .meeting-title{ color:#f6e3b8; }
  body.th-handmade .meta-row b{ color:#f6e3b8; }
  body.th-handmade thead th{ background:#6d2632; letter-spacing:0.8px; }
  body.th-handmade tbody tr{ border-bottom:1.5px dashed #d8c5aa; }
  body.th-handmade tbody tr.alt{ background:#f4ece0; }
  body.th-handmade td.time{ color:#8a3a44; }
  body.th-handmade aside{ background:#f8f1e6; }
  body.th-handmade aside h3{
    color:#6d2632; border-bottom:2px dashed var(--yellow-deep); letter-spacing:0.6px;
  }
  body.th-handmade .exco-role{ color:#3b2f26; }
  body.th-handmade .theme-strip{
    background:#f4ece0; border-left:4px solid var(--yellow-deep); border-radius:3px;
  }
  body.th-handmade .poetts{ border-left-color:#c9ab84; }
  body.th-handmade .rr-label{ color:#6d2632; }
  body.th-handmade .tbd{ border-radius:10px 3px 10px 3px; }
  body.th-handmade .flex-badge{ border-radius:10px 3px 10px 3px; border-style:dashed; }
  body.th-handmade footer{ border-top:1.5px dashed #d8c5aa; }

  /* ================= PRINT =================
     Kept LAST in this file on purpose. Theme rules are body.th-* (two
     classes) and several of them target the same elements the print rules
     do, so at equal specificity source order decides. Print must win —
     move this block and brutalist's page border and zine's item
     titles silently take over again. */
  @media print{
    /* A real 1 cm margin all round. The browser's own header/footer can only be
       switched off in the print dialog — CSS has no say; the toolbar hint covers it. */
    @page{ size: A4; margin: 10mm; }
    body{ background:#fff; }
    .print-fab{ display:none; }
    .page-wrap{ padding:0; display:block; }
    /* No border/padding on the page wrapper in print: the paper edge is the frame.
       A theme border here (brutalist has 3px) pushes the in-flow banner down while
       the fixed pane stays anchored to the page box, so the two overlap. body-level
       specificity beats the body.th-* theme rules. */
    body[class] .page{
      box-shadow:none; border-radius:0; max-width:100%; overflow:visible;
      position:relative; border:0; padding:0;
    }
    * { -webkit-print-color-adjust: exact; print-color-adjust: exact; }

    /* Reference pane is fixed, so it repeats on every printed page (Rama's call),
       sitting inside the 1 cm page margins. The agenda flows to its right. */
    .body-grid{ display:block; }
    aside, main{ grid-column: auto; grid-row: auto; }
    /* Pane is position:fixed again - identical on every page, which is exactly
       what we want now. The page-2 dead-gap that forced the per-page absolute
       copies is gone because the pane's top band is no longer empty space
       waiting for a banner: it holds the brand box, which belongs on every page.
       (For the record, per-page absolute copies DO work - copies at top:33mm and
       277mm landed on pages 1 and 2 - but the count has to match the real page
       count exactly, because a copy positioned past the end of the content
       forces an extra page, and neither overflow:hidden nor a zero-height anchor
       contains that. Fixed positioning has no such landmine.) */
    aside.ref-pane{
      position: fixed;
      top: 0; left: 0; bottom: var(--print-foot);
      width: var(--print-pane);
      overflow: hidden;
      padding: 0;
      border-right: none;   /* moved to .pane-body - see below */
      border-bottom: none;
      /* Belt and braces. The responsive block is scoped to 'screen' now, so
         nothing should reach this - but a stray border here is exactly the
         defect that shipped in V14-V19 (grey line above the pane, brand box
         pushed 2px below the banner), and it was invisible to headless
         testing for six versions. Zero it explicitly. */
      border-top: none;
      column-count: 1;
      font-size: 10.5px;
      background: #fff;
    }
    /* Brand box height is locked to the banner height so the two line up into a
       single band across the top of page 1. */
    /* Must match the banner exactly - same height, same bottom rule - or the
       two halves of the top band don't line up. Do not give this its own
       border width. */
    .pane-brand{
      height: var(--print-head);
      padding: 2mm;
      box-sizing: border-box;
    }
    .pane-brand img{ width: auto; height: 100%; max-width: 100%; }
    /* Carries the pane's column rule so it starts BELOW the brand box - on the
       aside it ran the full height and drew a pale seam across the dark band. */
    .pane-body{
      padding: 3.5mm 4mm 0 0;
      border-right: 1px solid var(--line);
      height: calc(100% - var(--print-head));
      box-sizing: border-box;
    }

    main{ margin-left: var(--print-pane); padding: 3mm 0 2mm 6mm; }
    /* Title banner: full page width, page 1 only. Fixed --print-head height with
       overflow:hidden, because the per-page pane copies are positioned at hard
       offsets and need the banner height to be a known constant; a banner that
       grew with a long theme or address would collide with pane copy 1.
       It cannot repeat on later pages: Chrome clips fixed elements to the page
       content box, so a banner living in the @page margin band is never painted
       (measured - 'top:-22mm' and 'translateY(-22mm)' both rendered nothing, and
       so did a negative margin-top on an in-flow header). Making it repeat would
       need a spacer row inside the agenda table's repeating thead. */
    header{
      /* Tucked 0.4mm UNDER the pane so the two halves of the band overlap instead
         of merely abutting - abutting left a sub-pixel hairline at the join.
         The overlap is safe whichever element paints on top: both carry the same
         vertical gradient over the same height, so the colours match exactly at
         every y, and 0.4mm is far too small to reach the logo. padding-left adds
         the 0.4mm back so the text sits where it did. */
      margin-left: calc(var(--print-pane) - 0.4mm);
      height: var(--print-head);
      padding: 3mm 5mm 3mm calc(5mm + 0.4mm);
      gap: 0;
      overflow: hidden;
      align-items: center;
      break-after: avoid;
      break-inside: avoid;
    }
    /* The logo has moved to the pane, so the club name gets the full banner
       width - sized up to use it, with the rest of the block scaled to match. */
    .head-text{ width: 100%; }
    .head-text .club{ font-size: 21px; line-height: 1.1; margin: 0 0 1mm; }
    .head-text .clubnum{ font-size: 10.5px; margin: 0 0 1.2mm; opacity: 0.9; }
    .head-text .meeting-title{ font-size: 13px; margin: 0 0 1.2mm; line-height: 1.2; }
    .meta-row{ gap: 1mm 6mm; font-size: 10px; margin-top: 0; line-height: 1.35; }
    .cadence{ margin: 1.2mm 0 0; font-size: 9px; letter-spacing: 0; }
    /* Zine and Brutalist set the theme line as an inline-block with a hard drop
       shadow, which lands on the date line once the banner is compressed for
       print. Buy it clearance. */
    body.th-zine .meeting-title, body.th-brutalist .meeting-title{ margin-bottom: 1.6mm; }

    /* Club line + generated date rule off the FULL page width at the foot of every
       page — deliberately not inset past the reference pane. */
    footer{
      position: fixed;
      bottom: 0; left: 0; right: 0;
      margin-left: 0;
      height: var(--print-foot);
      box-sizing: border-box;
      padding: 1.5mm 0 0;
      border-top: 1px solid var(--line);
      background: #fff;
    }

    /* V21 put four speeches and four evaluations in the template instead of
       three and three. Those two extra rows tipped the sheet onto a third page.
       Tightening the row padding buys back roughly 33mm over 25 rows, which
       fits it inside two pages again without shrinking any type. If a future
       change adds rows, this is the first dial to turn - measured, not guessed:
       checkall.py fails on page count the moment it stops fitting. */
    /* Turned again. The Language Evaluator role adds a 26th row and the filled
       sheet was already reaching a third page in classic, zine and swiss, so
       there was nothing left to absorb it. A pixel off each side of 26 rows is
       still the cheapest space on the sheet, and the row rules do the
       separating, so nothing reads as crowded. The leading comes down with it:
       1.42 was chosen for a screen read, and a table of one- and two-line
       entries does not need that much air between lines that rarely wrap. */
    tbody td{ padding: 4.5px 10px; line-height: 1.36; }

    /* The FLEXIBLE explainer earns its place on screen and wastes a line on
       paper - the badges in the rows already say it (Rama, V21). */
    .schedule-note{ display: none; }

    /* Sub-notes 12.3px -> 11.5px on paper. The Award Presentation row gained a
       sub line in V27 and three themes were within ~4mm of page 2's edge; this
       is the lightest trim that clears all six. Measured via pgprobe. */
    td.item .item-sub{ font-size: 11.5px; line-height: 1.3; margin-top: 1px; }

    /* The POETTS block under a prepared speech and the role roster under a
       grouped role row are the densest thing on the sheet and the loosest set:
       five or six short label/value pairs, each on its own grid row, each with
       a 1px gutter and 1.45 leading meant for the screen. They are read one line
       at a time off a table, so the gutter is doing no work on paper - it is
       ~45 lines of the agenda and the single biggest block win after the rows. */
    .poetts, .role-roster{ margin-top: 2px; row-gap: 0; line-height: 1.34; }
    /* The timing lights sit inside those blocks; their own leading and the gap
       above them were sized against the looser screen block. */
    .signal-line{ margin-top: 2px; }
    .sig-boxes .b{ line-height: 1.35; }

    /* The column head repeats on both printed pages, so every pixel here costs
       twice. 8px of padding was sized for a 13px screen table; the heads are
       11.5px caps in a solid maroon band and hold their weight on less. */
    thead th{ padding: 6px 10px; }

    /* The theme strip is one line of text in a tinted box. On screen it wants
       air around it; on paper it is a caption above the agenda and the 14px
       margin below it was reading as a gap, not as separation. */
    .theme-strip{ padding: 4px 12px; margin-bottom: 8px; font-size: 11.5px; }

    aside h3{ font-size: 10px; margin-bottom: 6px; padding-bottom: 3px; }
    .exco-block{ margin-bottom: 10px; break-inside: avoid; }
    .exco-item{ margin-bottom: 4px; }
    .exco-role{ font-size: 9.5px; }
    .exco-name{ font-size: 10px; }
    .exco-sub{ font-size: 9px; }
    .path-legend div{ font-size: 9.5px; margin-bottom: 2px; }
    .announcements .announce-line{ font-size: 9.5px; margin-bottom: 3px; }
    .holder-pair .hp-line{ line-height: 1.3; font-size: 10px; }
    .announcements .announce-gap{ height: 3px; }

    /* Zine's uppercase + tracking and Terminal's monospace item titles run the
       agenda two rows past page 2. Tightened here only, so the themes keep their
       character on screen. Measured: both land in 2 pages with this. */
    body.th-zine .item-title, body.th-brutalist .item-title,
 body.th-handmade .item-title{
      font-size: 11px; letter-spacing: 0;
    }
    /* Confessional sets a monospace body face, ~15% wider than the sans - the
       same trap Terminal hit. Body copy reverts to the sans on paper; the mono
       is kept where the theme actually reads. */
      font-family: "Source Sans 3", "Myriad Pro", Arial, sans-serif;
    }
    /* Retro-Futurism's wide tracking is the whole point on screen and pure cost
       on paper, where the column is 45mm narrower. Measured: tracking alone left
       it on three pages, so the item titles come back to the base size too. */
    body.th-retrofuture .head-text .club{ letter-spacing: 1.4px; }
    body.th-retrofuture thead th{ letter-spacing: 0.8px; }
    body.th-retrofuture aside h3{ letter-spacing: 0.8px; }
    body.th-retrofuture .item-title{ font-size: 11px; letter-spacing: 0; }
    body.th-retrofuture td.time{ letter-spacing: 0; }
    /* Confessional's underlined mono titles and Handmade's serif both sit wider
       than the sans; trim the sub-line as well as the title. */
 body.th-handmade td.item .item-sub,
    body.th-retrofuture td.item .item-sub{ font-size: 11px; }
    /* Brutalist rules every row at 2px and Zine sets its titles in tracked-out
       uppercase; with 25 rows those two were the last pair still spilling onto a
       third page. Trimmed here only, so both keep their look on screen. */
    body.th-brutalist tbody tr{ border-bottom-width: 1px; }
    body.th-zine td.item .item-sub, body.th-brutalist td.item .item-sub{ font-size: 11px; }
    /* Terminal sets monospace on the whole body, which is ~15% wider than the
       body face and spills a third page (verified: forcing the sans back drops it
       to 2). On paper, fitting beats the typeface joke — so body copy reverts to
       the sans in print and the mono is kept where the theme actually reads: the
       banner, the column heads and the pane headings. */
      font-family: "Source Sans 3", "Myriad Pro", Arial, sans-serif;
    }
      font-family: ui-monospace, 'Cascadia Mono', 'Courier New', monospace;
    }

    /* Zine's uppercase+tracking and Terminal's monospace item titles run the
       agenda two rows past page 2. Tightened in print only, so both themes keep
       their character on screen. */
    body.th-zine .item-title{
      font-size: 11px; letter-spacing: 0;
    }

    table{ break-before: auto; }
    thead{ display: table-header-group; }
    tbody tr{ break-inside: avoid; }
  }
`;
const LOGO_B64 = "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";
const PATHWAYS_DATA = {"paths": [{"abbr": "DL", "name": "Dynamic Leadership", "retired": false}, {"abbr": "EH", "name": "Engaging Humor", "retired": false}, {"abbr": "MS", "name": "Motivational Strategies", "retired": false}, {"abbr": "PI", "name": "Persuasive Influence", "retired": false}, {"abbr": "PM", "name": "Presentation Mastery", "retired": false}, {"abbr": "VC", "name": "Visionary Communication", "retired": false}, {"abbr": "EC", "name": "Effective Coaching", "retired": true}, {"abbr": "IP", "name": "Innovative Planning", "retired": true}, {"abbr": "LD", "name": "Leadership Development", "retired": true}, {"abbr": "SR", "name": "Strategic Relationships", "retired": true}, {"abbr": "TC", "name": "Team Collaboration", "retired": true}], "levels": {"DL": {"1": [{"n": "Ice Breaker", "e": false}, {"n": "Writing a Speech with Purpose", "e": false}, {"n": "Introduction to Vocal Variety and Body Language", "e": false}, {"n": "Evaluation and Feedback", "e": false}], "2": [{"n": "Understanding Your Leadership Style", "e": false}, {"n": "Understanding Your Communication Style", "e": false}, {"n": "Introduction to Toastmasters Mentoring", "e": false}], "3": [{"n": "Negotiate the Best Outcome", "e": false}, {"n": "Deliver Social Speeches", "e": true}, {"n": "Using Presentation Software", "e": true}, {"n": "Connect with Storytelling", "e": true}, {"n": "Creating Effective Visual Aids", "e": true}, {"n": "Using Descriptive Language", "e": true}, {"n": "Connect with Your Audience", "e": true}, {"n": "Make Connections Through Networking", "e": true}, {"n": "Focus on the Positive", "e": true}, {"n": "Inspire Your Audience", "e": true}, {"n": "Prepare for an Interview", "e": true}, {"n": "Understanding Vocal Variety", "e": true}, {"n": "Effective Body Language", "e": true}, {"n": "Active Listening", "e": true}], "4": [{"n": "Manage Change", "e": false}, {"n": "Create a Podcast", "e": true}, {"n": "Building a Social Media Presence", "e": true}, {"n": "Managing a Difficult Audience", "e": true}, {"n": "Write a Compelling Blog", "e": true}, {"n": "Manage Online Meetings", "e": true}, {"n": "Question-and-Answer Session", "e": true}, {"n": "Public Relations Strategies", "e": true}, {"n": "Manage Projects Successfully", "e": true}], "5": [{"n": "Lead in Any Situation", "e": false}, {"n": "Lessons Learned", "e": true}, {"n": "Moderate a Panel Discussion", "e": true}, {"n": "Ethical Leadership", "e": true}, {"n": "Leading in Your Volunteer Organization", "e": true}, {"n": "Prepare to Speak Professionally", "e": true}, {"n": "High Performance Leadership", "e": true}, {"n": "Reflect on Your Path", "e": false}]}, "EH": {"1": [{"n": "Ice Breaker", "e": false}, {"n": "Writing a Speech with Purpose", "e": false}, {"n": "Introduction to Vocal Variety and Body Language", "e": false}, {"n": "Evaluation and Feedback", "e": false}], "2": [{"n": "Know Your Sense of Humor", "e": false}, {"n": "Connect with Your Audience", "e": false}, {"n": "Introduction to Toastmasters Mentoring", "e": false}], "3": [{"n": "Engage Your Audience with Humor", "e": false}, {"n": "Deliver Social Speeches", "e": true}, {"n": "Using Presentation Software", "e": true}, {"n": "Connect with Storytelling", "e": true}, {"n": "Creating Effective Visual Aids", "e": true}, {"n": "Using Descriptive Language", "e": true}, {"n": "Make Connections Through Networking", "e": true}, {"n": "Focus on the Positive", "e": true}, {"n": "Inspire Your Audience", "e": true}, {"n": "Prepare for an Interview", "e": true}, {"n": "Understanding Vocal Variety", "e": true}, {"n": "Effective Body Language", "e": true}, {"n": "Active Listening", "e": true}, {"n": "Researching and Presenting", "e": true}], "4": [{"n": "The Power of Humor in an Impromptu Speech", "e": false}, {"n": "Create a Podcast", "e": true}, {"n": "Building a Social Media Presence", "e": true}, {"n": "Managing a Difficult Audience", "e": true}, {"n": "Write a Compelling Blog", "e": true}, {"n": "Manage Online Meetings", "e": true}, {"n": "Question-and-Answer Session", "e": true}, {"n": "Public Relations Strategies", "e": true}, {"n": "Manage Projects Successfully", "e": true}], "5": [{"n": "Deliver Your Message with Humor", "e": false}, {"n": "Lessons Learned", "e": true}, {"n": "Moderate a Panel Discussion", "e": true}, {"n": "Ethical Leadership", "e": true}, {"n": "Leading in Your Volunteer Organization", "e": true}, {"n": "Prepare to Speak Professionally", "e": true}, {"n": "High Performance Leadership", "e": true}, {"n": "Reflect on Your Path", "e": false}]}, "MS": {"1": [{"n": "Ice Breaker", "e": false}, {"n": "Writing a Speech with Purpose", "e": false}, {"n": "Introduction to Vocal Variety and Body Language", "e": false}, {"n": "Evaluation and Feedback", "e": false}], "2": [{"n": "Active Listening", "e": false}, {"n": "Understanding Your Communication Style", "e": false}, {"n": "Introduction to Toastmasters Mentoring", "e": false}], "3": [{"n": "Understanding Emotional Intelligence", "e": false}, {"n": "Deliver Social Speeches", "e": true}, {"n": "Using Presentation Software", "e": true}, {"n": "Connect with Storytelling", "e": true}, {"n": "Creating Effective Visual Aids", "e": true}, {"n": "Using Descriptive Language", "e": true}, {"n": "Connect with Your Audience", "e": true}, {"n": "Make Connections Through Networking", "e": true}, {"n": "Focus on the Positive", "e": true}, {"n": "Inspire Your Audience", "e": true}, {"n": "Prepare for an Interview", "e": true}, {"n": "Understanding Vocal Variety", "e": true}, {"n": "Effective Body Language", "e": true}, {"n": "Know Your Sense of Humor", "e": true}, {"n": "Researching and Presenting", "e": true}], "4": [{"n": "Motivate Others", "e": false}, {"n": "Create a Podcast", "e": true}, {"n": "Building a Social Media Presence", "e": true}, {"n": "Managing a Difficult Audience", "e": true}, {"n": "Write a Compelling Blog", "e": true}, {"n": "Manage Online Meetings", "e": true}, {"n": "Question-and-Answer Session", "e": true}, {"n": "Public Relations Strategies", "e": true}, {"n": "Manage Projects Successfully", "e": true}], "5": [{"n": "Team Building", "e": false}, {"n": "Lessons Learned", "e": true}, {"n": "Moderate a Panel Discussion", "e": true}, {"n": "Ethical Leadership", "e": true}, {"n": "Leading in Your Volunteer Organization", "e": true}, {"n": "Prepare to Speak Professionally", "e": true}, {"n": "High Performance Leadership", "e": true}, {"n": "Reflect on Your Path", "e": false}]}, "PI": {"1": [{"n": "Ice Breaker", "e": false}, {"n": "Writing a Speech with Purpose", "e": false}, {"n": "Introduction to Vocal Variety and Body Language", "e": false}, {"n": "Evaluation and Feedback", "e": false}], "2": [{"n": "Understanding Your Leadership Style", "e": false}, {"n": "Active Listening", "e": false}, {"n": "Introduction to Toastmasters Mentoring", "e": false}], "3": [{"n": "Understanding Conflict Resolution", "e": false}, {"n": "Deliver Social Speeches", "e": true}, {"n": "Using Presentation Software", "e": true}, {"n": "Connect with Storytelling", "e": true}, {"n": "Creating Effective Visual Aids", "e": true}, {"n": "Using Descriptive Language", "e": true}, {"n": "Connect with Your Audience", "e": true}, {"n": "Make Connections Through Networking", "e": true}, {"n": "Focus on the Positive", "e": true}, {"n": "Inspire Your Audience", "e": true}, {"n": "Prepare for an Interview", "e": true}, {"n": "Understanding Vocal Variety", "e": true}, {"n": "Effective Body Language", "e": true}, {"n": "Know Your Sense of Humor", "e": true}, {"n": "Researching and Presenting", "e": true}], "4": [{"n": "Leading in Difficult Situations", "e": false}, {"n": "Create a Podcast", "e": true}, {"n": "Building a Social Media Presence", "e": true}, {"n": "Managing a Difficult Audience", "e": true}, {"n": "Write a Compelling Blog", "e": true}, {"n": "Manage Online Meetings", "e": true}, {"n": "Question-and-Answer Session", "e": true}, {"n": "Public Relations Strategies", "e": true}, {"n": "Manage Projects Successfully", "e": true}], "5": [{"n": "High Performance Leadership", "e": false}, {"n": "Lessons Learned", "e": true}, {"n": "Moderate a Panel Discussion", "e": true}, {"n": "Ethical Leadership", "e": true}, {"n": "Leading in Your Volunteer Organization", "e": true}, {"n": "Prepare to Speak Professionally", "e": true}, {"n": "Reflect on Your Path", "e": false}]}, "PM": {"1": [{"n": "Ice Breaker", "e": false}, {"n": "Writing a Speech with Purpose", "e": false}, {"n": "Introduction to Vocal Variety and Body Language", "e": false}, {"n": "Evaluation and Feedback", "e": false}], "2": [{"n": "Understanding Your Communication Style", "e": false}, {"n": "Effective Body Language", "e": false}, {"n": "Introduction to Toastmasters Mentoring", "e": false}], "3": [{"n": "Persuasive Speaking", "e": false}, {"n": "Deliver Social Speeches", "e": true}, {"n": "Using Presentation Software", "e": true}, {"n": "Connect with Storytelling", "e": true}, {"n": "Creating Effective Visual Aids", "e": true}, {"n": "Using Descriptive Language", "e": true}, {"n": "Connect with Your Audience", "e": true}, {"n": "Make Connections Through Networking", "e": true}, {"n": "Focus on the Positive", "e": true}, {"n": "Inspire Your Audience", "e": true}, {"n": "Prepare for an Interview", "e": true}, {"n": "Understanding Vocal Variety", "e": true}, {"n": "Active Listening", "e": true}, {"n": "Know Your Sense of Humor", "e": true}, {"n": "Researching and Presenting", "e": true}], "4": [{"n": "Managing a Difficult Audience", "e": false}, {"n": "Create a Podcast", "e": true}, {"n": "Building a Social Media Presence", "e": true}, {"n": "Write a Compelling Blog", "e": true}, {"n": "Manage Online Meetings", "e": true}, {"n": "Question-and-Answer Session", "e": true}, {"n": "Public Relations Strategies", "e": true}, {"n": "Manage Projects Successfully", "e": true}], "5": [{"n": "Prepare to Speak Professionally", "e": false}, {"n": "Lessons Learned", "e": true}, {"n": "Moderate a Panel Discussion", "e": true}, {"n": "Ethical Leadership", "e": true}, {"n": "Leading in Your Volunteer Organization", "e": true}, {"n": "High Performance Leadership", "e": true}, {"n": "Reflect on Your Path", "e": false}]}, "VC": {"1": [{"n": "Ice Breaker", "e": false}, {"n": "Writing a Speech with Purpose", "e": false}, {"n": "Introduction to Vocal Variety and Body Language", "e": false}, {"n": "Evaluation and Feedback", "e": false}], "2": [{"n": "Understanding Your Leadership Style", "e": false}, {"n": "Understanding Your Communication Style", "e": false}, {"n": "Introduction to Toastmasters Mentoring", "e": false}], "3": [{"n": "Develop a Communication Plan", "e": false}, {"n": "Deliver Social Speeches", "e": true}, {"n": "Using Presentation Software", "e": true}, {"n": "Connect with Storytelling", "e": true}, {"n": "Creating Effective Visual Aids", "e": true}, {"n": "Using Descriptive Language", "e": true}, {"n": "Connect with Your Audience", "e": true}, {"n": "Make Connections Through Networking", "e": true}, {"n": "Focus on the Positive", "e": true}, {"n": "Inspire Your Audience", "e": true}, {"n": "Prepare for an Interview", "e": true}, {"n": "Understanding Vocal Variety", "e": true}, {"n": "Effective Body Language", "e": true}, {"n": "Active Listening", "e": true}, {"n": "Know Your Sense of Humor", "e": true}, {"n": "Researching and Presenting", "e": true}], "4": [{"n": "Communicate Change", "e": false}, {"n": "Create a Podcast", "e": true}, {"n": "Building a Social Media Presence", "e": true}, {"n": "Managing a Difficult Audience", "e": true}, {"n": "Write a Compelling Blog", "e": true}, {"n": "Manage Online Meetings", "e": true}, {"n": "Question-and-Answer Session", "e": true}, {"n": "Public Relations Strategies", "e": true}, {"n": "Manage Projects Successfully", "e": true}], "5": [{"n": "Develop Your Vision", "e": false}, {"n": "Lessons Learned", "e": true}, {"n": "Moderate a Panel Discussion", "e": true}, {"n": "Ethical Leadership", "e": true}, {"n": "High Performance Leadership", "e": true}, {"n": "Leading in Your Volunteer Organization", "e": true}, {"n": "Prepare to Speak Professionally", "e": true}, {"n": "Reflect on Your Path", "e": false}]}, "EC": {"1": [{"n": "Ice Breaker", "e": false}, {"n": "Writing a Speech with Purpose", "e": false}, {"n": "Introduction to Vocal Variety and Body Language", "e": false}, {"n": "Evaluation and Feedback", "e": false}], "2": [{"n": "Understanding Your Leadership Style", "e": false}, {"n": "Understanding Your Communication Style", "e": false}, {"n": "Introduction to Toastmasters Mentoring", "e": false}], "3": [{"n": "Reaching Consensus", "e": false}, {"n": "Deliver Social Speeches", "e": true}, {"n": "Using Presentation Software", "e": true}, {"n": "Connect with Storytelling", "e": true}, {"n": "Creating Effective Visual Aids", "e": true}, {"n": "Using Descriptive Language", "e": true}, {"n": "Connect with Your Audience", "e": true}, {"n": "Make Connections Through Networking", "e": true}, {"n": "Focus on the Positive", "e": true}, {"n": "Inspire Your Audience", "e": true}, {"n": "Prepare for an Interview", "e": true}, {"n": "Understanding Vocal Variety", "e": true}, {"n": "Effective Body Language", "e": true}, {"n": "Active Listening", "e": true}], "4": [{"n": "Improvement Through Positive Coaching", "e": false}, {"n": "Create a Podcast", "e": true}, {"n": "Building a Social Media Presence", "e": true}, {"n": "Managing a Difficult Audience", "e": true}, {"n": "Write a Compelling Blog", "e": true}, {"n": "Manage Online Meetings", "e": true}, {"n": "Question-and-Answer Session", "e": true}, {"n": "Public Relations Strategies", "e": true}, {"n": "Manage Projects Successfully", "e": true}], "5": [{"n": "High Performance Leadership", "e": false}, {"n": "Lessons Learned", "e": true}, {"n": "Moderate a Panel Discussion", "e": true}, {"n": "Ethical Leadership", "e": true}, {"n": "Leading in Your Volunteer Organization", "e": true}, {"n": "Prepare to Speak Professionally", "e": true}, {"n": "Reflect on Your Path", "e": false}]}, "IP": {"1": [{"n": "Ice Breaker", "e": false}, {"n": "Writing a Speech with Purpose", "e": false}, {"n": "Introduction to Vocal Variety and Body Language", "e": false}, {"n": "Evaluation and Feedback", "e": false}], "2": [{"n": "Understanding Your Leadership Style", "e": false}, {"n": "Connect with Your Audience", "e": false}, {"n": "Introduction to Toastmasters Mentoring", "e": false}], "3": [{"n": "Present a Proposal", "e": false}, {"n": "Deliver Social Speeches", "e": true}, {"n": "Using Presentation Software", "e": true}, {"n": "Connect with Storytelling", "e": true}, {"n": "Creating Effective Visual Aids", "e": true}, {"n": "Using Descriptive Language", "e": true}, {"n": "Make Connections Through Networking", "e": true}, {"n": "Focus on the Positive", "e": true}, {"n": "Inspire Your Audience", "e": true}, {"n": "Prepare for an Interview", "e": true}, {"n": "Understanding Vocal Variety", "e": true}, {"n": "Effective Body Language", "e": true}, {"n": "Active Listening", "e": true}], "4": [{"n": "Manage Projects Successfully", "e": false}, {"n": "Create a Podcast", "e": true}, {"n": "Building a Social Media Presence", "e": true}, {"n": "Managing a Difficult Audience", "e": true}, {"n": "Write a Compelling Blog", "e": true}, {"n": "Manage Online Meetings", "e": true}, {"n": "Question-and-Answer Session", "e": true}, {"n": "Public Relations Strategies", "e": true}], "5": [{"n": "High Performance Leadership", "e": false}, {"n": "Lessons Learned", "e": true}, {"n": "Moderate a Panel Discussion", "e": true}, {"n": "Ethical Leadership", "e": true}, {"n": "Leading in Your Volunteer Organization", "e": true}, {"n": "Prepare to Speak Professionally", "e": true}, {"n": "Reflect on Your Path", "e": false}]}, "LD": {"1": [{"n": "Ice Breaker", "e": false}, {"n": "Writing a Speech with Purpose", "e": false}, {"n": "Introduction to Vocal Variety and Body Language", "e": false}, {"n": "Evaluation and Feedback", "e": false}], "2": [{"n": "Understanding Your Leadership Style", "e": false}, {"n": "Managing Time", "e": false}, {"n": "Introduction to Toastmasters Mentoring", "e": false}], "3": [{"n": "Planning and Implementing", "e": false}, {"n": "Deliver Social Speeches", "e": true}, {"n": "Using Presentation Software", "e": true}, {"n": "Connect with Storytelling", "e": true}, {"n": "Creating Effective Visual Aids", "e": true}, {"n": "Using Descriptive Language", "e": true}, {"n": "Connect with Your Audience", "e": true}, {"n": "Make Connections Through Networking", "e": true}, {"n": "Focus on the Positive", "e": true}, {"n": "Inspire Your Audience", "e": true}, {"n": "Prepare for an Interview", "e": true}, {"n": "Understanding Vocal Variety", "e": true}, {"n": "Effective Body Language", "e": true}, {"n": "Active Listening", "e": true}, {"n": "Know Your Sense of Humor", "e": true}, {"n": "Researching and Presenting", "e": true}], "4": [{"n": "Leading Your Team", "e": false}, {"n": "Create a Podcast", "e": true}, {"n": "Building a Social Media Presence", "e": true}, {"n": "Managing a Difficult Audience", "e": true}, {"n": "Write a Compelling Blog", "e": true}, {"n": "Manage Online Meetings", "e": true}, {"n": "Question-and-Answer Session", "e": true}, {"n": "Public Relations Strategies", "e": true}, {"n": "Manage Projects Successfully", "e": true}], "5": [{"n": "Manage Successful Events", "e": false}, {"n": "Lessons Learned", "e": true}, {"n": "Moderate a Panel Discussion", "e": true}, {"n": "Ethical Leadership", "e": true}, {"n": "Leading in Your Volunteer Organization", "e": true}, {"n": "Prepare to Speak Professionally", "e": true}, {"n": "High Performance Leadership", "e": true}, {"n": "Reflect on Your Path", "e": false}]}, "SR": {"1": [{"n": "Ice Breaker", "e": false}, {"n": "Writing a Speech with Purpose", "e": false}, {"n": "Introduction to Vocal Variety and Body Language", "e": false}, {"n": "Evaluation and Feedback", "e": false}], "2": [{"n": "Understanding Your Leadership Style", "e": false}, {"n": "Cross-Cultural Understanding", "e": false}, {"n": "Introduction to Toastmasters Mentoring", "e": false}], "3": [{"n": "Make Connections Through Networking", "e": false}, {"n": "Deliver Social Speeches", "e": true}, {"n": "Using Presentation Software", "e": true}, {"n": "Connect with Storytelling", "e": true}, {"n": "Creating Effective Visual Aids", "e": true}, {"n": "Using Descriptive Language", "e": true}, {"n": "Connect with Your Audience", "e": true}, {"n": "Focus on the Positive", "e": true}, {"n": "Inspire Your Audience", "e": true}, {"n": "Prepare for an Interview", "e": true}, {"n": "Understanding Vocal Variety", "e": true}, {"n": "Effective Body Language", "e": true}, {"n": "Active Listening", "e": true}], "4": [{"n": "Public Relations Strategies", "e": false}, {"n": "Create a Podcast", "e": true}, {"n": "Building a Social Media Presence", "e": true}, {"n": "Managing a Difficult Audience", "e": true}, {"n": "Write a Compelling Blog", "e": true}, {"n": "Manage Online Meetings", "e": true}, {"n": "Question-and-Answer Session", "e": true}, {"n": "Manage Projects Successfully", "e": true}], "5": [{"n": "Leading in Your Volunteer Organization", "e": false}, {"n": "Lessons Learned", "e": true}, {"n": "Moderate a Panel Discussion", "e": true}, {"n": "Ethical Leadership", "e": true}, {"n": "Prepare to Speak Professionally", "e": true}, {"n": "High Performance Leadership", "e": true}, {"n": "Reflect on Your Path", "e": false}]}, "TC": {"1": [{"n": "Ice Breaker", "e": false}, {"n": "Writing a Speech with Purpose", "e": false}, {"n": "Introduction to Vocal Variety and Body Language", "e": false}, {"n": "Evaluation and Feedback", "e": false}], "2": [{"n": "Understanding Your Leadership Style", "e": false}, {"n": "Active Listening", "e": false}, {"n": "Introduction to Toastmasters Mentoring", "e": false}], "3": [{"n": "Successful Collaboration", "e": false}, {"n": "Deliver Social Speeches", "e": true}, {"n": "Using Presentation Software", "e": true}, {"n": "Connect with Storytelling", "e": true}, {"n": "Creating Effective Visual Aids", "e": true}, {"n": "Using Descriptive Language", "e": true}, {"n": "Connect with Your Audience", "e": true}, {"n": "Make Connections Through Networking", "e": true}, {"n": "Focus on the Positive", "e": true}, {"n": "Inspire Your Audience", "e": true}, {"n": "Prepare for an Interview", "e": true}, {"n": "Understanding Vocal Variety", "e": true}, {"n": "Effective Body Language", "e": true}], "4": [{"n": "Motivate Others", "e": false}, {"n": "Create a Podcast", "e": true}, {"n": "Building a Social Media Presence", "e": true}, {"n": "Managing a Difficult Audience", "e": true}, {"n": "Write a Compelling Blog", "e": true}, {"n": "Manage Online Meetings", "e": true}, {"n": "Question-and-Answer Session", "e": true}, {"n": "Public Relations Strategies", "e": true}, {"n": "Manage Projects Successfully", "e": true}], "5": [{"n": "Lead in Any Situation", "e": false}, {"n": "Lessons Learned", "e": true}, {"n": "Moderate a Panel Discussion", "e": true}, {"n": "Ethical Leadership", "e": true}, {"n": "Prepare to Speak Professionally", "e": true}, {"n": "High Performance Leadership", "e": true}, {"n": "Reflect on Your Path", "e": false}]}}, "projects": {"Ice Breaker": {"min": 4, "max": 6}, "Writing a Speech with Purpose": {"min": 5, "max": 7}, "Introduction to Vocal Variety and Body Language": {"min": 5, "max": 7}, "Understanding Your Communication Style": {"min": 5, "max": 7}, "Understanding Your Leadership Style": {"min": 5, "max": 7}, "Managing Time": {"min": 5, "max": 7}, "Introduction to Toastmasters Mentoring": {"min": 5, "max": 7}, "Know Your Sense of Humor": {"min": 5, "max": 7}, "Connect with Your Audience": {"min": 5, "max": 7}, "Cross-Cultural Understanding": {"min": 5, "max": 7}, "Negotiate the Best Outcome": {"min": 5, "max": 7}, "Engage Your Audience with Humor": {"min": 5, "max": 7}, "Present a Proposal": {"min": 5, "max": 7}, "Understanding Emotional Intelligence": {"min": 5, "max": 7}, "Understanding Conflict Resolution": {"min": 5, "max": 7}, "Persuasive Speaking": {"min": 5, "max": 7}, "Successful Collaboration": {"min": 5, "max": 7}, "Develop a Communication Plan": {"min": 5, "max": 7}, "Make Connections Through Networking": {"min": 5, "max": 7}, "Connect with Storytelling": {"min": 5, "max": 7}, "Creating Effective Visual Aids": {"min": 5, "max": 7}, "Inspire Your Audience": {"min": 5, "max": 7}, "Understanding Vocal Variety": {"min": 5, "max": 7}, "Using Descriptive Language": {"min": 5, "max": 7}, "Using Presentation Software": {"min": 5, "max": 7}, "Researching and Presenting": {"min": 5, "max": 7}, "Effective Body Language": {"min": 5, "max": 7}, "Manage Change": {"min": 5, "max": 7}, "Improvement Through Positive Coaching": {"min": 5, "max": 7}, "Leading Your Team": {"min": 5, "max": 7}, "Leading in Difficult Situations": {"min": 5, "max": 7}, "Communicate Change": {"min": 5, "max": 7}, "Motivate Others": {"min": 5, "max": 7}, "Public Relations Strategies": {"min": 5, "max": 7}, "Managing a Difficult Audience": {"min": 5, "max": 7}, "Building a Social Media Presence": {"min": 5, "max": 7}, "Manage Successful Events": {"min": 5, "max": 7}, "Leading in Your Volunteer Organization": {"min": 5, "max": 7}, "Lessons Learned": {"min": 5, "max": 7}, "Mentoring": {"min": 5, "max": 7}, "Advanced Mentoring": {"min": 5, "max": 7}, "Develop Your Vision": {"min": 5, "max": 7}, "Evaluation and Feedback": {"min": 5, "max": 7, "note": "Two 5–7 min speeches: 1st speech, then 2nd speech incorporating the feedback"}, "Deliver Social Speeches": {"min": 3, "max": 4, "note": "Two 3–4 min social speeches at separate meetings"}, "The Power of Humor in an Impromptu Speech": {"min": 2, "max": 3, "note": "Impromptu speaking — 2–3 min responses"}, "Write a Compelling Blog": {"min": 2, "max": 3, "note": "2–3 min speech about your blog"}, "Create a Podcast": {"min": 2, "max": 3, "note": "2–3 min introduction, then a 5–10 min podcast segment"}, "Question-and-Answer Session": {"min": 5, "max": 7, "note": "5–7 min speech + Q&A; 15–20 min total"}, "Focus on the Positive": {"min": 5, "max": 7, "alt": {"min": 2, "max": 3, "label": "2–3 min report option"}}, "Planning and Implementing": {"min": 5, "max": 7, "alt": {"min": 2, "max": 3, "label": "2–3 min report option"}}, "Team Building": {"min": 5, "max": 7, "alt": {"min": 2, "max": 3, "label": "2–3 min report option"}}, "Manage Projects Successfully": {"min": 5, "max": 7, "alt": {"min": 2, "max": 3, "label": "2–3 min report option"}}, "Reaching Consensus": {"min": 5, "max": 7, "alt": {"min": 2, "max": 3, "label": "2–3 min closing statement"}}, "High Performance Leadership": {"min": 5, "max": 7, "alt": {"min": 8, "max": 10, "label": "8–10 min review speech"}}, "Lead in Any Situation": {"min": 8, "max": 10}, "Deliver Your Message with Humor": {"min": 18, "max": 22, "note": "Keynote-style humorous speech"}, "Prepare to Speak Professionally": {"min": 18, "max": 22, "note": "Keynote-style speech"}, "Reflect on Your Path": {"min": 10, "max": 12}, "Ethical Leadership": {"min": 20, "max": 40, "note": "Moderated panel discussion — not a standard speech slot"}, "Moderate a Panel Discussion": {"min": 20, "max": 40, "note": "Panel discussion — not a standard speech slot"}, "Manage Online Meetings": {"min": 20, "max": 25, "note": "Online meeting/webinar — not a standard speech slot"}, "Prepare for an Interview": {"min": 5, "max": 7, "note": "Role-play interview at a club meeting"}, "Active Listening": {"min": null, "max": null, "note": "No speech — serve as Topicsmaster at a club meeting"}, "Prepare to Mentor": {"min": null, "max": null, "note": "No speech associated with this project"}}};
