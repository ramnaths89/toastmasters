"""Build a realistic saved meeting in each older build and dump its own
meetingPayload() to fixtures/, so V35 can be asked to load it."""
from harness import App, head
import json, pathlib

HERE = pathlib.Path(__file__).resolve().parent
FIX = HERE / "fixtures"
FIX.mkdir(exist_ok=True)
ROOT = HERE.parent.parent

FILL = """()=>{
  const m = state.meeting;
  m.title = 'Voices of a Nation';
  m.dateDisplay = 'Thursday, 13 August 2026';
  m.startTime = '19:00'; m.endTime = '21:30';
  m.location = 'Culinary Studio';
  m.fileName = 'NSE-Legacy-Fixture';
  if(m.voting){ m.voting.link='https://slido.example';
    m.voting.codes = {speechvote:'SPX1', ttvote:'TTX2', evalvote:'EVX3'}; }
  Object.keys(state.roles).forEach((k,i)=>{ state.roles[k] = 'Role_' + k; });
  state.roleActive.langeval = true;
  state.roleActive.photographer = false;
  if(Array.isArray(state.customRoles)){
    state.customRoles = [{key:'cr1', label:'Zoom Master'}, {key:'cr2', label:'Grammarian Plus'}];
  }
  state.announcementsText = 'Club AGM next month\\nBring a guest';
  state.execText = 'President|Alex Tan\\nVP Education|Jordan Lee';
  state.districtText = 'Area Director|Pat Chen|<Their Club>';
  state.linksText = 'Our Club|https://example.org|example.org';
  state.theme = 'classic';
  state.paneWidth = 44;
  /* let the build insert/remove the role-driven rows itself, so the fixture is
     self-consistent and V35 has nothing to sync on load */
  syncLanguageEvaluatorSegment(); syncRoleSegments();
  let n = 0;
  state.segments.forEach(sg=>{
    n++;
    if(sg.isSpeech){
      sg.speakerName = 'Speaker ' + n;
      sg.speechTitle = 'Title ' + n;
      sg.pathway = 'Dynamic Leadership'; sg.pLevel = '2'; sg.project = 'Understanding Your Leadership Style';
      sg.durMin = 7; sg.flexMin = 5; sg.flexMax = 7;
      sg.signalMin = 5; sg.signalMid = 6; sg.signalMax = 7; sg.signalSpan = 2;
      sg.signalsManual = true;
    }
    if(sg.isEvaluation){ sg.speakerName = 'Evaluator ' + n; sg.durMin = 3;
      sg.signalMin = 2; sg.signalMid = 2.5; sg.signalMax = 3; }
    if(sg.presetKey === 'tabletopics'){ sg.durMin = 25; sg.holderOverride = 'TT Master X'; }
    sg.sub = (sg.sub || '') + ' [fixture]';
  });
  return {segments: state.segments.length,
          keys: Object.keys(state).sort(),
          meetingKeys: Object.keys(state.meeting).sort(),
          segKeys: Object.keys(state.segments[0]).sort()};
}"""

head("T05 — generating legacy fixtures")
summary = {}
for v in ["V30", "V31", "V32", "V33", "V34", "V35"]:
    build = ROOT / ("ProgSheetGen%s.html" % v)
    with App(build=build) as a:
        info = a.js(FILL)
        payload = a.js("()=>meetingPayload()")
        (FIX / (v.lower() + ".nse.json")).write_text(payload)
        summary[v] = info
        print("  %s: %d segments, %d state keys, payload %d bytes"
              % (v, info["segments"], len(info["keys"]), len(payload)))

# a synthetic pre-V30 file: no customRoles, no clubInitials, no orgLine/cadence
base = json.loads((FIX / "v30.nse.json").read_text())
for k in ("customRoles",):
    base["state"].pop(k, None)
for k in ("clubInitials", "orgLine", "cadence", "fileName"):
    base["state"]["meeting"].pop(k, None)
base["v"] = 28
(FIX / "v29.nse.json").write_text(json.dumps(base, indent=2))
print("  V29 (synthetic, pre-customRoles) written")

(FIX / "_keys.json").write_text(json.dumps(summary, indent=2))
print("\n  state keys per build:")
for v, i in summary.items():
    print("   ", v, i["keys"])
print("\n  meeting keys per build:")
for v, i in summary.items():
    print("   ", v, i["meetingKeys"])
print("\n  segment keys per build:")
for v, i in summary.items():
    print("   ", v, i["segKeys"])
