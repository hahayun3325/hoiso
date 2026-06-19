#!/usr/bin/env python
from pathlib import Path
import json
import re

repo = Path("/home/fredcui/Projects/FollowMyHold")
home = Path("/home/fredcui")

patterns = [
    "arctic_aket01_gpt55_auto_selector_native_v2",
    "pipeline.phase0.arctic_aket01_gpt55_auto_selector_native_v2.env",
    "manual_gemini_responses.csv",
    "GEMINI_RESPONSES",
    "FOHO_RUN_DIR",
    "OUTPUT_DIR",
    "CROPPED_INPAINTED_OBJ",
    "HUNYUAN_HOI_MESH_PATH",
    "GUIDANCE_OUT_PATH",
]

roots = [
    repo / "scripts",
    repo / "configs",
    repo / "docs",
]

history_files = [
    home / ".bash_history",
    home / ".zsh_history",
]

hits = []

def scan_file(path):
    try:
        text = path.read_text(errors="ignore")
    except Exception:
        return
    lines = text.splitlines()
    for i, line in enumerate(lines, 1):
        for pat in patterns:
            if pat in line:
                hits.append({
                    "file": str(path),
                    "line": i,
                    "pattern": pat,
                    "text": line.strip(),
                })

for root in roots:
    if root.exists():
        for path in root.rglob("*"):
            if path.is_file() and path.suffix not in [".pyc", ".png", ".jpg", ".jpeg", ".ply", ".obj", ".glb"]:
                scan_file(path)

for path in history_files:
    if path.exists():
        scan_file(path)

out_dir = repo / "docs/phase1/step3_prompt_refined_rerun/aket01_attempt0"
out_dir.mkdir(parents=True, exist_ok=True)

json_path = out_dir / "aket01_launcher_discovery_hits.json"
json_path.write_text(json.dumps(hits, indent=2))

md_path = out_dir / "aket01_launcher_discovery_hits.md"
with md_path.open("w") as f:
    f.write("# aket01 launcher discovery hits\n\n")
    if not hits:
        f.write("No hits found.\n")
    for h in hits:
        f.write(f"- `{h['file']}:{h['line']}` [{h['pattern']}]\n")
        f.write(f"  ```text\n  {h['text']}\n  ```\n")

print("[OK] wrote", json_path)
print("[OK] wrote", md_path)
print("num_hits =", len(hits))
for h in hits[:80]:
    print(f"{h['file']}:{h['line']}: {h['text']}")
