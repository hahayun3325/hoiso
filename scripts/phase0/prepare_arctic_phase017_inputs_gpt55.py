from pathlib import Path
import shutil
import pandas as pd

root = Path("/home/fredcui/Projects/arctic/data/cropped_images_structured")
out_dir = Path.home() / "foho_phase0/inputs/arctic_phase017"
out_dir.mkdir(parents=True, exist_ok=True)

cases = [
    {
        "case_id": "abox01",
        "label": "box_grab_01",
        "path": root / "s01/box_grab_01/2/00082.jpg",
        "manual_prompt": "A rectangular cardboard box with flat square faces, sharp edges, printed window-like markings, and a boxy non-cylindrical shape; it is not a bottle, cup, or rounded can.",
    },
    {
        "case_id": "aket01",
        "label": "ketchup_grab_01",
        "path": root / "s01/ketchup_grab_01/7/00147.jpg",
        "manual_prompt": "A tall ketchup bottle with a red cylindrical body, green cap, curved side surfaces, and vertical bottle silhouette; it is not a box, cuboid, or flat rectangular object.",
    },
    {
        "case_id": "ascis01",
        "label": "scissors_grab_01",
        "path": root / "s01/scissors_grab_01/5/00365.jpg",
        "manual_prompt": "A pair of scissors with two thin metal blades and loop handles, forming a slender articulated tool with narrow elongated parts; it is not a solid block, bottle, or box.",
    },
    {
        "case_id": "alapuse01",
        "label": "laptop_use_01",
        "path": root / "s01/laptop_use_01/0/00114.jpg",
        "manual_prompt": "An open laptop with a flat rectangular screen connected by a hinge to a flat keyboard base, forming a two-panel articulated object; it is not a single closed box.",
    },
    {
        "case_id": "amicuse01",
        "label": "microwave_use_01",
        "path": root / "s01/microwave_use_01/0/00152.jpg",
        "manual_prompt": "A microwave oven with a box-shaped body and a front door opened on a side hinge, forming an articulated box-and-door object; it is not a single closed cube.",
    },
]

rows = []

for c in cases:
    dst = out_dir / f"{c['case_id']}.jpg"
    exists = c["path"].exists()
    if exists:
        shutil.copy2(c["path"], dst)
        print("[OK]", c["case_id"], "->", dst)
    else:
        print("[MISSING]", c["path"])

    rows.append({
        "case_id": c["case_id"],
        "label": c["label"],
        "image_id": c["case_id"],
        "image_path": str(dst),
        "source_path": str(c["path"]),
        "exists": exists,
        "manual_prompt": c["manual_prompt"],
    })

df = pd.DataFrame(rows)
out_csv = Path("docs/phase0/manual_llm_prompts/arctic_phase017_cases_gpt55.csv")
df.to_csv(out_csv, index=False)
print("[OK] wrote", out_csv)
print(df)
