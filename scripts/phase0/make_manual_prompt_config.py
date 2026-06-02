from pathlib import Path
import argparse
import csv
import os

def set_env_line(text, key, value):
    line = f'{key}="{value}"'
    lines = text.splitlines()
    out = []
    found = False
    for x in lines:
        if x.startswith(f"{key}="):
            out.append(line)
            found = True
        else:
            out.append(x)
    if not found:
        out.append(line)
    return "\n".join(out) + "\n"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base_config", default="configs/pipeline.phase0.oakink000.env")
    ap.add_argument("--run_id", required=True)
    ap.add_argument("--image_id", required=True)
    ap.add_argument("--image_path", required=True)
    ap.add_argument("--response", required=True)
    ap.add_argument("--dataset_tag", default="manual")
    args = ap.parse_args()

    run_dir = Path.home() / f"foho_phase0/runs/{args.run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)

    prompt_csv = run_dir / "manual_gemini_responses.csv"
    with prompt_csv.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["image_id", "image_path", "response"])
        w.writerow([args.image_id, args.image_path, args.response])

    base = Path(args.base_config)
    text = base.read_text()

    text = set_env_line(text, "BASE_DIR", str(run_dir))
    text = set_env_line(text, "IMAGE_PATH", args.image_path)
    text = set_env_line(text, "GEMINI_RESPONSES", str(prompt_csv))
    text = set_env_line(text, "GEMINI_API_KEY", "")

    # Keep debug local to this run.
    text = set_env_line(text, "FOHO_DEBUG_DIR", str(run_dir / "foho_debug"))

    out_cfg = Path("configs/generated") / f"pipeline.phase0.{args.run_id}.env"
    out_cfg.write_text(text)

    print("[OK] run_dir:", run_dir)
    print("[OK] prompt_csv:", prompt_csv)
    print("[OK] config:", out_cfg)
    print("[INFO] response:", args.response)

if __name__ == "__main__":
    main()
