from pathlib import Path
import json

CASE_ROOT = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse01")
RUN_ROOT = Path("/home/fredcui/foho_phase0/runs_prompt_refined_v2/arctic_alapuse01_partaware_v2/attempt0_partaware_prompt/run_outputs/arctic_alapuse01_partaware_v2_attempt0")

ACTIVE_PARTS = CASE_ROOT / "integrated_gates/gate_a_part_repair/active_clean_parts"
OUT_DIR = CASE_ROOT / "integrated_gates/gate_d0_image_evidence_fit/metrics"
OUT_DIR.mkdir(parents=True, exist_ok=True)

paths = {
    "screen_part": ACTIVE_PARTS / "screen.ply",
    "keyboard_base_part": ACTIVE_PARTS / "keyboard_base.ply",
    "hinge_part": ACTIVE_PARTS / "hinge.ply",

    "cropped_obj_mask": RUN_ROOT / "cropped_hand_masks/alapuse01_cropped_obj_mask.png",
    "cropped_hand_mask": RUN_ROOT / "cropped_hand_masks/alapuse01_cropped_hand_mask.png",
    "cropped_hoi_img": RUN_ROOT / "cropped_hoi_imgs/alapuse01_cropped_hoi_1.png",
    "cropped_hoi_wo_bckg": RUN_ROOT / "cropped_hoi_imgs_wo_bckg/alapuse01_cropped_hoi_wo_bckg_1.png",
    "inpainted_object_img": RUN_ROOT / "ours_inpaint/alapuse01_inpainted_object.png",

    "aligned_mano": RUN_ROOT / "aligned_mano/alapuse01_hamer_aligned_mano.ply",
    "hamer_kps": RUN_ROOT / "hamer_out/alapuse01_kps_for_guidance.npy",
    "h2m_transform": RUN_ROOT / "h2m_transformations/alapuse01_hoi_mesh.npy",

    "guidance_obj": RUN_ROOT / "guidance_out/alapuse01_obj.ply",
    "guidance_hand": RUN_ROOT / "guidance_out/alapuse01_hand.ply",
    "hunyuan_hoi_mesh": RUN_ROOT / "hunyuan_hoi_out/alapuse01_hoi_mesh.ply",
}

# Try to discover MoGe assets if they exist nearby.
moge_candidates = list(RUN_ROOT.rglob("*moge*")) + list(RUN_ROOT.rglob("mesh.glb")) + list(RUN_ROOT.rglob("fov.json"))

manifest = {
    "case_id": "alapuse01",
    "stage": "standalone_fast_articulated_fitter_inputs",
    "case_root": str(CASE_ROOT),
    "run_root": str(RUN_ROOT),
    "paths": {},
    "moge_candidates": [str(p) for p in moge_candidates[:50]],
}

missing = []
for k, p in paths.items():
    manifest["paths"][k] = {
        "path": str(p),
        "exists": p.exists(),
    }
    if not p.exists():
        missing.append(k)

manifest["missing_required_or_expected"] = missing
manifest["ready_for_fitter_v0"] = all(
    manifest["paths"][k]["exists"]
    for k in ["screen_part", "keyboard_base_part", "hinge_part", "cropped_obj_mask", "cropped_hoi_img"]
)

out = OUT_DIR / "standalone_fitter_input_manifest.json"
out.write_text(json.dumps(manifest, indent=2))

print("[OK] wrote", out)
print("[ready_for_fitter_v0]", manifest["ready_for_fitter_v0"])
print("[missing]", missing)
print("[moge_candidates]", len(moge_candidates))
for k, v in manifest["paths"].items():
    print(f"{k:24s}", "OK" if v["exists"] else "MISSING", v["path"])
