#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load(path: Path):
    return json.loads(path.read_text())


def require_file(path_value, label: str, errors: list[str]) -> str | None:
    if not path_value:
        errors.append(f"missing_path:{label}")
        return None
    p = Path(path_value)
    if not p.is_file() or p.stat().st_size == 0:
        errors.append(f"invalid_file:{label}:{p}")
        return None
    return str(p.resolve())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--semantic", required=True)
    ap.add_argument("--finger-map", required=True)
    ap.add_argument("--patch-map", required=True)
    ap.add_argument("--policy", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    paths = {k: Path(v) for k, v in {
        "semantic": a.semantic, "finger_map": a.finger_map,
        "patch_map": a.patch_map, "policy": a.policy}.items()}
    sem, fmap, pmap, policy = (load(paths[k]) for k in ("semantic", "finger_map", "patch_map", "policy"))
    errors: list[str] = []
    if sem.get("decision") != "compile": errors.append("semantic_decision_not_compile")
    if fmap.get("status") != "PASS": errors.append("finger_map_not_PASS")
    if pmap.get("status") != "PASS": errors.append("patch_map_not_PASS")
    compiled_contacts = []
    active_params = []
    for c in sem.get("contacts", []):
        finger = c["finger"]
        fg = fmap.get("fingers", {}).get(finger)
        if not fg:
            errors.append(f"unknown_finger:{finger}")
            continue
        part, region = c["object_part"], c["object_region"]
        patch = pmap.get("parts", {}).get(part, {}).get("regions", {}).get(region)
        if not patch:
            errors.append(f"unknown_patch:{part}/{region}")
            continue
        face_path = require_file(patch.get("face_ids_path"), f"faces:{part}/{region}", errors)
        vertex_path = require_file(patch.get("vertex_ids_path"), f"vertices:{part}/{region}", errors)
        contact_vertices = fg.get("contact_vertex_ids") or fg.get("tip_vertex_ids") or []
        params = fg.get("joint_parameter_names") or []
        if not contact_vertices: errors.append(f"empty_contact_vertices:{finger}")
        if c["contact_mode"] in {"touch", "near_contact"} and not params and finger != "palm":
            errors.append(f"empty_joint_parameters:{finger}")
        active_params.extend(params)
        conf = float(c["confidence"])
        cp = policy["confidence_policy"]
        if conf >= cp["active_attraction_min"]:
            attraction = "active"
            multiplier = conf
        elif conf >= cp["weak_attraction_min"]:
            attraction = "weak"
            multiplier = conf * cp["weak_weight_multiplier"]
        else:
            attraction = "diagnostic_only"
            multiplier = 0.0
        compiled_contacts.append({
            **c,
            "mano_contact_vertex_ids": sorted(set(map(int, contact_vertices))),
            "mano_joint_parameter_names": list(dict.fromkeys(params)),
            "object_patch_face_ids_path": face_path,
            "object_patch_vertex_ids_path": vertex_path,
            "attraction_policy": attraction,
            "objective_weight_multiplier": multiplier,
            "target_gap_mm": policy["contact"]["default_target_gap_mm"],
            "gap_tolerance_mm": policy["contact"]["default_gap_tolerance_mm"]
        })
    forbidden = []
    for r in sem.get("forbidden_regions", []):
        part, region = r["object_part"], r["object_region"]
        patch = pmap.get("parts", {}).get(part, {}).get("regions", {}).get(region)
        if not patch:
            errors.append(f"unknown_forbidden_patch:{part}/{region}")
            continue
        forbidden.append({
            **r,
            "object_patch_face_ids_path": require_file(patch.get("face_ids_path"), f"forbidden_faces:{part}/{region}", errors),
            "object_patch_vertex_ids_path": require_file(patch.get("vertex_ids_path"), f"forbidden_vertices:{part}/{region}", errors),
            "minimum_clearance_mm": policy["forbidden"]["default_clearance_mm"]
        })
    out_data = {
        "schema": "hoiso_gate_d0_compiled_contract_v1",
        "status": "PASS" if not errors else "HOLD",
        "case_id": sem.get("case_id"),
        "active_hand": sem.get("active_hand"),
        "contact_state": sem.get("contact_state"),
        "compiled_contacts": compiled_contacts,
        "compiled_forbidden_regions": forbidden,
        "active_hand_parameter_names": sorted(set(active_params)),
        "z_order_policy": policy["z_order"],
        "uncertainty": sem.get("uncertainty", ""),
        "source_files": {k: str(v.resolve()) for k,v in paths.items()},
        "source_hashes": {k: sha256(v) for k,v in paths.items()},
        "errors": errors,
        "authorizes_optimizer": False
    }
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(out_data, indent=2)+"\n")
    print(json.dumps(out_data, indent=2))
    return 0 if out_data["status"] == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
