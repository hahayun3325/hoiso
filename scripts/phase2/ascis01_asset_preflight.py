from pathlib import Path
import json

DATA = Path("/home/fredcui/foho_phase0")
CASE = "ascis01"
CASE_ROOT = DATA / "phase2_gateA_part_recon/cases" / CASE
SEL_RUN = DATA / "phase1_diagnostics/selector_v41_full_pipeline/runs/arctic_ascis01_selector_v41_refined_pipeline"
OUT = CASE_ROOT / "integrated_gates/articulated_probe_ascis01/metrics"
OUT.mkdir(parents=True, exist_ok=True)

patterns = {
    "case_root": CASE_ROOT,
    "selector_run": SEL_RUN,
    "guidance_hand": SEL_RUN / "guidance_out/ascis01_hand.ply",
    "guidance_object": SEL_RUN / "guidance_out/ascis01_obj.ply",
    "aligned_mano": SEL_RUN / "aligned_mano/ascis01_hamer_aligned_mano.ply",
}

part_files = []
if CASE_ROOT.exists():
    for p in CASE_ROOT.rglob("*.ply"):
        name = p.name.lower()
        if any(k in name for k in ["part", "blade", "handle", "scissor", "body", "residual"]):
            part_files.append(p)

glb_files = list(CASE_ROOT.rglob("*.glb")) if CASE_ROOT.exists() else []
manifest_files = list(CASE_ROOT.rglob("*manifest*.json")) if CASE_ROOT.exists() else []

report = {
    "case": CASE,
    "exists": {k: v.exists() for k, v in patterns.items()},
    "paths": {k: str(v) for k, v in patterns.items()},
    "num_candidate_part_plys": len(part_files),
    "candidate_part_plys": [str(p) for p in sorted(part_files)[:100]],
    "num_glb_files": len(glb_files),
    "glb_files": [str(p) for p in sorted(glb_files)[:50]],
    "num_manifest_files": len(manifest_files),
    "manifest_files": [str(p) for p in sorted(manifest_files)[:50]],
}

if not patterns["guidance_hand"].exists() or not patterns["guidance_object"].exists():
    decision = "FAIL_MISSING_GUIDANCE_SHARED_FRAME"
elif len(part_files) == 0:
    decision = "FAIL_NO_PART_MESHES"
elif len(part_files) < 2:
    decision = "WEAK_ONLY_SINGLE_PART"
else:
    decision = "PASS_ASSET_PREFLIGHT_RUN_DRYRUN"

report["decision"] = decision

out = OUT / "ascis01_asset_preflight_report.json"
out.write_text(json.dumps(report, indent=2))

print(json.dumps(report, indent=2))
print("[OK] wrote", out)
