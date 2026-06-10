from pathlib import Path
import pandas as pd

HOME = Path.home()

roots = [
    Path("/home/fredcui/Projects/BIGS-main/data/arctic_data"),
    Path("/home/fredcui/datasets/hoi/arctic/raw"),
    Path("/home/fredcui/Projects/arctic/data"),
    Path("/home/fredcui/Projects/arctic/unpack/arctic_data/data"),
    Path("/home/fredcui/Projects/arctic/unpack/arctic_data"),
]

required_dirs = [
    "raw_seqs",
    "processed_seqs",
    "splits",
    "splits_json",
    "meta",
    "object_vtemplates",
]

print("===== ARCTIC GT directory readiness =====")

found = {k: [] for k in required_dirs}

for root in roots:
    if not root.exists():
        continue
    for p in root.rglob("*"):
        if p.is_dir() and p.name in required_dirs:
            n_files = sum(1 for x in p.rglob("*") if x.is_file())
            found[p.name].append((p, n_files))

for k in required_dirs:
    print(f"\n{k}:")
    if not found[k]:
        print("  [MISS]")
    else:
        for p, n in found[k]:
            status = "OK" if n > 0 else "EMPTY"
            print(f"  [{status}] files={n} path={p}")

print("\n===== ARCTIC case mapping readiness =====")
map_p = HOME / "foho_phase0/inspection/arctic_phase017/arctic_phase017_case_to_split_mapping.csv"
if map_p.exists():
    df = pd.read_csv(map_p)
    print(df[["case", "image_path", "num_split_candidates"]].to_string(index=False))
    print("\nall_mapped:", bool((df["num_split_candidates"] > 0).all()))
else:
    print("[MISS]", map_p)

print("\n===== conclusion =====")
gt_ready = all(any(n > 0 for _, n in found[k]) for k in ["meta", "splits"])
print("gt_ready_minimal:", gt_ready)
print("paper_eval_ready:", False)
print("reason: still need official case provenance + GT overlay validation")
