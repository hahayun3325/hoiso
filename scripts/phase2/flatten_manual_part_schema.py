from pathlib import Path
import json
import pandas as pd

IN = Path("/home/fredcui/Projects/FollowMyHold/docs/phase2/gate_a_part_recon/arctic5_manual_part_schema.jsonl")
OUT = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/manual_part_schema/arctic5_manual_part_schema_flat.csv")

rows = []
for line in IN.read_text().splitlines():
    if not line.strip():
        continue
    d = json.loads(line)
    for idx, part in enumerate(d["main_parts"]):
        rows.append({
            "case_id": d["case_id"],
            "object_category": d["object_category"],
            "rigid_or_articulated": d["rigid_or_articulated"],
            "part_index": idx,
            "part_name": part["part_name"],
            "part_role": part["part_role"],
            "expected_geometry": part["expected_geometry"],
            "contact_relevance": part["contact_relevance"],
            "thin_or_small": part["thin_or_small"],
            "visible_in_image": part["visible_in_image"],
            "num_joints": len(d.get("joint_graph", [])),
            "joint_graph_json": json.dumps(d.get("joint_graph", [])),
        })

df = pd.DataFrame(rows)
OUT.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(OUT, index=False)

print("[OK] wrote", OUT)
print(df.to_string(index=False))
