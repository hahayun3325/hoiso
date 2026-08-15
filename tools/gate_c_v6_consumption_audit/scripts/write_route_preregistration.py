#!/usr/bin/env python3
"""Write a non-authorizing preregistration stub from the v6 route decision."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROUTE_TEXT = {
    "V6_DISCRIMINATES_CANONICAL_JOINT_CONSUMPTION": """## Proposed next experiment: canonical-joint adapter zero update

Purpose: reproduce the source-faithful carried canonical joints in the live Gate-C
loss without changing the immutable v3 target.

Allowed now:
- create a new versioned adapter module;
- unit-test it against saved canonical joints;
- run zero-update projection identity.

Not allowed now:
- hand movement;
- MANO articulation;
- object movement;
- contact/collision optimization;
- C2, F3.4, or Gate D.

Advance only when source-derived and adapter-derived 21-joint projections agree
within preregistered deterministic tolerances and the object hash is unchanged.
""",
    "V6_DISCRIMINATES_MESH_HELPER_JOINT_CONSUMPTION": """## Proposed next experiment: same-run physical-hand candidate audit

Purpose: determine whether the selected v3 HaMeR candidate is the physical upper
hand under the frozen mesh-helper contract.

Allowed now:
- inventory same-run candidates, handedness, crop, confidence, and raster affine;
- reproject each candidate into the exact target raster;
- compute source-faithful keypoint and silhouette diagnostics;
- optional indexed VLM semantic review after deterministic gates.

Not allowed now:
- target rewrite;
- reflection;
- MANO articulation;
- object movement;
- C2, F3.4, or Gate D.
""",
    "V6_MIXED_JOINT_CONSUMPTION_REQUIRES_TERM_SPLIT": """## Proposed next experiment: paired zero-update term split

Purpose: separate every active keypoint/contact/selector term by producer and test
canonical-versus-mesh-helper consumption without moving geometry.

Create two fresh zero-update branches with identical inputs, target, camera, and
object. Change only the predicted-joint producer for the disputed term. Do not
compare a historical target against a silently redefined producer.
""",
    "V6_FUNCTIONAL_CONTROL_ONLY_NONDISCRIMINATING": """## Proposed next experiment: source-faithful producer identity control

The accepted v6 result is a useful contact/export control but does not adjudicate
the disputed internal 21-joint source.

Run only:
1. H0/H1 source identity;
2. H2 exact-raster projection identity;
3. a paired zero-update canonical-versus-mesh-helper projection report if needed.

Do not replay the full v6 optimizer merely to create a discriminating result.
Do not modify the v3 helper until this producer identity is resolved.
""",
}

DEFAULT_HOLD = """## Proposed next action: recover evidence or close

The accepted v6 consumption path is not reconstructable from the current evidence.
Recover the missing source, configuration, target, candidate, and artifact hashes.
If that cannot be done, create one clean versioned control run or close the branch
as a contained placement failure. No geometry movement is authorized.
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--decision", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    try:
        data = json.loads(args.decision.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[HOLD] cannot read decision: {exc}")
        return 1

    route = str(data.get("route", ""))
    body = ROUTE_TEXT.get(route, DEFAULT_HOLD)
    text = f"""# Gate-C next-route preregistration stub

**Source decision:** `{args.decision.resolve()}`
**Route:** `{route}`

This document is preparatory. It does not authorize an optimizer launch.

{body}
## Frozen acceptance policy

- v3 saved target remains immutable;
- normalized RMSE <= 0.50;
- normalized p95 <= 0.75;
- trust-region fraction < 0.98;
- proper chirality only;
- exact target raster and crop contract;
- object vertices, topology, lid/base relation, and camera hashes unchanged;
- no C2, F3.4, or Gate D before Gate C passes.
"""
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text)
    print(f"[PASS] PREREGISTRATION_STUB={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
