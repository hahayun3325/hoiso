from pathlib import Path
import json

src = Path("/home/fredcui/Projects/FollowMyHold/docs/phase2/gate_a_part_recon/arctic5_manual_part_schema.jsonl")
out_dir = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/part_prompts")
out_dir.mkdir(parents=True, exist_ok=True)

if not src.exists():
    raise FileNotFoundError(f"Missing source JSONL: {src}")

count = 0
for line in src.read_text().splitlines():
    if not line.strip():
        continue
    d = json.loads(line)
    case_id = d["case_id"]
    out = out_dir / f"{case_id}_part_schema.json"
    out.write_text(json.dumps(d, indent=2))
    print("[OK]", out)
    count += 1

print("written_json_files =", count)
if count != 5:
    raise SystemExit(f"[BAD] expected 5 files, wrote {count}")
