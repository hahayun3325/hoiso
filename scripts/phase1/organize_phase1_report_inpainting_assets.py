#!/usr/bin/env python
from pathlib import Path
import shutil
import pandas as pd

REPORT_OUT = Path("/home/fredcui/foho_phase0/phase1_report_assets")
MANIFEST = REPORT_OUT / "manifests/report_asset_manifest.csv"
OUT_ROOT = REPORT_OUT / "inpainting"

df = pd.read_csv(MANIFEST)

IMAGE_EXTS = [".png", ".jpg", ".jpeg", ".webp"]

def score_image(path: Path):
    s = str(path).lower()
    score = 0

    # Prefer actual inpainting outputs.
    if "ours_inpaint" in s:
        score += 100
    if "inpaint" in s:
        score += 80

    # Useful visual stages.
    if "cropped_hoi" in s:
        score += 20
    if "wo_bckg" in s or "without" in s:
        score += 10

    # Avoid masks / tiny debug maps if possible.
    if "mask" in s:
        score -= 50
    if "normal" in s:
        score -= 30
    if "depth" in s:
        score -= 30
    if "alpha" in s:
        score -= 20

    try:
        score += min(path.stat().st_size / 1e6, 10)
    except Exception:
        pass

    return score

def find_best_inpaint_image(run_root: Path):
    candidates = []

    priority_dirs = [
        run_root / "ours_inpaint",
        run_root / "cropped_hoi_imgs_wo_bckg",
        run_root / "cropped_hoi_imgs",
        run_root / "masked_obj_imgs",
    ]

    for d in priority_dirs:
        if d.exists():
            for p in d.rglob("*"):
                if p.suffix.lower() in IMAGE_EXTS:
                    candidates.append(p)

    # Fallback: search entire run root.
    if not candidates and run_root.exists():
        for p in run_root.rglob("*"):
            if p.suffix.lower() in IMAGE_EXTS and ("inpaint" in str(p).lower() or "cropped" in str(p).lower()):
                candidates.append(p)

    if not candidates:
        return None, []

    candidates = sorted(set(candidates), key=lambda p: score_image(p), reverse=True)
    return candidates[0], candidates

rows = []

for _, r in df.iterrows():
    case = r["case"]
    method = r["method_key"]
    run_root = Path(str(r["run_root"]))

    out_dir = OUT_ROOT / case / method
    out_dir.mkdir(parents=True, exist_ok=True)

    best, candidates = find_best_inpaint_image(run_root)

    if best is None:
        rows.append({
            "case": case,
            "method_key": method,
            "run_root": str(run_root),
            "status": "missing_inpaint_image",
            "selected_source": "",
            "copied_image": "",
            "num_candidates": 0,
        })
        continue

    dst = out_dir / "inpaint_selected.png"
    shutil.copy2(best, dst)

    # Also copy top 3 candidates for manual checking.
    for i, p in enumerate(candidates[:3]):
        shutil.copy2(p, out_dir / f"candidate_{i}_{p.name}")

    rows.append({
        "case": case,
        "method_key": method,
        "run_root": str(run_root),
        "status": "ok",
        "selected_source": str(best),
        "copied_image": str(dst),
        "num_candidates": len(candidates),
    })

out = pd.DataFrame(rows)
out_path = REPORT_OUT / "manifests/inpainting_asset_manifest.csv"
out.to_csv(out_path, index=False)

print("[OK] wrote", out_path)
print(out.to_string(index=False))
