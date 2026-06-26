from pathlib import Path
import argparse
import json
import pandas as pd

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    src = Path(args.json)
    out = Path(args.out)

    data = json.loads(src.read_text())
    rows = []
    for c in data.get("contacts", []):
        rows.append({
            "case_id": data["case_id"],
            "frame_id": data.get("frame_id", "single_image"),
            "source": data.get("source", ""),
            "camera_view": data.get("camera_view", "uncertain"),
            "hand": c["hand"],
            "finger": c["finger"],
            "object_part": c["object_part"],
            "state": c["state"],
            "confidence": c["confidence"],
            "false_positive_risk": c["false_positive_risk"],
            "should_use_for_optimization": c["should_use_for_optimization"],
            "visual_evidence": c["visual_evidence"],
            "notes": c.get("notes", "")
        })

    df = pd.DataFrame(rows)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print("[OK] wrote", out)
    print(df.to_string(index=False))

if __name__ == "__main__":
    main()
