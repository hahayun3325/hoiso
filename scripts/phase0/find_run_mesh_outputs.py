from pathlib import Path
import sys

run = Path(sys.argv[1]).expanduser()

patterns = {
    "hunyuan_hoi": [
        "hunyuan_hoi_out/*hoi*.ply",
        "hunyuan_hoi_out/*.ply",
    ],
    "final_obj": [
        "guidance_out/*obj*.ply",
        "guidance_out/test_obj.ply",
        "guidance_out/*.ply",
    ],
    "final_hand": [
        "guidance_out/*hand*.ply",
        "guidance_out/test_hand.ply",
        "guidance_out/*.ply",
    ],
}

print(f"run={run}")

for name, pats in patterns.items():
    hits = []
    for pat in pats:
        hits.extend(sorted(run.glob(pat)))
    # Deduplicate while preserving order.
    seen = set()
    hits = [p for p in hits if not (p in seen or seen.add(p))]

    print(f"\n[{name}]")
    if hits:
        for p in hits:
            print(p)
    else:
        print("[MISSING]")
