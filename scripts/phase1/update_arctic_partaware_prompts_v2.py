#!/usr/bin/env python
from pathlib import Path
import pandas as pd

# Change this if your active prompt CSV is different.
IN_CSV = Path("docs/phase0/manual_llm_prompts/arctic_phase017_cases_gpt55.csv")
OUT_CSV = Path("docs/phase0/manual_llm_prompts/arctic_phase017_cases_gpt55_partaware_v2.csv")

PROMPTS = {
    "abox01": (
        "A plain rectangular box, rigid cuboid object with six flat faces, sharp straight edges and square corners, "
        "closed solid volume, matte cardboard/plastic-like surface, not a bag, bottle, rounded container, or soft object."
    ),
    "aket01": (
        "A ketchup bottle, rigid squeeze-bottle with narrow neck and small cap above wider rounded-rectangular body, "
        "smooth curved sides and flat label faces, plastic red/white appearance, not a can, cup, box, or cylinder-only object."
    ),
    "ascis01": (
        "A pair of scissors, articulated two-blade tool with central pivot, two thin elongated blades and loop handles, "
        "narrow flat metal parts, open V-shaped silhouette if visible, not pliers, tongs, knife, or a single solid object."
    ),
    "alapuse01": (
        "An open laptop, articulated two-part object with flat base and thin rectangular screen connected by rear hinge, "
        "L-shaped side silhouette, large flat panels and sharp corners, dark/gray rigid material, not a closed box, book, tablet, or single slab."
    ),
    "amicuse01": (
        "A microwave oven with articulated front door, boxy main body plus hinged rectangular door panel, flat faces and sharp edges, "
        "visible window/handle if present, rigid plastic/metal shell, not a laptop, toaster, cube-only block, or open box."
    ),
}

def find_col(cols, candidates):
    lower = {c.lower(): c for c in cols}
    for x in candidates:
        if x.lower() in lower:
            return lower[x.lower()]
    return None

def main():
    if not IN_CSV.exists():
        raise FileNotFoundError(f"Input CSV not found: {IN_CSV}")

    df = pd.read_csv(IN_CSV)

    case_col = find_col(df.columns, ["case", "case_id", "object_id", "object_name", "sample_case"])
    if case_col is None:
        # fallback: use sample_id if it contains abox01 etc.
        case_col = find_col(df.columns, ["sample_id", "id", "name"])

    prompt_col = find_col(df.columns, [
        "prompt",
        "object_prompt",
        "manual_prompt",
        "gpt55_prompt",
        "text_prompt",
        "object_description",
        "description",
    ])

    if case_col is None or prompt_col is None:
        print("Columns:", list(df.columns))
        raise RuntimeError("Could not infer case column or prompt column. Please set case_col/prompt_col manually.")

    df["prompt_template_version"] = "partaware_v2"
    df["prompt_update_note"] = ""

    updated = 0
    for idx, row in df.iterrows():
        row_text = " ".join(str(v).lower() for v in row.values)
        matched_case = None
        for case in PROMPTS:
            if case in row_text:
                matched_case = case
                break

        if matched_case is not None:
            df.at[idx, prompt_col] = PROMPTS[matched_case]
            df.at[idx, "prompt_update_note"] = (
                "Part-aware ARCTIC prompt: includes rigid/articulated type, parts, hinge/pivot/open state, "
                "contact-relevant surfaces, and negative constraints."
            )
            updated += 1

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_CSV, index=False)

    print("[OK] wrote", OUT_CSV)
    print("case_col =", case_col)
    print("prompt_col =", prompt_col)
    print("updated_rows =", updated)

    if updated == 0:
        print("[WARN] No rows updated. Inspect the CSV columns and row values.")

if __name__ == "__main__":
    main()
