from pathlib import Path
import trimesh

pfsep = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/aket01/partfield/partseps_low30k")
out = pfsep / "00000_partfield_clusters_colored.glb"

colors = [
    [255, 80, 80, 255],
    [80, 255, 80, 255],
    [80, 80, 255, 255],
    [255, 255, 80, 255],
    [255, 80, 255, 255],
    [80, 255, 255, 255],
]

scene = trimesh.Scene()

for i, ply in enumerate(sorted(pfsep.glob("00000_part_*.ply"))):
    if "_vmap" in ply.name:
        continue
    mesh = trimesh.load(ply, force="mesh", process=False)
    if hasattr(mesh.visual, "vertex_colors"):
        mesh.visual.vertex_colors = colors[i % len(colors)]
    scene.add_geometry(mesh, node_name=f"part_{i}")

scene.export(out)
print("[OK] wrote", out)
