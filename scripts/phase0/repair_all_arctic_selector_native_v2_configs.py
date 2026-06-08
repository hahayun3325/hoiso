from pathlib import Path
import shutil

ROOT = Path("/home/fredcui/Projects/FollowMyHold")
HOME = Path.home()

BASE_RUNS = [
    "arctic_aket01_gpt55_auto",
    "arctic_ascis01_gpt55_auto",
    "arctic_alapuse01_gpt55_auto",
    "arctic_amicuse01_gpt55_auto",
]

def set_env(text, key, value):
    value = str(value)
    out = []
    found = False
    for line in text.splitlines():
        if line.startswith(key + "=") or line.startswith("export " + key + "="):
            out.append(f'{key}="{value}"')
            found = True
        else:
            out.append(line)
    if not found:
        out.append(f'{key}="{value}"')
    return "\n".join(out) + "\n"

for base_id in BASE_RUNS:
    new_id = base_id + "_selector_native_v2"

    base_cfg = ROOT / f"configs/generated/pipeline.phase0.{base_id}.env"
    new_cfg = ROOT / f"configs/generated/pipeline.phase0.{new_id}.env"

    if not base_cfg.exists():
        raise FileNotFoundError(base_cfg)

    base_run = HOME / "foho_phase0/runs" / base_id
    new_run = HOME / "foho_phase0/runs" / new_id
    export_dir = new_run / "internal_selector_exports"

    text = base_cfg.read_text()
    text = text.replace(str(base_run), str(new_run))

    text = set_env(text, "RUN_ID", new_id)
    text = set_env(text, "BASE_DIR", new_run)
    text = set_env(text, "FOHO_RUN_DIR", new_run)
    text = set_env(text, "OUTPUT_DIR", new_run)

    output_dirs = {
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

    for key, subdir in output_dirs.items():
        text = set_env(text, key, new_run / subdir)

    text = set_env(text, "FOHO_ENABLE_INTERNAL_PHASE42_SELECTOR", "1")
    text = set_env(text, "FOHO_INTERNAL_PHASE42_SELECTOR_CHOICE", "auto_fragmentation")
    text = set_env(text, "FOHO_INTERNAL_SELECTOR_EXPORT_DIR", export_dir)
    text = set_env(text, "FOHO_SELECTOR_DEBUG_DIR", export_dir)

    new_run.mkdir(parents=True, exist_ok=True)

    old_prompt = new_run / "manual_gemini_responses.csv"
    if old_prompt.exists():
        text = set_env(text, "GEMINI_RESPONSES", old_prompt)
    else:
        base_prompt = base_run / "manual_gemini_responses.csv"
        new_prompt = new_run / "manual_gemini_responses.csv"
        if base_prompt.exists():
            shutil.copy2(base_prompt, new_prompt)
            text = set_env(text, "GEMINI_RESPONSES", new_prompt)

    new_cfg.write_text(text)

    print("[OK] repaired", new_cfg)
    print("     run_dir:", new_run)
