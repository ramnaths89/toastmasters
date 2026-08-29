"""V30 feature 2 - custom meeting roles (cr1, cr2, ...)."""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import open_app, open_sections, run_suite  # noqa: E402

ADD = "button.cr-add"


async def roster(p):
    """The role-player roster the TME reads out, from the PREVIEW IFRAME."""
    await p.evaluate("() => renderPreviewNow()")
    await p.wait_for_timeout(350)
    return await p.frame_locator("#previewFrame").locator(".role-roster").first.inner_text()


async def main(ctx, s):
    app = await open_app(ctx)
    p = app.page
    await open_sections(p)   # V31: sections load shut

    # ---------- 2.1 the button exists and adds a row ----------
    s.eq("2.1 custom roles start empty in the template",
         await p.evaluate("() => state.customRoles.length"), 0)
    s.check("2.2 '+ Add a role' button exists in Meeting Roles",
            await p.locator(ADD).count() == 1,
            f"count={await p.locator(ADD).count()}")
    s.eq("2.3 button label", (await p.locator(ADD).inner_text()).strip(), "+ Add a role")

    await p.locator(ADD).click()
    await p.wait_for_timeout(250)
    rows = p.locator("#customRoles .cr-row")
    s.eq("2.4 clicking it adds exactly one row", await rows.count(), 1)
    s.eq("2.5 first key is cr1", await p.evaluate("() => state.customRoles[0].key"), "cr1")

    r1 = rows.first
    s.eq("2.6 row has a title field", await r1.locator("input.cr-label").count(), 1)
    s.eq("2.7 row has a person field", await r1.locator("input#r-cr1").count(), 1)
    s.eq("2.8 row has a tick box", await r1.locator("input#rc-cr1").count(), 1)
    s.check("2.9 the new role is ticked on by default",
            await p.evaluate("() => state.roleActive.cr1") is True)
    s.eq("2.10 state.roles gets the key", await p.evaluate("() => state.roles.cr1"), "")

    # ---------- 2.11 typing a title + person prints it in the roster ----------
    await r1.locator("input.cr-label").fill("Zoom Master")
    await r1.locator("input#r-cr1").fill("Priya Menon")
    await p.wait_for_timeout(300)
    ros = await roster(p)
    s.check("2.11 custom role title appears in the printed roster", "Zoom Master" in ros, ros[:300])
    s.check("2.12 custom role person appears in the printed roster", "Priya Menon" in ros, ros[:300])

    # It must be under TME Welcome Remarks, and AFTER the built-in role players.
    welcome_row = await p.frame_locator("#previewFrame").locator(
        "tr:has(.role-roster)").first.inner_text()
    s.check("2.13 the roster sits on the TME Welcome Remarks row",
            "Welcome" in welcome_row, welcome_row[:160])
    s.check("2.14 custom role is listed after the built-in role players",
            ros.index("Zoom Master") > ros.index("Sergeant-at-Arms"),
            "custom role rendered before the built-ins")

    # ---------- 2.15 unnamed custom role => red TBD + still-open list ----------
    await p.locator(ADD).click()
    await p.wait_for_timeout(200)
    await p.locator("#customRoles .cr-row").nth(1).locator("input.cr-label").fill("Joke Master")
    await p.wait_for_timeout(300)
    s.eq("2.15 second key is cr2", await p.evaluate("() => state.customRoles[1].key"), "cr2")

    ros = await roster(p)
    s.check("2.16 an unnamed custom role still appears in the roster",
            "Joke Master" in ros, ros[:300])
    tbd_html = await p.frame_locator("#previewFrame").locator(".role-roster").first.inner_html()
    after = tbd_html.split("Joke Master", 1)[1][:200]
    s.check("2.17 unnamed custom role prints a red TBD chip",
            'class="tbd-inline"' in after and "TBD" in after, after[:150])
    # the TBD chip is styled red by the sheet CSS
    color = await p.frame_locator("#previewFrame").locator(".tbd-inline").first.evaluate(
        "el => getComputedStyle(el).color")
    s.check("2.18 the TBD chip renders red", color.startswith("rgb(") and
            int(color[4:-1].split(",")[0]) > 120 and
            int(color[4:-1].split(",")[0]) > int(color[4:-1].split(",")[1]) + 40, color)

    open_roles = await p.evaluate("() => openRoleLabels()")
    s.check("2.19 unnamed custom role is listed as still open",
            "Joke Master" in open_roles, str(open_roles))
    s.check("2.20 a named custom role is NOT listed as still open",
            "Zoom Master" not in open_roles, str(open_roles))
    sheet_text = await p.frame_locator("#previewFrame").locator("body").inner_text()
    s.check("2.21 the still-open notice on the sheet names it",
            "Joke Master" in sheet_text, "")

    # ---------- 2.22 unticking removes it from the roster ----------
    await p.locator("#rc-cr1").uncheck()
    await p.wait_for_timeout(400)
    ros = await roster(p)
    s.check("2.22 unticking a custom role drops it from the roster",
            "Zoom Master" not in ros, ros[:300])
    s.check("2.23 unticking keeps its person in state (not destroyed)",
            await p.evaluate("() => state.roles.cr1") == "Priya Menon")
    s.check("2.24 unticked custom role is not chased as 'still open'",
            "Zoom Master" not in await p.evaluate("() => openRoleLabels()"))
    s.check("2.25 unticking disables its person field",
            await p.locator("#r-cr1").is_disabled())
    s.check("2.26 unticking a custom role raises no page error",
            not app.clean_errors(), str(app.clean_errors()[:2]))

    await p.locator("#rc-cr1").check()
    await p.wait_for_timeout(400)
    ros = await roster(p)
    s.check("2.27 re-ticking brings it back with its person",
            "Zoom Master" in ros and "Priya Menon" in ros, ros[:300])

    # ---------- 2.28 removal is clean ----------
    p.on("dialog", lambda d: asyncio.ensure_future(d.accept()))
    await p.locator("#customRoles .cr-row").nth(1).locator("button.cr-del").click()
    await p.wait_for_timeout(400)
    st = await p.evaluate(
        "() => ({keys: state.customRoles.map(r=>r.key),"
        " roleKeys: Object.keys(state.roles), activeKeys: Object.keys(state.roleActive)})"
    )
    s.eq("2.28 removing deletes the entry from state.customRoles", st["keys"], ["cr1"])
    s.check("2.29 removal leaves no stray key in state.roles",
            "cr2" not in st["roleKeys"], str(st["roleKeys"]))
    s.check("2.30 removal leaves no stray key in state.roleActive",
            "cr2" not in st["activeKeys"], str(st["activeKeys"]))
    s.eq("2.31 removing one row leaves the other rendered",
         await p.locator("#customRoles .cr-row").count(), 1)
    ros = await roster(p)
    s.check("2.32 the removed role is gone from the roster", "Joke Master" not in ros, ros[:300])

    # ---------- 2.33 keys are never reused ----------
    # cr1 exists; add cr2, cr3, remove the MIDDLE one (cr2), add again -> must be cr4.
    await p.locator(ADD).click()
    await p.wait_for_timeout(150)
    await p.locator(ADD).click()
    await p.wait_for_timeout(150)
    keys = await p.evaluate("() => state.customRoles.map(r=>r.key)")
    s.eq("2.33 keys increment cr1, cr2, cr3", keys, ["cr1", "cr2", "cr3"])

    await p.locator("#customRoles .cr-row").nth(1).locator("button.cr-del").click()
    await p.wait_for_timeout(300)
    s.eq("2.34 removing the middle row leaves cr1, cr3",
         await p.evaluate("() => state.customRoles.map(r=>r.key)"), ["cr1", "cr3"])
    await p.locator(ADD).click()
    await p.wait_for_timeout(250)
    s.eq("2.35 the next added role is cr4, NOT a reused cr2",
         await p.evaluate("() => state.customRoles.map(r=>r.key)"), ["cr1", "cr3", "cr4"])

    # A segment pointing at a removed role must not be left holding a dead key.
    await p.evaluate("() => { state.segments[0].roleKey = 'cr4'; }")
    await p.locator("#customRoles .cr-row").nth(2).locator("button.cr-del").click()
    await p.wait_for_timeout(300)
    s.eq("2.36 removing a role clears segments that pointed at it",
         await p.evaluate("() => state.segments[0].roleKey"), "")

    # ---------- 2.37 round trip through meetingPayload / adoptState ----------
    await p.evaluate(
        """() => {
             state.customRoles = [];
             state.roles = Object.fromEntries(Object.entries(state.roles).filter(([k])=>!/^cr/.test(k)));
             addCustomRole(); addCustomRole();
             state.customRoles[0].label = 'Zoom Master';  state.roles[state.customRoles[0].key] = 'Priya Menon';
             state.customRoles[1].label = 'Grammarian';   state.roles[state.customRoles[1].key] = '';
             state.roleActive[state.customRoles[1].key] = false;
             renderCustomRoles(); renderPreviewNow();
           }"""
    )
    await p.wait_for_timeout(300)
    before = await p.evaluate(
        "() => ({cr: state.customRoles, roles: state.roles, active: state.roleActive})")
    payload = await p.evaluate("() => meetingPayload()")
    s.check("2.37 meetingPayload carries customRoles",
            "customRoles" in payload and "Zoom Master" in payload)

    ok = await p.evaluate(
        "t => { const r = adoptState(JSON.parse(t)); syncFormInputs(); renderFormPane();"
        " renderPreviewNow(); return r; }", payload)
    s.check("2.38 adoptState accepts the payload", ok is True)
    await p.wait_for_timeout(400)
    after_st = await p.evaluate(
        "() => ({cr: state.customRoles, roles: state.roles, active: state.roleActive})")
    s.eq("2.39 custom role list survives save-and-reload",
         after_st["cr"], before["cr"])
    s.eq("2.40 the people named in custom roles survive",
         [after_st["roles"].get(r["key"]) for r in after_st["cr"]],
         [before["roles"].get(r["key"]) for r in before["cr"]])
    s.eq("2.41 the tick state of custom roles survives",
         [after_st["active"].get(r["key"]) for r in after_st["cr"]],
         [before["active"].get(r["key"]) for r in before["cr"]])
    s.eq("2.42 the reloaded rows are re-rendered in the form",
         await p.locator("#customRoles .cr-row").count(), 2)
    s.eq("2.43 the reloaded person is back in its input",
         await p.locator("#customRoles .cr-row").first.locator("input[id^='r-cr']").input_value(),
         "Priya Menon")
    s.eq("2.44 the reloaded title is back in its input",
         await p.locator("#customRoles .cr-row").first.locator("input.cr-label").input_value(),
         "Zoom Master")
    ros = await roster(p)
    s.check("2.45 the reloaded custom role prints in the roster", "Zoom Master" in ros, ros[:300])
    s.check("2.46 an unticked reloaded custom role stays off the roster",
            "Grammarian" not in ros, ros[:300])

    # After a round trip the key counter must still not reuse a key.
    await p.locator(ADD).click()
    await p.wait_for_timeout(200)
    keys = await p.evaluate("() => state.customRoles.map(r=>r.key)")
    s.check("2.47 key allocation after a reload continues past the restored keys",
            len(set(keys)) == len(keys) and keys[-1] == "cr3", str(keys))

    # ---------- 2.48 a V29-era payload (no customRoles) still loads ----------
    v29_payload = await p.evaluate(
        """() => { const o = JSON.parse(meetingPayload());
                   delete o.state.customRoles;
                   Object.keys(o.state.roles).forEach(k=>{ if(/^cr/.test(k)) delete o.state.roles[k]; });
                   Object.keys(o.state.roleActive).forEach(k=>{ if(/^cr/.test(k)) delete o.state.roleActive[k]; });
                   return JSON.stringify(o); }"""
    )
    err = await p.evaluate(
        """t => { try { const r = adoptState(JSON.parse(t)); syncFormInputs();
                        renderFormPane(); renderPreviewNow();
                        return {ok:r, cr: state.customRoles, err:null}; }
                 catch(e){ return {ok:false, cr:null, err:String(e)}; } }""",
        v29_payload)
    s.check("2.48 a V29 payload with no customRoles key loads without error",
            err["ok"] is True and err["err"] is None, str(err["err"]))
    s.eq("2.49 a V29 payload yields an empty customRoles list", err["cr"], [])
    s.eq("2.50 no custom-role rows are rendered for a V29 payload",
         await p.locator("#customRoles .cr-row").count(), 0)

    # Malformed entries must be filtered, not rendered as undefined.
    bad = await p.evaluate(
        """() => { const o = JSON.parse(meetingPayload());
                   o.state.customRoles = [null, 5, {label:'no key'}, {key:'cr9'},
                                          {key:'cr10', label:null}, {key:7, label:'numeric key'}];
                   const r = adoptState(o); syncFormInputs(); renderCustomRoles();
                   return {ok:r, cr: state.customRoles}; }"""
    )
    s.check("2.51 malformed customRoles entries are filtered on load",
            bad["ok"] is True and
            [c["key"] for c in bad["cr"]] == ["cr9", "cr10", "7"] and
            all(isinstance(c["label"], str) for c in bad["cr"]),
            str(bad["cr"]))
    html = await p.locator("#customRoles").inner_html()
    s.check("2.52 no 'undefined' leaks into the rendered rows", "undefined" not in html,
            html[:200])

    # ---------- 2.53 no errors overall ----------
    s.check("2.53 zero uncaught page errors during feature 2", not app.clean_errors(),
            str(app.clean_errors()[:3]))
    s.check("2.54 zero console errors during feature 2", not app.clean_console(),
            str(app.clean_console()[:3]))


if __name__ == "__main__":
    asyncio.run(run_suite(main, "2_custom_roles"))
