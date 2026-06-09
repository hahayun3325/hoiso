from pathlib import Path

CASES = ["abox01", "aket01", "ascis01", "alapuse01", "amicuse01"]
ROOT = Path("/home/fredcui/Projects/FollowMyHold")
HOME = Path.home()

def set_env(text, key, value):
    line = f'{key}="{value}"'
    lines = text.splitlines()
    out = []
    found = False
    for x in lines:
        if x.startswith(f"{key}=") or x.startswith(f"# {key}="):
            out.append(line)
            found = True
        else:
            out.append(x)
    if not found:
        out.append(line)
    return "\n".join(out) + "\n"

for case in CASES:
    run_id = f"arctic_{case}_default"
    cfg = ROOT / f"configs/generated/pipeline.phase0.{run_id}.env"
    if not cfg.exists():
        print("[MISS]", cfg)
        continue

    run = HOME / "foho_phase0/runs" / run_id
    text = cfg.read_text()

    replacements = {
        "BASE_DIR": str(run),
        "ORIGINAL_IMG_DIR": str(run / "original_imgs"),
        "MASKED_OBJ_PATH": str(run / "masked_obj_imgs"),
        "CROPPED_HOI_PATH": str(run / "cropped_hoi_imgs"),
        "CROPPED_HOI_WO_BCKG_PATH": str(run / "cropped_hoi_imgs_wo_bckg"),
        "CROPPED_INPAINTED_OBJ": str(run / "ours_inpaint"),
        "MASK_DIR_PATH": str(run / "cropped_hand_masks"),
        "MOGE_OUT_PATH": str(run / "moge_out"),
        "HUNYUAN_HOI_MESH_PATH": str(run / "hunyuan_hoi_out"),
        "HAMER_OUT_PATH": str(run / "hamer_out"),
        "H2M_RT_PATH": str(run / "h2m_transformations"),
        "ALIGNED_MANO_PATH": str(run / "aligned_mano"),
        "GUIDANCE_OUT_PATH": str(run / "guidance_out"),
        "FOHO_DEBUG_DIR": str(run / "foho_debug"),
        "GEMINI_RESPONSES": "",
        "FOHO_ENABLE_INTERNAL_PHASE42_SELECTOR": "0",
        "FOHO_INTERNAL_PHASE42_SELECTOR_CHOICE": "",
        "FOHO_INTERNAL_SELECTOR_EXPORT_DIR": "",
        "FOHO_SELECTOR_DEBUG_DIR": "",
        "RUN_ID": run_id,
        "FOHO_RUN_DIR": str(run),
        "OUTPUT_DIR": str(run),
    }

    for k, v in replacements.items():
        text = set_env(text, k, v)

    cfg.write_text(text)
    print("[OK] repaired", cfg)
