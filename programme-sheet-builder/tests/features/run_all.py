"""Run every V30 feature suite sequentially and print one PASS/FAIL table.

Sequential on purpose: this box has 2 cores and other Playwright jobs share it.

    python3 tests/features/run_all.py
"""

import asyncio
import glob
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from harness import run_suite  # noqa: E402

SUITES = [
    ("test_1_education_series", "1_education_series"),
    ("test_2_custom_roles", "2_custom_roles"),
    ("test_3_save_dialog", "3_save_dialog"),
    ("test_4_exports", "4_exports"),
    ("test_5_layout", "5_layout"),
    ("test_6_invariants", "6_invariants"),
    ("test_7_print_density", "7_print_density"),
    ("test_8_v31_features", "8_v31_features"),
    ("test_9_print_layout_exports", "9_print_layout_exports"),
    ("test_10_v33_features", "10_v33_features"),
    # test_11_v34_markdown is NOT run: it covers the Markdown save/import that
    # V34 added and V35 deliberately removed. Kept on disk so the suite can be
    # restored with the feature if it ever comes back; running it against any
    # build from V35 on is a guaranteed red that trains people to skim.
    ("test_12_v36_features", "12_v36_features"),
    ("test_13_v43_contest", "13_v43_contest"),
]


async def main():
    for f in glob.glob(os.path.join(HERE, "_res_*.json")):
        os.unlink(f)
    all_results = []
    for mod_name, suite_name in SUITES:
        mod = importlib.import_module(mod_name)
        suite = await run_suite(mod.main, suite_name)
        all_results.append((suite_name, suite.results))

    width = max(len(c) for _, rs in all_results for c, _, _ in rs) + 2
    print("\n" + "=" * (width + 10))
    print("V30 FEATURE TEST RESULTS".center(width + 10))
    print("=" * (width + 10))
    tp = tf = 0
    fails = []
    for suite_name, rs in all_results:
        pas = sum(1 for _, ok, _ in rs if ok)
        print(f"\n--- {suite_name}  ({pas}/{len(rs)}) ---")
        for cid, ok, detail in rs:
            print(f"  {'PASS' if ok else 'FAIL'}  {cid}")
            if not ok:
                print(f"        -> {detail}")
                fails.append((suite_name, cid, detail))
        tp += pas
        tf += len(rs) - pas
    print("\n" + "=" * (width + 10))
    print(f"TOTAL: {tp} passed, {tf} failed, {tp + tf} checks")
    if fails:
        print("\nFAILURES:")
        for sn, cid, d in fails:
            print(f"  [{sn}] {cid}\n      {d}")
    return 1 if tf else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
