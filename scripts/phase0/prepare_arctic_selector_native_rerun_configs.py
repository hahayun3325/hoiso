from pathlib import Path
import shutil

ROOT = Path("/home/fredcui/Projects/FollowMyHold")
HOME = Path.home()

BASE_RUNS = [
    "arctic_abox01_gpt55_auto",
    "arctic_aket01_gpt55_auto",
    "arctic_ascis01_gpt55_auto",
    "arctic_alapuse01_gpt55_auto",
    "arctic_amicuse01_gpt55_auto",
]

SUFFIX = "selector_native_v2"

def set_env(text, key, value):
    value = str(value)
    lines = text.splitlines()
    out = []
    found = False
    for line in lines:
        if line.startswith(key + "=") or line.startswith("export " + key + "="):
            out.append(f'{key}="{value}"')
            found = True
        else:
            out.append(line)
    if not found:
        out.append(f'{key}="{value}"')
    return "\n".join(out) + "\n"

for base in BASE_RUNS:
    new = f"{base}_{SUFFIX}"

    base_cfg = ROOT / f"configs/generated/pipeline.phase0.{base}.env"
    new_cfg = ROOT / f"configs/generated/pipeline.phase0.{new}.env"

    if not base_cfg.exists():
        raise FileNotFoundError(base_cfg)

    text = base_cfg.read_text()

    run_dir = HOME / "foho_phase0/runs" / new
    export_dir = run_dir / "internal_selector_exports"

    text = set_env(text, "RUN_ID", new)
    text = set_env(text, "BASE_DIR", run_dir)
    text = set_env(text, "FOHO_RUN_DIR", run_dir)
    text = set_env(text, "GUIDANCE_OUT_PATH", run_dir / "guidance_out")
    text = set_env(text, "FOHO_ENABLE_INTERNAL_PHASE42_SELECTOR", "1")
    text = set_env(text, "FOHO_INTERNAL_PHASE42_SELECTOR_CHOICE", "auto_fragmentation")
    text = set_env(text, "FOHO_INTERNAL_SELECTOR_EXPORT_DIR", export_dir)
    text = set_env(text, "FOHO_SELECTOR_DEBUG_DIR", export_dir)

    old_prompt = HOME / "foho_phase0/runs" / base / "manual_gemini_responses.csv"
    new_prompt = run_dir / "manual_gemini_responses.csv"
    run_dir.mkdir(parents=True, exist_ok=True)

    if old_prompt.exists():
        shutil.copy2(old_prompt, new_prompt)
        text = set_env(text, "GEMINI_RESPONSES", new_prompt)
    else:
        print(f"[WARN] prompt csv missing for {base}: {old_prompt}")

    new_cfg.write_text(text)
    print("[OK]", new)
    print("  config:", new_cfg)
    print("  run_dir:", run_dir)
    print("  export_dir:", export_dir)
