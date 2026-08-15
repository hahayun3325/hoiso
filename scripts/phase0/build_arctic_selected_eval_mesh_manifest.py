from pathlib import Path
import pandas as pd

HOME = Path.home()
ROOT = Path("/home/fredcui/Projects/FollowMyHold")
CASES = ROOT / "docs/phase0/arctic_phase017_selected_cases.csv"
OUT = HOME / "foho_phase0/inspection/arctic_phase017/paper_style_eval_selected_cases/arctic_selected_eval_mesh_manifest.csv"

methods = {
    "default": "arctic_{case}_default",
    "gpt55_selector": "arctic_{case}_gpt55_auto_selector_native_v2",
}

def pick_final(root, kind):
    # Prefer final FOHO output; fallback to guidance_out.
    candidates = []
    candidates += sorted(root.glob(f"foho_debug/*/final_{kind}_mesh.ply"))
    if kind == "obj":
        candidates += [root / "guidance_out" / f"{root.name.split('_')[1]}_obj.ply"]
    if kind == "hand":
        candidates += [root / "guidance_out" / f"{root.name.split('_')[1]}_hand.ply"]

    candidates = [p for p in candidates if p.exists()]
    return candidates[0] if candidates else None

df = pd.read_csv(CASES)
rows = []

for _, r in df.iterrows():
    case = r["case"]
    for method, template in methods.items():
        run_root = HOME / "foho_phase0/runs" / template.format(case=case)

        hand = pick_final(run_root, "hand")
        obj = pick_final(run_root, "obj")

        rows.append({
            "case": case,
            "method": method,
            "subject": r["subject"],
            "seq_name": r["seq_name"],
            "frame": int(r["frame"]),
            "view_id": int(r["view_id"]),
            "gt_processed": f"/home/fredcui/Projects/arctic/outputs/processed_verts/seqs/{r['subject']}/{r['seq_name']}.npy",
            "run_root": str(run_root),
            "hand_mesh": str(hand) if hand else "",
            "object_mesh": str(obj) if obj else "",
            "hand_exists": bool(hand and hand.exists()),
            "object_exists": bool(obj and obj.exists()),
        })

out_df = pd.DataFrame(rows)
OUT.parent.mkdir(parents=True, exist_ok=True)
out_df.to_csv(OUT, index=False)

print("[OK] wrote", OUT)
print(out_df.to_string(index=False))
