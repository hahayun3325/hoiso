from pathlib import Path
import os
import shutil
import subprocess
import sys

run = Path(sys.argv[1]).expanduser()

hunyuan_hits = sorted((run / "hunyuan_hoi_out").glob("*hoi*.ply")) or sorted((run / "hunyuan_hoi_out").glob("*.ply"))
obj_hits = sorted((run / "guidance_out").glob("*obj*.ply"))
hand_hits = sorted((run / "guidance_out").glob("*hand*.ply"))

if not hunyuan_hits or not obj_hits or not hand_hits:
    print("[ERROR] missing required outputs")
    print("hunyuan:", hunyuan_hits)
    print("obj:", obj_hits)
    print("hand:", hand_hits)
    sys.exit(1)

hunyuan = hunyuan_hits[0]
obj = obj_hits[0]
hand = hand_hits[0]

shutil.copy2(hunyuan, run / "hunyuan_hoi_out/test_hoi_mesh.ply")
shutil.copy2(obj, run / "guidance_out/test_obj.ply")
shutil.copy2(hand, run / "guidance_out/test_hand.ply")

env = os.environ.copy()
env["FOHO_ENABLE_OBJECT_FALLBACK"] = "1"
env["FOHO_FALLBACK_ALIGN_MODE"] = "bbox"
env["FOHO_RUN_DIR"] = str(run)
env["FOHO_INITIAL_OBJECT"] = str(run / "hunyuan_hoi_out/test_hoi_mesh.ply")

print("[OK] compatibility copies created")
print("[INFO] hunyuan:", hunyuan)
print("[INFO] obj:", obj)
print("[INFO] hand:", hand)

subprocess.run(
    ["python", "scripts/phase0/apply_object_fallback_optional.py"],
    check=True,
    env=env,
)
