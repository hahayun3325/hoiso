from pathlib import Path
import pandas as pd

DATA = Path("/home/fredcui/foho_phase0")
PHASE1_ASSETS = DATA / "phase1_report_assets"
OUT = DATA / "phase2_gateA_part_recon/gate_a_cases.csv"

cases = ["aket01", "ascis01", "alapuse01", "amicuse01", "abox01"]

rows = []
for case in cases:
    root = PHASE1_ASSETS / "meshes" / case / "selector_v41"
    rows.append({
        "case": case,
        "input_image": str(DATA / "inputs" / "arctic_phase017" / f"{case}.jpg"),
        "hand_mesh": str(root / "final_hand.ply"),
        "object_mesh": str(root / "final_object.ply"),
        "hoi_mesh": str(root / "final_hoi_colored.ply"),
        "source_method": "selector_v41_refined_pipeline",
    })

df = pd.DataFrame(rows)
OUT.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(OUT, index=False)

print("[OK] wrote", OUT)
print(df.to_string(index=False))
