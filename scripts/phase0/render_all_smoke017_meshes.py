from pathlib import Path
import trimesh

run = Path.home() / "foho_phase0/runs/smoke_017_prompt_rect_guidance_octree192_steps6"
out_dir = Path.home() / "foho_phase0/inspection/prompt_ablation/smoke017_all_mesh_renders"
out_dir.mkdir(parents=True, exist_ok=True)

mesh_paths = []
for ext in ["*.ply", "*.obj", "*.glb"]:
    mesh_paths.extend(run.rglob(ext))

for path in sorted(mesh_paths):
    try:
        mesh = trimesh.load(path, process=False)
        scene = mesh if isinstance(mesh, trimesh.Scene) else mesh.scene()
        rel = path.relative_to(run).as_posix().replace("/", "__").replace(".", "_")
        out = out_dir / f"{rel}.png"
        png = scene.save_image(resolution=(1024, 1024))
        out.write_bytes(png)
        print("[OK]", path, "->", out)
    except Exception as e:
        print("[BAD]", path, repr(e))
