from pathlib import Path
import re
import shutil

ROOT = Path("/home/fredcui/Projects/FollowMyHold")
HOME = Path.home()

RUNS = [
    "arctic_abox01_gpt55_auto",
    "arctic_aket01_gpt55_auto",
    "arctic_ascis01_gpt55_auto",
    "arctic_alapuse01_gpt55_auto",
    "arctic_amicuse01_gpt55_auto",
]

OUT_KEYS = {
    "ORIGINAL_IMG_DIR": "original_imgs",
    "MASKED_OBJ_PATH": "masked_obj_imgs",
    "CROPPED_HOI_PATH": "cropped_hoi_imgs",
    "CROPPED_HOI_WO_BCKG_PATH": "cropped_hoi_imgs_wo_bckg",
    "CROPPED_INPAINTED_OBJ": "ours_inpaint",
    "MASK_DIR_PATH": "cropped_hand_masks",
    "MOGE_OUT_PATH": "moge_out",
    "HUNYUAN_HOI_MESH_PATH": "hunyuan_hoi_out",
    "HAMER_OUT_PATH": "hamer_out",
    "H2M_RT_PATH": "h2m_transformations",
    "ALIGNED_MANO_PATH": "aligned_mano",
    "GUIDANCE_OUT_PATH": "guidance_out",
    "FOHO_DEBUG_DIR": "foho_debug",
}

def quote(x):
    return '"' + str(x).replace('"', '\\"') + '"'

def set_line(text, key, value):
    new = f"{key}={quote(value)}"
    pat = re.compile(rf"^#?\s*{re.escape(key)}=.*$", re.M)
    if pat.search(text):
        return pat.sub(new, text)
    return text.rstrip() + "\n" + new + "\n"

for run_id in RUNS:
    cfg = ROOT / f"configs/generated/pipeline.phase0.{run_id}.env"
    if not cfg.exists():
        print("[MISSING CFG]", cfg)
        continue

    backup = cfg.with_suffix(cfg.suffix + ".before_arctic_path_repair")
    shutil.copy2(cfg, backup)

    run_dir = HOME / "foho_phase0/runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    text = cfg.read_text()

    text = set_line(text, "BASE_DIR", run_dir)

    for key, subdir in OUT_KEYS.items():
        text = set_line(text, key, run_dir / subdir)

    text = set_line(text, "GEMINI_RESPONSES", run_dir / "manual_gemini_responses.csv")
    text = set_line(text, "FOHO_ENABLE_INTERNAL_PHASE42_SELECTOR", "1")
    text = set_line(text, "FOHO_INTERNAL_PHASE42_SELECTOR_CHOICE", "auto_fragmentation")
    text = set_line(text, "FOHO_INTERNAL_SELECTOR_EXPORT_DIR", run_dir / "internal_selector_exports")

    cfg.write_text(text)

    print("[OK] repaired", cfg)
    print("     backup:", backup)
    print("     BASE_DIR:", run_dir)
