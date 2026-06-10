from pathlib import Path
import csv
import numpy as np
import trimesh
from scipy.spatial import cKDTree

HOME = Path.home()
CASES = ["abox01", "aket01", "ascis01", "alapuse01", "amicuse01"]

def load_mesh(path):
    mesh = trimesh.load(path, process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    return mesh

def sample_vertices(mesh, n=20000):
    pts = np.asarray(mesh.vertices, dtype=np.float64)
    if len(pts) > n:
        idx = np.linspace(0, len(pts) - 1, n).astype(int)
        pts = pts[idx]
    return pts

def component_stats(mesh):
    comps = mesh.split(only_watertight=False)
    face_counts = np.array([len(c.faces) for c in comps], dtype=np.float64)
    largest = float(face_counts.max() / max(len(mesh.faces), 1)) if len(face_counts) else 0.0
    frag = float((len(comps) - 1) + (1.0 - largest))
    return len(comps), largest, frag, bool(mesh.is_watertight)

def contact_stats(hand, obj):
    hp = sample_vertices(hand)
    op = sample_vertices(obj)
    tree = cKDTree(op)
    d, _ = tree.query(hp, k=1)
    return {
        "hand_to_obj_min": float(d.min()),
        "hand_to_obj_p05": float(np.percentile(d, 5)),
        "hand_to_obj_mean": float(d.mean()),
    }

rows = []

for case in CASES:
    for method, run_id in [
        ("default", f"arctic_{case}_default"),
        ("gpt55_selector", f"arctic_{case}_gpt55_auto_selector_native_v2"),
    ]:
        run = HOME / "foho_phase0/runs" / run_id
        hand_p = run / "guidance_out" / f"{case}_hand.ply"
        obj_p = run / "guidance_out" / f"{case}_obj.ply"

        row = {
            "case": case,
            "method": method,
            "run_id": run_id,
            "hand_path": str(hand_p),
            "obj_path": str(obj_p),
            "hand_exists": hand_p.exists(),
            "obj_exists": obj_p.exists(),
        }

        if hand_p.exists() and obj_p.exists():
            hand = load_mesh(hand_p)
            obj = load_mesh(obj_p)
            comps, largest, frag, watertight = component_stats(obj)
            row.update({
                "obj_vertices": len(obj.vertices),
                "obj_faces": len(obj.faces),
                "obj_components": comps,
                "obj_largest_face_ratio": largest,
                "obj_fragmentation": frag,
                "obj_watertight": watertight,
            })
            row.update(contact_stats(hand, obj))

        rows.append(row)

out = HOME / "foho_phase0/inspection/arctic_phase017/arctic_default_vs_selector_proxy_metrics.csv"
out.parent.mkdir(parents=True, exist_ok=True)

fields = sorted(set().union(*[r.keys() for r in rows]))
with open(out, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)

print("[OK] wrote", out)
for r in rows:
    print(r)
