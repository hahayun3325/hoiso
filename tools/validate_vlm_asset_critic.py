from pathlib import Path
import json
import sys

def main():
    if len(sys.argv) < 4:
        print("[HOLD] usage: python tools/validate_vlm_asset_critic.py RESPONSE_JSON MANIFEST_JSON AUTH_ENV")
        return

    response_path = Path(sys.argv[1])
    manifest_path = Path(sys.argv[2])
    auth_env = Path(sys.argv[3])

    auth_env.parent.mkdir(parents=True, exist_ok=True)

    result = {
        "authorized": False,
        "reason": "uninitialized",
        "response": str(response_path),
        "manifest": str(manifest_path)
    }

    try:
        if not response_path.is_file():
            result["reason"] = "response_json_missing"
        elif not manifest_path.is_file():
            result["reason"] = "manifest_json_missing"
        else:
            response = json.loads(response_path.read_text())
            manifest = json.loads(manifest_path.read_text())

            required = [
                "schema_version",
                "case_id",
                "candidate_id",
                "decision",
                "confidence",
                "fatal_vetoes",
                "target_object_assessment",
                "mask_assessment",
                "inpaint_assessment",
                "downstream_dryrun_assessment",
                "repair_instruction",
                "one_sentence_summary"
            ]

            missing = [k for k in required if k not in response]
            if missing:
                result["reason"] = "missing_required_keys:" + ",".join(missing)
            elif response.get("schema_version") != "vlm_asset_critic_v1":
                result["reason"] = "schema_version_mismatch"
            elif response.get("case_id") != manifest.get("case_id"):
                result["reason"] = "case_id_mismatch"
            else:
                decision = str(response.get("decision", "")).strip().lower()
                fatal_vetoes = response.get("fatal_vetoes", [])

                target = response.get("target_object_assessment", {})
                mask = response.get("mask_assessment", {})
                inpaint = response.get("inpaint_assessment", {})
                dryrun = response.get("downstream_dryrun_assessment", {})

                includes_stand = bool(mask.get("includes_wooden_stand", False))
                inpaint_keeps_stand = not bool(inpaint.get("stand_removed_or_excluded", True))
                dryrun_fused_stand = bool(dryrun.get("stand_fused_into_object", False))
                missing_laptop = (
                    not bool(target.get("screen_lid_visible", False))
                    or not bool(target.get("keyboard_base_visible", False))
                )

                if decision not in {"reject", "repair_required", "pass"}:
                    result["reason"] = "invalid_decision"
                elif decision == "pass" and fatal_vetoes:
                    result["reason"] = "pass_with_fatal_vetoes"
                elif decision == "pass" and (
                    includes_stand
                    or inpaint_keeps_stand
                    or dryrun_fused_stand
                    or missing_laptop
                ):
                    result["reason"] = "pass_contradicts_deterministic_veto"
                elif decision in {"reject", "repair_required"}:
                    result["authorized"] = False
                    result["reason"] = "repair_required_or_rejected"
                elif decision == "pass":
                    result["authorized"] = True
                    result["reason"] = "vlm_pass_and_deterministic_checks_pass"

    except Exception as exc:
        result["authorized"] = False
        result["reason"] = f"validator_exception:{type(exc).__name__}:{exc}"

    auth_json = auth_env.with_suffix(".json")
    auth_json.write_text(json.dumps(result, indent=2) + "\n")

    auth_env.write_text(
        f"export VLM_AUTHORIZED={'1' if result['authorized'] else '0'}\n"
        f"export VLM_AUTH_REASON={json.dumps(result['reason'])}\n"
        f"export VLM_AUTH_JSON={json.dumps(str(auth_json))}\n"
    )

    print(json.dumps(result, indent=2))
    if result["authorized"]:
        print(f"[PASS] VLM_ASSET_AUTHORIZED={auth_env}")
    else:
        print(f"[HOLD] VLM_ASSET_NOT_AUTHORIZED reason={result['reason']} env={auth_env}")

if __name__ == "__main__":
    main()
