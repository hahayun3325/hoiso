from pathlib import Path
import hashlib
import json
import sys

def main():
    if len(sys.argv) < 6:
        print(
            '[HOLD] usage: guard_vlm_inpaint_response.py '
            'RESPONSE MANIFEST IMAGE CANDIDATE_ID GUARD_ENV'
        )
        return

    response_path = Path(sys.argv[1])
    manifest_path = Path(sys.argv[2])
    image_path = Path(sys.argv[3])
    expected_candidate_id = sys.argv[4]
    guard_path = Path(sys.argv[5])
    guard_path.parent.mkdir(parents=True, exist_ok=True)

    guard_ok = False
    reason = 'uninitialized'

    try:
        missing = [
            str(path)
            for path in (response_path, manifest_path, image_path)
            if not path.is_file()
        ]
        if missing:
            reason = 'missing_files:' + ','.join(missing)
        else:
            response = json.loads(response_path.read_text())
            manifest = json.loads(manifest_path.read_text())
            auth = response.get('authorization_recommendation', {})
            decision = str(response.get('decision', '')).lower()
            preferred = str(auth.get('preferred_image_for_hunyuan', '')).strip()
            authorize = bool(auth.get('authorize_hunyuan', False))

            checks = {
                'case_id': response.get('case_id') == 'alapuse02v3n60',
                'candidate_id': response.get('candidate_id') == expected_candidate_id,
                'manifest_candidate_id': manifest.get('candidate_id') == expected_candidate_id,
                'image_hash': (
                    manifest.get('hunyuan_input_sha256')
                    == hashlib.sha256(image_path.read_bytes()).hexdigest()
                ),
                'known_decision': decision in {'pass', 'reject'},
            }

            if decision == 'pass':
                checks['pass_authorization_consistent'] = (
                    authorize
                    and preferred == image_path.name
                )
            elif decision == 'reject':
                checks['reject_authorization_consistent'] = (
                    not authorize
                    and preferred in {'', 'none'}
                )

            failed = [name for name, value in checks.items() if not value]
            guard_ok = not failed
            reason = 'pass' if guard_ok else 'failed_checks:' + ','.join(failed)
    except Exception as error:
        reason = f'guard_exception:{type(error).__name__}:{error}'

    guard_path.write_text(
        f"export VLM_INPAINT_RESPONSE_PROVENANCE={'1' if guard_ok else '0'}\n"
        f"export VLM_INPAINT_RESPONSE_PROVENANCE_REASON={json.dumps(reason)}\n"
    )
    print(
        f"[{'PASS' if guard_ok else 'HOLD'}] "
        f"VLM_RESPONSE_PROVENANCE_GUARD={guard_path} reason={reason}"
    )

if __name__ == '__main__':
    main()
