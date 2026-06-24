from pathlib import Path
import json

p = Path("/home/fredcui/Projects/FollowMyHold/docs/phase2/gate_a_part_recon/arctic5_manual_part_schema.jsonl")

required_top = [
    "case_id",
    "object_category",
    "rigid_or_articulated",
    "main_parts",
    "joint_graph",
    "part_segmentation_guidance",
    "negative_constraints",
    "confidence_notes",
]

ok = True
seen = []

for i, line in enumerate(p.read_text().splitlines(), start=1):
    if not line.strip():
        continue
    try:
        d = json.loads(line)
    except Exception as e:
        print("[BAD JSON]", i, e)
        ok = False
        continue

    seen.append(d.get("case_id", ""))

    for k in required_top:
        if k not in d:
            print("[BAD] missing key", i, k)
            ok = False

    if not isinstance(d.get("main_parts", None), list) or len(d["main_parts"]) == 0:
        print("[BAD] no main_parts", i)
        ok = False

    for part in d.get("main_parts", []):
        for k in ["part_name", "part_role", "expected_geometry", "contact_relevance", "thin_or_small", "visible_in_image"]:
            if k not in part:
                print("[BAD] missing part key", i, d.get("case_id"), k)
                ok = False

print("seen_cases =", seen)
print("manual_part_schema_ok =", ok)
if not ok:
    raise SystemExit("[BAD] manual part schema validation failed")
