from pathlib import Path
import json

DATA = Path("/home/fredcui/foho_phase0")
CASE = "alapuse02_v3"
TOKEN = "alapuse02v3"

case_root = DATA / "phase2_gateA_part_recon/cases" / CASE
run_root = DATA / "phase1_diagnostics/selector_v41_full_pipeline/runs/arctic_alapuse02_v3_selector_v41_refined_pipeline"

paths = {
    "run_root": run_root,
    "guidance_hand": run_root / "guidance_out" / f"{TOKEN}_hand.ply",
    "guidance_object": run_root / "guidance_out" / f"{TOKEN}_obj.ply",
    "aligned_mano": run_root / "aligned_mano" / f"{TOKEN}_hamer_aligned_mano.ply",
    "hunyuan_hoi_mesh": run_root / "hunyuan_hoi_out" / f"{TOKEN}_hoi_mesh.ply",
    "h2m_transform": run_root / "h2m_transformations" / f"{TOKEN}_hoi_mesh.npy",
    "moge_depth": run_root / "moge_out" / f"{TOKEN}_cropped_hoi" / "depth.exr",
    "moge_fov": run_root / "moge_out" / f"{TOKEN}_cropped_hoi" / "fov.json",
}

report = {
    "case": CASE,
    "token": TOKEN,
    "paths": {k: str(v) for k, v in paths.items()},
    "exists": {k: v.exists() for k, v in paths.items()},
    "sizes_bytes": {k: (v.stat().st_size if v.exists() and v.is_file() else None) for k, v in paths.items()},
}

required = ["guidance_hand", "guidance_object"]
if all(report["exists"][k] and (report["sizes_bytes"][k] or 0) > 0 for k in required):
    report["decision"] = "PASS_GUIDANCE_ASSETS_READY"
else:
    report["decision"] = "FAIL_MISSING_GUIDANCE_ASSETS"

out = case_root / "metrics" / "alapuse02_v3_precise_guidance_asset_check.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(report, indent=2))

print(json.dumps(report, indent=2))
print("[OK] wrote", out)
