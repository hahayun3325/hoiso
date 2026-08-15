from pathlib import Path
import json
import sys

def main():
    if len(sys.argv) < 4:
        print("[HOLD] usage: python tools/validate_vlm_inpaint_asset.py RESPONSE_JSON CANDIDATE_DIR AUTH_ENV")
        return

    response_path = Path(sys.argv[1])
    candidate_dir = Path(sys.argv[2])
    auth_env = Path(sys.argv[3])
    auth_env.parent.mkdir(parents=True, exist_ok=True)

    result = {
        "authorized": False,
        "reason": "uninitialized",
        "response": str(response_path),
        "candidate_dir": str(candidate_dir),
        "preferred_image": ""
    }

    try:
        if not response_path.is_file():
            result["reason"] = "response_json_missing"
        else:
            r = json.loads(response_path.read_text())

            required = [
                "schema_version",
                "case_id",
                "candidate_id",
                "decision",
                "confidence",
                "fatal_vetoes",
                "mask_assessment",
                "inpaint_or_object_image_assessment",
                "authorization_recommendation",
                "repair_instruction",
                "one_sentence_summary",
            ]

            missing = [k for k in required if k not in r]
            if missing:
                result["reason"] = "missing_required_keys:" + ",".join(missing)
            elif r.get("schema_version") != "vlm_inpaint_asset_critic_v1":
                result["reason"] = "schema_version_mismatch"
            elif r.get("case_id") != "alapuse02v3n60":
                result["reason"] = "case_id_mismatch"
            else:
                decision = str(r.get("decision", "")).lower()
                fatal = r.get("fatal_vetoes", [])

                mask = r.get("mask_assessment", {})
                img = r.get("inpaint_or_object_image_assessment", {})
                auth = r.get("authorization_recommendation", {})

                deterministic_veto = []

                if not mask.get("laptop_only", False):
                    deterministic_veto.append("mask_not_laptop_only")
                if mask.get("includes_wooden_stand", False):
                    deterministic_veto.append("mask_includes_wooden_stand")
                if mask.get("includes_hand_or_arm", False):
                    deterministic_veto.append("mask_includes_hand_or_arm")
                if mask.get("includes_table_background_cables", False):
                    deterministic_veto.append("mask_includes_background")

                for key in ["includes_screen_lid", "includes_keyboard_base", "includes_hinge_or_side_frame"]:
                    if not mask.get(key, False):
                        deterministic_veto.append("mask_missing_" + key)

                if not img.get("laptop_identity_preserved", False):
                    deterministic_veto.append("object_identity_not_preserved")
                if not img.get("screen_lid_preserved", False):
                    deterministic_veto.append("screen_lid_not_preserved")
                if not img.get("keyboard_base_preserved", False):
                    deterministic_veto.append("keyboard_base_not_preserved")
                if not img.get("hinge_angle_preserved", False):
                    deterministic_veto.append("hinge_angle_not_preserved")
                if not img.get("viewpoint_preserved", False):
                    deterministic_veto.append("viewpoint_not_preserved")
                if not img.get("wooden_stand_removed", False):
                    deterministic_veto.append("wooden_stand_not_removed")
                if img.get("wooden_stand_visible", False):
                    deterministic_veto.append("wooden_stand_visible")
                if img.get("large_hallucination", False):
                    deterministic_veto.append("large_hallucination")
                if img.get("major_pose_or_scale_drift", False):
                    deterministic_veto.append("pose_or_scale_drift")

                preferred = str(auth.get("preferred_image_for_hunyuan", "")).strip()
                preferred_path = candidate_dir / preferred if preferred and preferred != "none" else Path("")

                if decision != "pass":
                    result["reason"] = "decision_not_pass"
                elif fatal:
                    result["reason"] = "fatal_vetoes_present"
                elif deterministic_veto:
                    result["reason"] = "deterministic_veto:" + ",".join(deterministic_veto)
                elif not auth.get("authorize_hunyuan", False):
                    result["reason"] = "vlm_does_not_authorize_hunyuan"
                elif not preferred_path.is_file():
                    result["reason"] = "preferred_hunyuan_image_missing:" + preferred
                else:
                    result["authorized"] = True
                    result["reason"] = "pass"
                    result["preferred_image"] = str(preferred_path)

    except Exception as exc:
        result["reason"] = f"validator_exception:{type(exc).__name__}:{exc}"

    auth_json = auth_env.with_suffix(".json")
    auth_json.write_text(json.dumps(result, indent=2) + "\n")

    auth_env.write_text(
        f"export VLM_INPAINT_AUTHORIZED={'1' if result['authorized'] else '0'}\n"
        f"export VLM_INPAINT_AUTH_REASON={json.dumps(result['reason'])}\n"
        f"export VLM_INPAINT_PREFERRED_IMAGE={json.dumps(result['preferred_image'])}\n"
        f"export VLM_INPAINT_AUTH_JSON={json.dumps(str(auth_json))}\n"
    )

    print(json.dumps(result, indent=2))
    if result["authorized"]:
        print(f"[PASS] VLM_INPAINT_ASSET_AUTHORIZED={auth_env}")
    else:
        print(f"[HOLD] VLM_INPAINT_ASSET_NOT_AUTHORIZED reason={result['reason']} env={auth_env}")

if __name__ == "__main__":
    main()
