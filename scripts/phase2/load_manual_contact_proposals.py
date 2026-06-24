from pathlib import Path
import pandas as pd

def load_manual_contact_proposals(path):
    path = Path(path)
    df = pd.read_csv(path)

    required = [
        "case_id",
        "frame_id",
        "hand",
        "finger",
        "object_part",
        "state",
        "confidence",
        "false_positive_risk",
        "should_use_for_optimization",
        "visual_evidence",
    ]

    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in manual contact file: {missing}")

    df["confidence"] = df["confidence"].astype(float)
    df["should_use_for_optimization"] = df["should_use_for_optimization"].astype(str).str.lower().isin(["true", "1", "yes"])

    return df

if __name__ == "__main__":
    p = "/home/fredcui/Projects/FollowMyHold/docs/phase2/gate_b_manual_contact/arctic5_manual_contact_proposals.csv"
    df = load_manual_contact_proposals(p)
    print(df.to_string(index=False))
    print("manual_contact_rows =", len(df))
