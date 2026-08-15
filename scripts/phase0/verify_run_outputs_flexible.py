from pathlib import Path
import sys

run = Path(sys.argv[1]).expanduser()

hunyuan = list((run / "hunyuan_hoi_out").glob("*.ply"))
guidance = list((run / "guidance_out").glob("*.ply"))

obj = [p for p in guidance if "obj" in p.name.lower()]
hand = [p for p in guidance if "hand" in p.name.lower()]

print("run:", run)
print("hunyuan_mesh_count:", len(hunyuan))
print("guidance_mesh_count:", len(guidance))
print("object_candidates:", [str(p) for p in obj])
print("hand_candidates:", [str(p) for p in hand])

if hunyuan and obj and hand:
    print("[OK] run produced required meshes")
else:
    print("[STOP] missing required mesh category")
