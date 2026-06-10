from pathlib import Path
import pandas as pd

HOME = Path.home()
ROOT = Path("/home/fredcui/Projects/FollowMyHold")
GT_ROOT = Path("/home/fredcui/Projects/arctic/unpack/arctic_data/data")

required = {
    "raw_seqs": GT_ROOT / "raw_seqs",
    "splits": GT_ROOT / "splits",
    "splits_json": GT_ROOT / "splits_json",
    "meta": GT_ROOT / "meta",
    "object_vtemplates": GT_ROOT / "meta/object_vtemplates",
}

optional = {
    "processed_seqs": GT_ROOT / "processed_seqs",
}

print("===== ARCTIC GT readiness v2 =====")
gt_ok = True

for name, p in required.items():
    n = sum(1 for x in p.rglob("*") if x.is_file()) if p.exists() else 0
    status = "OK" if n > 0 else "MISS"
    print(f"{name}: [{status}] files={n} path={p}")
    gt_ok = gt_ok and n > 0

for name, p in optional.items():
    n = sum(1 for x in p.rglob("*") if x.is_file()) if p.exists() else 0
    status = "OK" if n > 0 else "OPTIONAL_MISSING"
    print(f"{name}: [{status}] files={n} path={p}")

print("\n===== manual provenance readiness =====")
csv_path = ROOT / "docs/phase0/arctic_phase017_selected_cases.csv"
prov_ok = False
if csv_path.exists():
    df = pd.read_csv(csv_path)
    needed = {"case", "subject", "seq_name", "view_id", "frame", "source_path", "input_path"}
    prov_ok = needed.issubset(df.columns) and len(df) == 5
    print(df[["case", "subject", "seq_name", "view_id", "frame"]].to_string(index=False))
    print("provenance_ok:", prov_ok)
else:
    print("[MISS]", csv_path)

print("\n===== conclusion =====")
print("gt_ready_minimal:", gt_ok)
print("provenance_ready:", prov_ok)
print("ready_for_first_gt_overlay:", bool(gt_ok and prov_ok))
print("ready_for_final_metric_table:", False)
print("reason: still need to validate one GT overlay before reporting paper-like metrics")
