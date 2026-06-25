from pathlib import Path
import json
import trimesh

DATA = Path("/home/fredcui/foho_phase0")
PHASE2_ROOT = DATA / "phase2_gateA_part_recon"
case = "aket01"

case_root = PHASE2_ROOT / "cases" / case
obj_path = case_root / "input/final_object_singleblob.ply"
schema_path = case_root / "schema/part_schema.json"
out_path = case_root / "metrics/gate_a_case_ready_report.json"

obj = trimesh.load(obj_path, force="mesh")
schema = json.loads(schema_path.read_text())

parts = [p["part_name"] for p in schema["main_parts"]]
components = obj.split(only_watertight=False)

report = {
    "case": case,
    "object_mesh": str(obj_path),
    "schema": str(schema_path),
    "num_vertices": int(len(obj.vertices)),
    "num_faces": int(len(obj.faces)),
    "num_connected_components": int(len(components)),
    "schema_parts": parts,
    "num_schema_parts": len(parts),
    "rigid_or_articulated": schema["rigid_or_articulated"],
    "joint_graph": schema.get("joint_graph", []),
    "ready_for_part_split": True,
    "next_step": "run PartField/SAM2/manual part mesh splitting"
}

out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
