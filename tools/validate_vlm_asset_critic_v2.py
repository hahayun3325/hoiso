from pathlib import Path
import json
import sys

def as_list(value):
    return value if isinstance(value, list) else []

def as_dict(value):
    return value if isinstance(value, dict) else {}

def main():
    if len(sys.argv) < 6:
        print(
            "[HOLD] usage: python3 tools/validate_vlm_asset_critic_v2.py "
            "RESPONSE_JSON CASE_SPEC_JSON MANIFEST_JSON DECISION_JSON "
            "known_negative|candidate"
        )
        return

    response_path = Path(sys.argv[1])
    spec_path = Path(sys.argv[2])
    manifest_path = Path(sys.argv[3])
    decision_path = Path(sys.argv[4])
    experiment_role = sys.argv[5]
    decision_path.parent.mkdir(parents=True, exist_ok=True)

    audit = {
        "schema_version": "vlm_asset_gate_decision_v2",
        "authorized": False,
        "authorization_scope": "none",
        "validation_passed": False,
        "experiment_role": experiment_role,
        "reasons": [],
    }

    try:
        if not response_path.is_file():
            audit["reasons"].append("response_missing")
        elif not spec_path.is_file():
            audit["reasons"].append("case_spec_missing")
        elif not manifest_path.is_file():
            audit["reasons"].append("manifest_missing")
        else:
            response = json.loads(response_path.read_text())
            spec = json.loads(spec_path.read_text())
            manifest = json.loads(manifest_path.read_text())

            audit.update({
                "case_id": spec.get("case_id"),
                "candidate_id": spec.get("candidate_id"),
                "gate_mode": spec.get("gate_mode"),
                "response_path": str(response_path),
                "case_spec_path": str(spec_path),
                "manifest_path": str(manifest_path),
            })

            required_response_keys = [
                "schema_version", "case_id", "candidate_id", "gate_mode",
                "decision", "confidence", "fatal_vetoes",
                "target_object_assessment", "mask_assessment",
                "inpaint_assessment", "downstream_dryrun_assessment",
                "repair_instruction", "one_sentence_summary",
            ]
            missing_keys = [key for key in required_response_keys if key not in response]
            if missing_keys:
                audit["reasons"].append("missing_response_keys:" + ",".join(missing_keys))

            for field in ("case_id", "candidate_id", "gate_mode"):
                expected = spec.get(field)
                if response.get(field) != expected:
                    audit["reasons"].append(f"response_{field}_mismatch")
                if manifest.get(field) != expected:
                    audit["reasons"].append(f"manifest_{field}_mismatch")

            if response.get("schema_version") != "vlm_asset_critic_v2":
                audit["reasons"].append("response_schema_version_mismatch")

            missing_images = []
            for item in manifest.get("ordered_images", []):
                if item.get("required", False):
                    path_text = str(item.get("packet_path", ""))
                    if not path_text or not Path(path_text).is_file():
                        missing_images.append(str(item.get("role", "unknown")))
            if missing_images:
                audit["reasons"].append("required_images_missing:" + ",".join(missing_images))

            raw_decision = str(response.get("decision", "")).strip().lower()
            try:
                confidence = float(response.get("confidence", 0.0))
            except (TypeError, ValueError):
                confidence = 0.0
                audit["reasons"].append("confidence_not_numeric")

            fatal_vetoes = as_list(response.get("fatal_vetoes"))
            target = as_dict(response.get("target_object_assessment"))
            mask = as_dict(response.get("mask_assessment"))
            inpaint = as_dict(response.get("inpaint_assessment"))
            dryrun = as_dict(response.get("downstream_dryrun_assessment"))

            visible_failure = bool(
                fatal_vetoes
                or as_list(mask.get("included_forbidden_distractors"))
                or bool(mask.get("major_target_part_missing", False))
                or not bool(target.get("identity_matches", False))
                or as_list(target.get("missing_required_parts"))
                or as_list(inpaint.get("forbidden_distractors_present"))
                or not bool(inpaint.get("object_identity_preserved", False))
            )

            pass_checks = bool(
                raw_decision == "pass"
                and confidence >= float(spec.get("minimum_confidence", 0.75))
                and not fatal_vetoes
                and bool(target.get("identity_matches", False))
                and not as_list(target.get("missing_required_parts"))
                and bool(target.get("state_and_orientation_preserved", False))
                and bool(mask.get("includes_target_object", False))
                and not as_list(mask.get("included_forbidden_distractors"))
                and not bool(mask.get("major_target_part_missing", False))
                and bool(inpaint.get("object_identity_preserved", False))
                and bool(inpaint.get("state_and_orientation_preserved", False))
                and not as_list(inpaint.get("forbidden_distractors_present"))
            )

            mode = spec.get("gate_mode")
            if mode == "post_hunyuan":
                pass_checks = bool(
                    pass_checks
                    and bool(dryrun.get("available", False))
                    and not bool(dryrun.get("wrong_object_geometry_visible", False))
                    and not as_list(dryrun.get("forbidden_content_fused_into_object"))
                )
            elif mode != "pre_hunyuan":
                pass_checks = False
                audit["reasons"].append("invalid_gate_mode")

            if experiment_role == "known_negative":
                negative_rejected = bool(
                    raw_decision in {"reject", "repair_required"}
                    and confidence >= float(spec.get("minimum_confidence", 0.75))
                    and visible_failure
                )
                audit["validation_passed"] = negative_rejected
                audit["known_negative_rejected"] = negative_rejected
                if not negative_rejected:
                    audit["reasons"].append("known_negative_not_correctly_rejected")
            elif experiment_role == "candidate":
                audit["validation_passed"] = pass_checks
                audit["authorized"] = pass_checks
                if pass_checks:
                    audit["authorization_scope"] = (
                        "hunyuan_dryrun_only" if mode == "pre_hunyuan"
                        else "full_downstream"
                    )
                else:
                    audit["reasons"].append("candidate_failed_deterministic_checks")
            else:
                audit["reasons"].append("invalid_experiment_role")

    except Exception as error:
        audit["authorized"] = False
        audit["authorization_scope"] = "none"
        audit["validation_passed"] = False
        audit["reasons"].append(f"validator_exception:{type(error).__name__}:{error}")

    decision_path.write_text(json.dumps(audit, indent=2) + "\n")
    print(json.dumps(audit, indent=2))

    if audit.get("known_negative_rejected") is True:
        print(f"[PASS] KNOWN_NEGATIVE_REJECTED={decision_path}")
    elif audit.get("authorized") is True:
        print(
            f"[PASS] CANDIDATE_AUTHORIZED scope="
            f"{audit.get('authorization_scope')} decision={decision_path}"
        )
    else:
        print(f"[HOLD] VLM_ASSET_NOT_AUTHORIZED={decision_path}")

if __name__ == "__main__":
    main()
