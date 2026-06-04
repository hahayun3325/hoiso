from pathlib import Path
import json

score_path = Path.home() / "foho_phase0/inspection/oakink_000/oakink000_gpt55_internal_selector_variant_scores.json"
scores = json.loads(score_path.read_text())

def quality(s):
    if "error" in s:
        return 1e9
    return s["fragmentation_score"]

best_name = min(scores.keys(), key=lambda k: quality(scores[k]))

print("[SELECTOR_DECISION]", best_name)
print(json.dumps(scores[best_name], indent=2))

if best_name == "selector_phase42":
    print("FOHO_INTERNAL_PHASE42_SELECTOR_CHOICE=phase42_before_joint")
elif best_name == "selector_before42":
    print("FOHO_INTERNAL_PHASE42_SELECTOR_CHOICE=before_phase42")
else:
    print("[WARN] unknown selector choice")
