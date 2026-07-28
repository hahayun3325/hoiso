from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import subprocess


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_env(path):
    values = {}
    for line in Path(path).read_text().splitlines():
        if line.startswith("export ") and "=" in line:
            key, raw = line[7:].split("=", 1)
            values[key] = json.loads(raw)
    return values


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--authorization-env", required=True)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument(
        "--worker",
        default="scripts/phase2_1/run_hunyuan_shape_dryrun.py",
    )
    parser.add_argument("--steps", type=int, default=30)
    parser.add_argument("--octree-resolution", type=int, default=384)
    parser.add_argument("--num-chunks", type=int, default=8000)
    parser.add_argument("--seed", type=int, default=1234)
    args = parser.parse_args()

    auth_path = Path(args.authorization_env)
    image_path = Path(args.image).resolve()
    output_path = Path(args.out)
    worker_path = Path(args.worker)

    required = [auth_path, image_path, worker_path]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        print("[HOLD] AUTHORIZED_HUNYUAN_INPUT_MISSING=" + ",".join(missing))
        return

    auth = read_env(auth_path)
    checks = {
        "authorized":
            auth.get("VLM_INPAINT_AUTHORIZED") == "1",
        "candidate":
            auth.get("VLM_INPAINT_CANDIDATE_ID")
            == args.candidate_id,
        "exact_path":
            auth.get("VLM_INPAINT_PREFERRED_IMAGE")
            == str(image_path),
        "exact_hash":
            auth.get("VLM_INPAINT_AUTHORIZED_SHA256")
            == digest(image_path),
        "output_absent": not output_path.exists(),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        print(
            "[HOLD] AUTHORIZED_HUNYUAN_BLOCKED="
            + ",".join(failed)
        )
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "python3",
        str(worker_path),
        "--image",
        str(image_path),
        "--out",
        str(output_path),
        "--steps",
        str(args.steps),
        "--octree-resolution",
        str(args.octree_resolution),
        "--num-chunks",
        str(args.num_chunks),
        "--seed",
        str(args.seed),
    ]
    trial = {
        "schema_version": "authorized_hunyuan_trial_v1",
        "candidate_id": args.candidate_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "authorization_env": str(auth_path),
        "authorization_env_sha256": digest(auth_path),
        "image": str(image_path),
        "image_sha256": digest(image_path),
        "output": str(output_path),
        "command": command,
    }
    trial_path = output_path.parent / "authorized_trial_spec.json"
    trial_path.write_text(json.dumps(trial, indent=2) + "\n")
    print(f"[PASS] AUTHORIZED_HUNYUAN_TRIAL_SPEC={trial_path}")

    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        print(
            "[HOLD] AUTHORIZED_HUNYUAN_WORKER_FAILED="
            + str(completed.returncode)
        )
    elif output_path.is_file() and output_path.stat().st_size > 0:
        print(f"[PASS] AUTHORIZED_HUNYUAN_OUTPUT={output_path}")
    else:
        print(f"[HOLD] AUTHORIZED_HUNYUAN_OUTPUT_MISSING={output_path}")


if __name__ == "__main__":
    main()
