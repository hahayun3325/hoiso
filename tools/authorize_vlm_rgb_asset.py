from pathlib import Path
import hashlib
import json
import sys


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_env(path):
    result = {}
    for line in Path(path).read_text().splitlines():
        if not line.startswith("export ") or "=" not in line:
            continue
        key, raw = line[7:].split("=", 1)
        try:
            result[key] = json.loads(raw)
        except Exception:
            result[key] = raw.strip("'\"")
    return result


def write_env(path, values):
    lines = [
        "export " + key + "=" + json.dumps(str(value))
        for key, value in values.items()
    ]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines) + "\n")


def main():
    if len(sys.argv) != 7:
        print("[HOLD] RGB_ROUTER_ARGUMENTS_INVALID")
        return

    response_path = Path(sys.argv[1])
    guard_path = Path(sys.argv[2])
    rgb_manifest_path = Path(sys.argv[3])
    rgb_path = Path(sys.argv[4])
    expected_candidate = sys.argv[5]
    auth_path = Path(sys.argv[6])

    required = [
        response_path,
        guard_path,
        rgb_manifest_path,
        rgb_path,
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        write_env(
            auth_path,
            {
                "VLM_INPAINT_AUTHORIZED": "0",
                "VLM_INPAINT_AUTH_REASON":
                    "missing_files:" + ",".join(missing),
                "VLM_INPAINT_PREFERRED_IMAGE": "",
            },
        )
        print("[HOLD] RGB_AUTHORIZATION_INPUT_MISSING=" + str(auth_path))
        return

    try:
        response = json.loads(response_path.read_text())
        guard = read_env(guard_path)
        rgb_manifest = json.loads(rgb_manifest_path.read_text())
    except Exception as error:
        write_env(
            auth_path,
            {
                "VLM_INPAINT_AUTHORIZED": "0",
                "VLM_INPAINT_AUTH_REASON":
                    "parse_error:" + type(error).__name__,
                "VLM_INPAINT_PREFERRED_IMAGE": "",
            },
        )
        print("[HOLD] RGB_AUTHORIZATION_PARSE_FAILED=" + str(auth_path))
        return

    decision = str(response.get("decision", "")).strip().lower()
    recommendation = response.get("authorization_recommendation", {})
    if not isinstance(recommendation, dict):
        recommendation = {}

    preferred_value = response.get("preferred_image_for_hunyuan")
    if preferred_value is None:
        preferred_value = recommendation.get(
            "preferred_image_for_hunyuan",
            "",
        )
    preferred = str(preferred_value).strip()

    authorized = response.get("authorize_for_hunyuan")
    if authorized is None:
        authorized = recommendation.get("authorize_hunyuan")

    checks = {
        "provenance":
            guard.get("VLM_RGB_RESPONSE_PROVENANCE") == "1",
        "candidate":
            response.get("candidate_id") == expected_candidate,
        "manifest_candidate":
            rgb_manifest.get("candidate_id") == expected_candidate,
        "rgb_hash":
            rgb_manifest.get("hunyuan_input_rgb_sha256")
            == digest(rgb_path),
    }

    authorized = (
        all(checks.values())
        and decision == "pass"
        and authorized is True
        and Path(preferred).name == rgb_path.name
    )

    if authorized:
        reason = "pass_exact_rgb"
        selected = str(rgb_path.resolve())
    elif decision == "reject" and all(checks.values()):
        reason = "vlm_reject"
        selected = ""
    else:
        failed = [name for name, passed in checks.items() if not passed]
        if not failed:
            failed = ["decision_or_preferred_image"]
        reason = "failed_checks:" + ",".join(failed)
        selected = ""

    write_env(
        auth_path,
        {
            "VLM_INPAINT_AUTHORIZED": "1" if authorized else "0",
            "VLM_INPAINT_AUTH_REASON": reason,
            "VLM_INPAINT_PREFERRED_IMAGE": selected,
            "VLM_INPAINT_AUTHORIZED_SHA256":
                digest(rgb_path) if authorized else "",
            "VLM_INPAINT_CANDIDATE_ID": expected_candidate,
        },
    )

    label = "PASS" if authorized else "HOLD"
    print(
        f"[{label}] VLM_RGB_ASSET_AUTHORIZATION="
        f"{auth_path} reason={reason}"
    )


if __name__ == "__main__":
    main()
