from pathlib import Path
from PIL import Image, ImageDraw
import pandas as pd

HOME = Path.home()
ROOT = Path("/home/fredcui/Projects/FollowMyHold")

CASES = ROOT / "docs/phase0/arctic_phase017_selected_cases.csv"
OVERLAY_DIR = HOME / "foho_phase0/inspection/arctic_phase017/gt_overlay_all_cases"
REPORT_DIR = HOME / "foho_phase0/inspection/arctic_phase017/final_report_assets"
OUT = REPORT_DIR / "arctic_selected_paper_style_qual_panel.jpg"

REPORT_DIR.mkdir(parents=True, exist_ok=True)

def make_cell(path, title, size=(320, 240)):
    cell = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(cell)

    if path and Path(path).exists():
        try:
            im = Image.open(path).convert("RGB")
            im.thumbnail((size[0], size[1] - 28))
            x = (size[0] - im.width) // 2
            y = 28 + (size[1] - 28 - im.height) // 2
            cell.paste(im, (x, y))
        except Exception as e:
            draw.text((10, 60), f"LOAD ERR\n{Path(path).name}\n{e}", fill="red")
    else:
        draw.text((10, 70), "MISSING", fill="red")

    draw.rectangle((0, 0, size[0]-1, size[1]-1), outline="black")
    draw.text((8, 8), title[:45], fill="black")
    return cell

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

    if scorer(imgs[0]) <= 0:
        return None
    return imgs[0]

df = pd.read_csv(CASES)

cols = [
    "Input",
    "GT 2D overlay",
    "Baseline inpaint",
    "Baseline final",
    "Selector inpaint",
    "Selector final",
]

cell_w, cell_h = 320, 240
sheet = Image.new("RGB", (cell_w * len(cols), cell_h * len(df)), "white")

for ridx, row in df.iterrows():
    case = row["case"]

    baseline_root = HOME / "foho_phase0/runs" / f"arctic_{case}_default"
    selector_root = HOME / "foho_phase0/runs" / f"arctic_{case}_gpt55_auto_selector_native_v2"

    paths = [
        row["input_path"],
        OVERLAY_DIR / f"{case}_gt_2d_official_overlay.jpg",
        find_image(baseline_root, "inpaint"),
        find_image(baseline_root, "final"),
        find_image(selector_root, "inpaint"),
        find_image(selector_root, "final"),
    ]

    titles = [
        f"{case} input",
        f"{case} GT overlay",
        "baseline inpaint",
        "baseline final",
        "selector inpaint",
        "selector final",
    ]

    for cidx, (p, title) in enumerate(zip(paths, titles)):
        cell = make_cell(p, title, size=(cell_w, cell_h))
        sheet.paste(cell, (cidx * cell_w, ridx * cell_h))

sheet.save(OUT)
print("[OK] wrote", OUT)
