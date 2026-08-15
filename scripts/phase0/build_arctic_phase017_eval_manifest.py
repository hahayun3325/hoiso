from pathlib import Path
import csv
import re
import pandas as pd

HOME = Path.home()
ROOT = Path("/home/fredcui/Projects/FollowMyHold")

CASES = ["abox01", "aket01", "ascis01", "alapuse01", "amicuse01"]

def read_env(path):
    d = {}
    if not path.exists():
        return d
    for line in path.read_text(errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        d[k.strip().replace("export ", "")] = v.strip().strip('"')
    return d

def exists(path):
    return Path(path).exists() and Path(path).stat().st_size > 0

split_path = ROOT / "test_splits/arctic_test.csv"
split_df = pd.read_csv(split_path) if split_path.exists() else pd.DataFrame()

rows = []

for case in CASES:
    method_run = f"arctic_{case}_gpt55_auto_selector_native_v2"
    method_cfg = ROOT / f"configs/generated/pipeline.phase0.{method_run}.env"
    env = read_env(method_cfg)

    image_path = env.get("IMAGE_PATH", "")
    method_run_dir = HOME / "foho_phase0/runs" / method_run

    # Candidate baseline names. We do not know yet which exists.
    baseline_candidates = [
        f"arctic_{case}_default",
        f"arctic_{case}_baseline",
        f"arctic_{case}_followmyhold_default",
        f"arctic_{case}_gpt55_auto",  # old non-selector, not true default but useful to inspect
    ]

    baseline_existing = []
    for b in baseline_candidates:
        bdir = HOME / "foho_phase0/runs" / b
        if bdir.exists():
            baseline_existing.append(b)

    split_matches = []
    if not split_df.empty and image_path:
        image_name = Path(image_path).name
        for _, r in split_df.iterrows():
            if image_name in str(r.get("img_path", "")) or case in str(r.get("img_path", "")):
                split_matches.append(dict(r))

    row = {
        "case": case,
        "method_run": method_run,
        "method_cfg": str(method_cfg),
        "image_path": image_path,
        "method_obj_exists": exists(method_run_dir / "guidance_out" / f"{case}_obj.ply"),
        "method_hand_exists": exists(method_run_dir / "guidance_out" / f"{case}_hand.ply"),
        "baseline_existing": ";".join(baseline_existing),
        "split_match_count": len(split_matches),
    }

    if split_matches:
        first = split_matches[0]
        for k in ["img_id", "img_path", "sid_seq_name", "frame"]:
            if k in first:
                row[f"split_{k}"] = first[k]

    rows.append(row)

out = HOME / "foho_phase0/inspection/arctic_phase017/arctic_phase017_eval_manifest.csv"
out.parent.mkdir(parents=True, exist_ok=True)

fields = sorted(set().union(*[r.keys() for r in rows]))
with open(out, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)

print("[OK] wrote", out)
for r in rows:
    print(r)
