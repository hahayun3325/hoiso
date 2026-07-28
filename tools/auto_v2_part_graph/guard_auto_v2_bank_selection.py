#!/usr/bin/env python3
from pathlib import Path
import hashlib
import json
import sys


SEMANTIC_FIELDS = (
    "target_identity_preserved",
    "lid_complete",
    "base_complete",
    "hinge_preserved",
    "support_absent",
    "tabletop_absent",
    "hand_absent",
    "orientation_preserved",
    "safe_for_hunyuan",
)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_env(path, values):
    lines = [
        "export " + key + "=" + json.dumps(str(value))
        for key, value in values.items()
    ]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines) + "\n")


def hold(env_path, failed):
    reason = "failed_checks:" + ",".join(failed)
    write_env(
        env_path,
        {
            "VLM_RGB_RESPONSE_PROVENANCE": "0",
            "VLM_RGB_RESPONSE_PROVENANCE_REASON": reason,
            "VLM_RGB_RESPONSE_DECISION": "unknown",
        },
    )
    print(
        "[HOLD] AUTO_V2_BANK_SELECTION_PROVENANCE="
        + str(env_path)
        + " reason="
        + reason
    )


def main():
    if len(sys.argv) != 11:
        print("[HOLD] AUTO_V2_BANK_BRIDGE_ARGUMENTS_INVALID")
        return

    (
        bank_path,
        gate_path,
        query_path,
        response_path,
        selection_path,
        manifest_path,
        rgb_path,
        adapted_path,
        rgb_manifest_path,
        env_path,
    ) = (Path(value) for value in sys.argv[1:])

    inputs = (
        bank_path,
        gate_path,
        query_path,
        response_path,
        selection_path,
        manifest_path,
        rgb_path,
    )
    missing = [str(path) for path in inputs if not path.is_file()]
    if missing:
        hold(env_path, ["missing_files:" + "|".join(missing)])
        return

    if adapted_path.exists() or rgb_manifest_path.exists() or env_path.exists():
        print("[HOLD] AUTO_V2_BANK_BRIDGE_OUTPUT_EXISTS")
        return

    try:
        bank = json.loads(bank_path.read_text())
        gate = json.loads(gate_path.read_text())
        query = json.loads(query_path.read_text())
        response = json.loads(response_path.read_text().strip())
        selection = json.loads(selection_path.read_text())
        manifest = json.loads(manifest_path.read_text())
    except Exception as error:
        hold(env_path, ["json_error:" + type(error).__name__])
        return

    candidate_items = {
        str(item.get("candidate_id")): item
        for item in bank.get("candidates", [])
    }
    expected_ids = set(candidate_items)
    selected_id = str(selection.get("selected_candidate_id", ""))
    reviews = response.get("candidate_reviews", [])
    review_items = {
        str(item.get("candidate_id")): item
        for item in reviews
        if isinstance(item, dict)
    }
    query_assets = {
        str(item.get("candidate_id")): item
        for item in query.get("candidate_assets", [])
        if isinstance(item, dict)
    }

    prompt = query.get("prompt", {})
    panel = query.get("panel", {})
    bank_binding = query.get("candidate_bank", {})
    prompt_path = Path(prompt.get("path", ""))
    panel_path = Path(panel.get("path", ""))
    selected = candidate_items.get(selected_id, {})
    review = review_items.get(selected_id, {})
    query_asset = query_assets.get(selected_id, {})

    checks = {
        "bank_case": bank.get("case_id") == "alapuse02v3n60",
        "gate_case": gate.get("case_id") == "alapuse02v3n60",
        "query_schema":
            query.get("schema_version") == "auto_v2_blind_critic_query_v1",
        "query_case": query.get("case_id") == "alapuse02v3n60",
        "response_schema":
            response.get("schema_version") == "auto_v2_candidate_critic_v1",
        "response_case": response.get("case_id") == "alapuse02v3n60",
        "response_not_uncertain": response.get("uncertain") is False,
        "candidate_set_complete":
            expected_ids
            == set(query.get("candidate_ids", []))
            == set(review_items),
        "review_count_exact": len(reviews) == len(expected_ids),
        "selection_schema":
            selection.get("schema_version") == "auto_v2_selection_v1",
        "selection_case": selection.get("case_id") == "alapuse02v3n60",
        "selection_is_preselection":
            selection.get("decision")
            == "selected_for_existing_provenance_guard"
            and selection.get("authorize_hunyuan") is False,
        "selection_id_registered": selected_id in candidate_items,
        "selection_bank_hash":
            selection.get("bank_sha256") == digest(bank_path),
        "selection_response_hash":
            selection.get("critic_response_sha256") == digest(response_path),
        "gate_bank_hash": gate.get("bank_sha256") == digest(bank_path),
        "selected_deterministic_pass":
            selected.get("deterministic_gate_pass") is True
            and selected_id in set(gate.get("deterministic_pass_ids", [])),
        "selection_manifest_path":
            Path(selection.get("candidate_manifest", "")).resolve()
            == manifest_path.resolve(),
        "selection_rgb_path":
            Path(selection.get("candidate_rgb", "")).resolve()
            == rgb_path.resolve(),
        "selection_rgb_hash":
            selection.get("candidate_rgb_sha256") == digest(rgb_path),
        "manifest_candidate": manifest.get("candidate_id") == selected_id,
        "manifest_schema":
            manifest.get("schema_version")
            == "inpaint_fallback_candidate_v7_auto_part_graph",
        "manifest_rgb_path":
            Path(manifest.get("hunyuan_input_rgb", "")).resolve()
            == rgb_path.resolve(),
        "manifest_rgb_hash":
            manifest.get("hunyuan_input_rgb_sha256") == digest(rgb_path),
        "query_bank_hash":
            bank_binding.get("sha256") == digest(bank_path),
        "query_prompt_exists": prompt_path.is_file(),
        "query_panel_exists": panel_path.is_file(),
        "query_asset_set": set(query_assets) == expected_ids,
        "query_selected_manifest_hash":
            query_asset.get("manifest_sha256") == digest(manifest_path),
        "query_selected_rgb_hash":
            query_asset.get("hunyuan_input_rgb_sha256") == digest(rgb_path),
        "selected_review_matches_selection":
            selection.get("critic_review") == review,
        "selected_review_fields":
            bool(review)
            and all(review.get(field) is True for field in SEMANTIC_FIELDS),
        "selected_review_no_failures":
            isinstance(review.get("failure_reasons"), list)
            and not review.get("failure_reasons"),
    }

    try:
        checks["selected_confidence"] = (
            float(review.get("confidence")) >= 0.80
            and float(selection.get("critic_confidence")) >= 0.80
        )
    except (TypeError, ValueError):
        checks["selected_confidence"] = False

    if prompt_path.is_file():
        checks["query_prompt_hash"] = prompt.get("sha256") == digest(prompt_path)
    else:
        checks["query_prompt_hash"] = False
    if panel_path.is_file():
        checks["query_panel_hash"] = panel.get("sha256") == digest(panel_path)
    else:
        checks["query_panel_hash"] = False

    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        hold(env_path, failed)
        return

    adapted = {
        "schema_version": "auto_v2_candidate_scoped_adapter_v1",
        "case_id": "alapuse02v3n60",
        "candidate_id": selected_id,
        "decision": "pass",
        "authorize_for_hunyuan": True,
        "preferred_image_for_hunyuan": rgb_path.name,
        "confidence": float(review["confidence"]),
        "source_bank_critic_response": str(response_path),
        "source_bank_critic_response_sha256": digest(response_path),
        "source_selection": str(selection_path),
        "source_selection_sha256": digest(selection_path),
        "note":
            "Deterministic schema adaptation only; the exact-file router "
            "remains the authorization authority.",
    }
    rgb_manifest = {
        "schema_version": "auto_v2_exact_rgb_manifest_v1",
        "case_id": "alapuse02v3n60",
        "candidate_id": selected_id,
        "source_candidate_manifest": str(manifest_path),
        "source_candidate_manifest_sha256": digest(manifest_path),
        "hunyuan_input_rgb": str(rgb_path),
        "hunyuan_input_rgb_sha256": digest(rgb_path),
    }

    adapted_path.parent.mkdir(parents=True, exist_ok=True)
    rgb_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    adapted_path.write_text(json.dumps(adapted, indent=2) + "\n")
    rgb_manifest_path.write_text(json.dumps(rgb_manifest, indent=2) + "\n")
    write_env(
        env_path,
        {
            "VLM_RGB_RESPONSE_PROVENANCE": "1",
            "VLM_RGB_RESPONSE_PROVENANCE_REASON":
                "pass_auto_v2_bank_selection",
            "VLM_RGB_RESPONSE_DECISION": "pass",
            "VLM_RGB_RESPONSE_SHA256": digest(response_path),
            "VLM_RGB_QUERY_SHA256": digest(query_path),
            "VLM_RGB_IMAGE_SHA256": digest(rgb_path),
            "AUTO_V2_SELECTION_SHA256": digest(selection_path),
        },
    )
    print(f"[PASS] AUTO_V2_BANK_SELECTION_PROVENANCE={env_path}")
    print(f"[PASS] AUTO_V2_CANDIDATE_SCOPED_RESPONSE={adapted_path}")
    print(f"[PASS] AUTO_V2_EXACT_RGB_MANIFEST={rgb_manifest_path}")


if __name__ == "__main__":
    main()
