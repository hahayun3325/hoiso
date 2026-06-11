from pathlib import Path
import pandas as pd

HOME = Path.home()
ROOT = Path("/home/fredcui/Projects/FollowMyHold")

CASES = ROOT / "docs/phase0/arctic_phase017_selected_cases.csv"
OVERLAY_DIR = HOME / "foho_phase0/inspection/arctic_phase017/gt_overlay_all_cases"
REPORT_DIR = HOME / "foho_phase0/inspection/arctic_phase017/final_report_assets"
OUT = REPORT_DIR / "arctic_selected_paper_style_qual_panel_sources.csv"

def find_image(root, mode):
    root = Path(root)
    if not root.exists():
        return None

    imgs = [p for p in root.rglob("*") if p.suffix.lower() in [".jpg", ".jpeg", ".png"]]
    if not imgs:
        return None

    def score_inpaint(p):
        s = str(p).lower()
        score = 0
        if "inpaint" in s:
            score += 100
        if "object" in s or "obj" in s:
            score += 20
        if "mask" in s or "overlay" in s:
            score -= 50
        if "debug" in s:
            score += 5
        return score

    def score_final(p):
        s = str(p).lower()
        score = 0
        if "rendered_normal_t5" in s:
            score += 120
        if "rendered_normal" in s:
            score += 100
        if "final" in s:
            score += 50
        if "hoi" in s or "scene" in s:
            score += 20
        if "mask" in s or "overlay" in s:
            score -= 20
        return score

    scorer = score_inpaint if mode == "inpaint" else score_final
    imgs = sorted(imgs, key=lambda p: scorer(p), reverse=True)

    return imgs[0] if scorer(imgs[0]) > 0 else None

df = pd.read_csv(CASES)
rows = []

for _, row in df.iterrows():
    case = row["case"]
    baseline_root = HOME / "foho_phase0/runs" / f"arctic_{case}_default"
    selector_root = HOME / "foho_phase0/runs" / f"arctic_{case}_gpt55_auto_selector_native_v2"

    rows.append({
        "case": case,
        "input": row["input_path"],
        "gt_2d_overlay": str(OVERLAY_DIR / f"{case}_gt_2d_official_overlay.jpg"),
        "baseline_inpaint_selected": str(find_image(baseline_root, "inpaint")),
        "baseline_final_selected": str(find_image(baseline_root, "final")),
        "selector_inpaint_selected": str(find_image(selector_root, "inpaint")),
        "selector_final_selected": str(find_image(selector_root, "final")),
        "baseline_root": str(baseline_root),
        "selector_root": str(selector_root),
    })

out = pd.DataFrame(rows)
REPORT_DIR.mkdir(parents=True, exist_ok=True)
out.to_csv(OUT, index=False)

print("[OK] wrote", OUT)
print(out.to_string(index=False))
