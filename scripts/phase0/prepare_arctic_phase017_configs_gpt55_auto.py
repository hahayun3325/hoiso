from pathlib import Path
import csv
import re
import pandas as pd

ROOT = Path("/home/fredcui/Projects/FollowMyHold")
HOME = Path.home()

CSV_PATH = ROOT / "docs/phase0/manual_llm_prompts/arctic_phase017_cases_gpt55.csv"
OUT_CFG_DIR = ROOT / "configs/generated"
OUT_CFG_DIR.mkdir(parents=True, exist_ok=True)

TEMPLATE_CANDIDATES = [
    ROOT / "configs/generated/pipeline.phase0.oakink000_gpt55_short.env",
    ROOT / "configs/pipeline.phase0.env",
    ROOT / "configs/pipeline.phase0.template.env",
]

INPUT_SEARCH_DIRS = [
    HOME / "foho_phase0/inputs/arctic",
    HOME / "foho_phase0/inputs/arctic_phase017",
    HOME / "foho_phase0/inputs",
]

def q(s):
    return '"' + str(s).replace('"', '\\"') + '"'

def set_env(text, key, value):
    line = f'{key}={q(value)}'
    pat = re.compile(rf'^{re.escape(key)}=.*$', re.M)
    if pat.search(text):
        return pat.sub(line, text)
    return text.rstrip() + "\n" + line + "\n"

def find_template():
    for p in TEMPLATE_CANDIDATES:
        if p.exists():
            return p
    raise FileNotFoundError("No config template found.")

def find_image(row):
    for col in ["image_path", "input_path", "path"]:
        if col in row and str(row[col]).strip() and str(row[col]) != "nan":
            p = Path(str(row[col])).expanduser()
            if p.exists():
                return p

    case_id = str(row["case_id"])
    patterns = [
        f"{case_id}.png",
        f"{case_id}.jpg",
        f"{case_id}.jpeg",
        f"*{case_id}*.png",
        f"*{case_id}*.jpg",
        f"*{case_id}*.jpeg",
    ]

    for base in INPUT_SEARCH_DIRS:
        if not base.exists():
            continue
        for pat in patterns:
            hits = sorted(base.rglob(pat))
            hits = [h for h in hits if h.is_file()]
            if hits:
                return hits[0]

    raise FileNotFoundError(f"Cannot find image for case_id={case_id}")

def main():
    df = pd.read_csv(CSV_PATH).fillna("")
    template_path = find_template()
    template = template_path.read_text()

    print("[INFO] template:", template_path)

    for _, row in df.iterrows():
        case_id = str(row["case_id"])
        prompt = str(row["manual_prompt"]).strip()
        img = find_image(row)

        run_id = f"arctic_{case_id}_gpt55_auto"
        run_dir = HOME / "foho_phase0/runs" / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        prompt_csv = run_dir / "manual_gemini_responses.csv"
        with prompt_csv.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["image_id", "image_path", "response"])
            writer.writeheader()
            writer.writerow({
                "image_id": case_id,
                "image_path": str(img),
                "response": prompt,
            })

        selector_dir = HOME / "foho_phase0/inspection/arctic_phase017" / run_id / "internal_selector_debug"

        cfg = template
        cfg = set_env(cfg, "IMAGE_PATH", img)
        cfg = set_env(cfg, "GEMINI_RESPONSES", prompt_csv)
        cfg = set_env(cfg, "RUN_ID", run_id)
        cfg = set_env(cfg, "FOHO_RUN_DIR", run_dir)
        cfg = set_env(cfg, "OUTPUT_DIR", run_dir)
        cfg = set_env(cfg, "FOHO_ENABLE_INTERNAL_PHASE42_SELECTOR", "1")
        cfg = set_env(cfg, "FOHO_INTERNAL_PHASE42_SELECTOR_CHOICE", "auto_fragmentation")
        cfg = set_env(cfg, "FOHO_INTERNAL_SELECTOR_EXPORT_DIR", selector_dir)

        out_cfg = OUT_CFG_DIR / f"pipeline.phase0.{run_id}.env"
        out_cfg.write_text(cfg)

        print("[OK]", run_id)
        print("     image:", img)
        print("     prompt_csv:", prompt_csv)
        print("     config:", out_cfg)

if __name__ == "__main__":
    main()
