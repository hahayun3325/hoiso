#!/usr/bin/env python3
from copy import deepcopy
from pathlib import Path
import json
import subprocess
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
)


def run(command):
    return subprocess.run(command, text=True, capture_output=True)


def response_for(candidate_ids, mode):
    reviews = []
    for index, candidate_id in enumerate(candidate_ids):
        review = {
            "candidate_id": candidate_id,
            **{field: True for field in SEMANTIC_FIELDS},
            "safe_for_hunyuan": True,
            "confidence": 0.95 - index * 0.01,
            "failure_reasons": [],
        }
        reviews.append(review)

    response = {
        "schema_version": "auto_v2_candidate_critic_v1",
        "case_id": "alapuse02v3n60",
        "uncertain": False,
        "candidate_reviews": reviews,
        "notes": "synthetic fixture only",
    }
    if mode == "all_rejected":
        for review in reviews:
            review["base_complete"] = False
            review["safe_for_hunyuan"] = False
            review["failure_reasons"] = ["synthetic_rejection"]
    elif mode == "uncertain":
        response["uncertain"] = True
    elif mode == "unknown_id":
        reviews[-1]["candidate_id"] = "c99_unknown"
    return response


def provenance_passed(path):
    return (
        path.is_file()
        and 'VLM_RGB_RESPONSE_PROVENANCE="1"' in path.read_text()
    )


def provenance_held(path):
    return (
        path.is_file()
        and 'VLM_RGB_RESPONSE_PROVENANCE="0"' in path.read_text()
    )


