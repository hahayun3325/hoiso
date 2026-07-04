from pathlib import Path
import json
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--case", required=True)
parser.add_argument("--data", default="/home/fredcui/foho_phase0")
parser.add_argument("--repo", default="/home/fredcui/Projects/FollowMyHold")
args = parser.parse_args()

case = args.case
data = Path(args.data)
case_root = data / "phase2_gateA_part_recon" / "cases" / case
out_root = case_root / "integrated_gates" / "case_preflight_after_alapuse01"
(out_root / "metrics").mkdir(parents=True, exist_ok=True)

patterns = {
    "case_root": [case_root],
    "active_clean_parts": list(case_root.rglob("active_clean_parts")) if case_root.exists() else [],
    "part_meshes": list(case_root.rglob("*.ply")) if case_root.exists() else [],
    "visual_scenes": list(case_root.rglob("*.glb")) if case_root.exists() else [],
    "selector_runs": list((data / "phase1_diagnostics").rglob(f"*{case}*")) if (data / "phase1_diagnostics").exists() else [],
    "repo_scripts": list(Path(args.repo).glob("scripts/phase2/*.py"))
}

summary = {}
for k, vals in patterns.items():
    paths = [str(v) for v in vals]
    summary[k] = {
        "count": len(paths),
        "examples": paths[:30]
    }

# Common expected files.
expected = {
    "case_root_exists": case_root.exists(),
    "active_clean_parts_exists": any(p.name == "active_clean_parts" for p in patterns["active_clean_parts"]),
    "has_ply": len(patterns["part_meshes"]) > 0,
    "has_glb": len(patterns["visual_scenes"]) > 0,
    "has_selector_related": len(patterns["selector_runs"]) > 0
}

decision = "MANUAL_REVIEW_REQUIRED"
if not expected["case_root_exists"]:
    decision = "FAIL_NO_CASE_ROOT"
elif not expected["has_ply"]:
    decision = "FAIL_NO_PART_OR_MESH_PLY"
elif not expected["has_selector_related"]:
    decision = "PARTIAL_NO_SELECTOR_RUN_FOUND"
else:
    decision = "ASSET_PREFLIGHT_PASS_VISUAL_REVIEW_REQUIRED"

report = {
    "case_id": case,
    "stage": "case preflight after alapuse01",
    "expected": expected,
    "summary": summary,
    "decision": decision,
    "next_step": "open candidate scenes and decide whether to run integrated gates"
}

out = out_root / "metrics" / f"{case}_preflight_asset_audit.json"
out.write_text(json.dumps(report, indent=2))

print("[OK] wrote", out)
print("[decision]", decision)
print(json.dumps(expected, indent=2))
print("\nUseful examples:")
for k, v in summary.items():
    print("\n==", k, "count=", v["count"])
    for e in v["examples"][:10]:
        print(e)
