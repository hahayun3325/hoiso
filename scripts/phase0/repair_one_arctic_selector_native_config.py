from pathlib import Path
import shutil

ROOT = Path("/home/fredcui/Projects/FollowMyHold")
HOME = Path.home()

base_id = "arctic_abox01_gpt55_auto"
new_id = "arctic_abox01_gpt55_auto_selector_native_v2"

base_cfg = ROOT / f"configs/generated/pipeline.phase0.{base_id}.env"
new_cfg = ROOT / f"configs/generated/pipeline.phase0.{new_id}.env"

if not base_cfg.exists():
    raise FileNotFoundError(base_cfg)

text = base_cfg.read_text()

base_run = HOME / "foho_phase0/runs" / base_id
new_run = HOME / "foho_phase0/runs" / new_id
export_dir = new_run / "internal_selector_exports"

# Replace every old run-directory path with the new run-directory path.
text = text.replace(str(base_run), str(new_run))

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

text = set_env(text, "RUN_ID", new_id)
text = set_env(text, "BASE_DIR", new_run)
text = set_env(text, "FOHO_RUN_DIR", new_run)
text = set_env(text, "GUIDANCE_OUT_PATH", new_run / "guidance_out")
text = set_env(text, "FOHO_ENABLE_INTERNAL_PHASE42_SELECTOR", "1")
text = set_env(text, "FOHO_INTERNAL_PHASE42_SELECTOR_CHOICE", "auto_fragmentation")
text = set_env(text, "FOHO_INTERNAL_SELECTOR_EXPORT_DIR", export_dir)
text = set_env(text, "FOHO_SELECTOR_DEBUG_DIR", export_dir)

# Copy prompt csv into the new run dir.
new_run.mkdir(parents=True, exist_ok=True)
old_prompt = base_run / "manual_gemini_responses.csv"
new_prompt = new_run / "manual_gemini_responses.csv"
if old_prompt.exists():
    shutil.copy2(old_prompt, new_prompt)
    text = set_env(text, "GEMINI_RESPONSES", new_prompt)
else:
    print("[WARN] old prompt csv missing:", old_prompt)

new_cfg.write_text(text)
print("[OK] wrote", new_cfg)
print("[OK] new run dir", new_run)
print("[OK] export dir", export_dir)