def main():
    if len(sys.argv) != 7:
        print("[HOLD] AUTO_V2_BRIDGE_TEST_ARGUMENTS_INVALID")
        return

    selector = Path(sys.argv[1])
    bridge = Path(sys.argv[2])
    bank_path = Path(sys.argv[3])
    gate_path = Path(sys.argv[4])
    query_path = Path(sys.argv[5])
    root = Path(sys.argv[6])

    required = (selector, bridge, bank_path, gate_path, query_path)
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        print("[HOLD] AUTO_V2_BRIDGE_TEST_INPUT_MISSING=" + ",".join(missing))
        return
    if root.exists():
        print(f"[HOLD] AUTO_V2_BRIDGE_TEST_ROOT_EXISTS={root}")
        return

    root.mkdir(parents=True)
    bank = json.loads(bank_path.read_text())
    query = json.loads(query_path.read_text())
    candidate_ids = [
        str(item["candidate_id"]) for item in bank.get("candidates", [])
    ]
    results = {}

    def write_response(name, mode):
        case_dir = root / name
        case_dir.mkdir()
        path = case_dir / "response.json"
        path.write_text(json.dumps(response_for(candidate_ids, mode), indent=2) + "\n")
        return case_dir, path

    valid_dir, valid_response = write_response("01_valid_selected", "valid")
    valid_selection_dir = valid_dir / "selection"
    selected_run = run([
        sys.executable,
        str(selector),
        str(bank_path),
        str(valid_response),
        str(valid_selection_dir),
    ])
    valid_selection = valid_selection_dir / "selection.json"
    if valid_selection.is_file():
        selection = json.loads(valid_selection.read_text())
        selected_id = selection.get("selected_candidate_id")
        bank_item = next(
            item for item in bank["candidates"]
            if item["candidate_id"] == selected_id
        )
        guard = valid_dir / "guard.env"
        run([
            sys.executable,
            str(bridge),
            str(bank_path),
            str(gate_path),
            str(query_path),
            str(valid_response),
            str(valid_selection),
            str(bank_item["manifest"]),
            str(bank_item["hunyuan_input_rgb"]),
            str(valid_dir / "adapted_response.json"),
            str(valid_dir / "rgb_manifest.json"),
            str(guard),
        ])
        results["valid_selected_candidate"] = provenance_passed(guard)
    else:
        results["valid_selected_candidate"] = False

    reject_dir, reject_response = write_response("02_all_rejected", "all_rejected")
    reject_selection_dir = reject_dir / "selection"
    run([
        sys.executable,
        str(selector),
        str(bank_path),
        str(reject_response),
        str(reject_selection_dir),
    ])
    reject_record = reject_selection_dir / "selection.json"
    results["all_rejected"] = (
        reject_record.is_file()
        and json.loads(reject_record.read_text()).get("decision")
        == "hold_no_eligible_candidate"
    )

    uncertain_dir, uncertain_response = write_response("03_uncertain", "uncertain")
    uncertain_run = run([
        sys.executable,
        str(selector),
        str(bank_path),
        str(uncertain_response),
        str(uncertain_dir / "selection"),
    ])
    results["uncertain_response"] = (
        "[HOLD] CRITIC_RESPONSE_UNCERTAIN=true" in uncertain_run.stdout
    )

    unknown_dir, unknown_response = write_response("04_unknown_id", "unknown_id")
    unknown_run = run([
        sys.executable,
        str(selector),
        str(bank_path),
        str(unknown_response),
        str(unknown_dir / "selection"),
    ])
    results["unknown_candidate_id"] = (
        "[HOLD] CRITIC_RESPONSE_VALIDATION=" in unknown_run.stdout
    )

    if valid_selection.is_file():
        selection = json.loads(valid_selection.read_text())
        selected_id = selection["selected_candidate_id"]
        bank_item = next(
            item for item in bank["candidates"]
            if item["candidate_id"] == selected_id
        )

        mismatch_dir = root / "05_selection_response_hash_mismatch"
        mismatch_dir.mkdir()
        mismatch_selection = mismatch_dir / "selection.json"
        altered = deepcopy(selection)
        altered["critic_response_sha256"] = "0" * 64
        mismatch_selection.write_text(json.dumps(altered, indent=2) + "\n")
        mismatch_guard = mismatch_dir / "guard.env"
        run([
            sys.executable,
            str(bridge),
            str(bank_path),
            str(gate_path),
            str(query_path),
            str(valid_response),
            str(mismatch_selection),
            str(bank_item["manifest"]),
            str(bank_item["hunyuan_input_rgb"]),
            str(mismatch_dir / "adapted.json"),
            str(mismatch_dir / "rgb_manifest.json"),
            str(mismatch_guard),
        ])
        results["selection_response_hash_mismatch"] = provenance_held(mismatch_guard)

        manifest_dir = root / "06_manifest_hash_mismatch"
        manifest_dir.mkdir()
        manifest_query = manifest_dir / "query.json"
        altered_query = deepcopy(query)
        for item in altered_query["candidate_assets"]:
            if item["candidate_id"] == selected_id:
                item["manifest_sha256"] = "0" * 64
        manifest_query.write_text(json.dumps(altered_query, indent=2) + "\n")
        manifest_guard = manifest_dir / "guard.env"
        run([
            sys.executable,
            str(bridge),
            str(bank_path),
            str(gate_path),
            str(manifest_query),
            str(valid_response),
            str(valid_selection),
            str(bank_item["manifest"]),
            str(bank_item["hunyuan_input_rgb"]),
            str(manifest_dir / "adapted.json"),
            str(manifest_dir / "rgb_manifest.json"),
            str(manifest_guard),
        ])
        results["manifest_hash_mismatch"] = provenance_held(manifest_guard)

        rgb_dir = root / "07_rgb_hash_mismatch"
        rgb_dir.mkdir()
        rgb_query = rgb_dir / "query.json"
        altered_query = deepcopy(query)
        for item in altered_query["candidate_assets"]:
            if item["candidate_id"] == selected_id:
                item["hunyuan_input_rgb_sha256"] = "0" * 64
        rgb_query.write_text(json.dumps(altered_query, indent=2) + "\n")
        rgb_guard = rgb_dir / "guard.env"
        run([
            sys.executable,
            str(bridge),
            str(bank_path),
            str(gate_path),
            str(rgb_query),
            str(valid_response),
            str(valid_selection),
            str(bank_item["manifest"]),
            str(bank_item["hunyuan_input_rgb"]),
            str(rgb_dir / "adapted.json"),
            str(rgb_dir / "rgb_manifest.json"),
            str(rgb_guard),
        ])
        results["rgb_hash_mismatch"] = provenance_held(rgb_guard)
    else:
        results["selection_response_hash_mismatch"] = False
        results["manifest_hash_mismatch"] = False
        results["rgb_hash_mismatch"] = False

    report = {
        "schema_version": "auto_v2_bridge_synthetic_test_report_v1",
        "case_id": "alapuse02v3n60",
        "synthetic_only": True,
        "results": results,
        "all_passed": all(results.values()) and len(results) == 7,
    }
    report_path = root / "test_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    if report["all_passed"]:
        print(f"[PASS] AUTO_V2_BRIDGE_SYNTHETIC_TESTS={report_path}")
    else:
        failed = [name for name, value in results.items() if not value]
        print("[HOLD] AUTO_V2_BRIDGE_SYNTHETIC_TESTS=" + ",".join(failed))


if __name__ == "__main__":
    main()
