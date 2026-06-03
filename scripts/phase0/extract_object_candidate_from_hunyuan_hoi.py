from pathlib import Path
import argparse
import trimesh
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("--mesh", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--rank", type=int, default=0)
args = ap.parse_args()

mesh_path = Path(args.mesh).expanduser()
out_path = Path(args.out).expanduser()
out_path.parent.mkdir(parents=True, exist_ok=True)

mesh = trimesh.load(mesh_path, process=False)
if isinstance(mesh, trimesh.Scene):
    mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))

components = sorted(
    mesh.split(only_watertight=False),
    key=lambda m: len(m.faces),
    reverse=True,
)

if args.rank >= len(components):
    raise ValueError(f"rank={args.rank} but only {len(components)} components exist")

comp = components[args.rank]
comp.export(out_path)

print("[OK] wrote", out_path)
print("rank:", args.rank)
print("vertices:", len(comp.vertices))
print("faces:", len(comp.faces))
print("bounds:", np.round(comp.bounds, 5).tolist())
print("extents:", np.round(comp.extents, 5).tolist())
