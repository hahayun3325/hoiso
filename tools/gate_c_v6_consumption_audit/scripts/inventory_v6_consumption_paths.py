#!/usr/bin/env python3
"""Read-only inventory of the accepted v6 hand/keypoint consumption path.

The script does not modify the repository or case artifacts. It searches source,
configuration, logs, and case outputs for evidence showing which hand
representation actually entered each accepted F3/F3.1/F3.3/F3.4/Gate-D term.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator

TEXT_EXTENSIONS = {
    ".py", ".sh", ".bash", ".zsh", ".env", ".yaml", ".yml", ".json",
    ".toml", ".ini", ".cfg", ".md", ".txt", ".csv", ".log",
}

SOURCE_PATTERNS: dict[str, re.Pattern[str]] = {
    "saved_2d_target": re.compile(r"mano_2d_kps|keypoints_2d|pred_keypoints_2d", re.I),
    "saved_3d_target": re.compile(r"mano_3d_kps|pred_keypoints_3d", re.I),
    "canonical_wrapper_joints": re.compile(
        r"mano_output\.joints|extra_joints_idxs|joint_map|J_regressor|joint_regressor_extra",
        re.I,
    ),
    "mesh_helper_joints": re.compile(
        r"mano_vert_to_3dkps|mesh[_-]?derived[_-]?joints|joints_from_mano_mesh",
        re.I,
    ),
    "direct_fingertip_vertices": re.compile(
        r"TIP_IDS|FINGERTIP_IDX|target_tip_ids|thumb\s*[:=]\s*744|index\s*[:=]\s*320|"
        r"middle\s*[:=]\s*443|ring\s*[:=]\s*554|pinky\s*[:=]\s*671|"
        r"\b744\b.*\b320\b.*\b443\b|\b320\b.*\b443\b",
        re.I,
    ),
    "f3_stage": re.compile(r"FOHO_F3_|F3_anchored|F3_STAGE1|f3_optimizer", re.I),
    "f31_stage": re.compile(r"FOHO_F3_1|F3_1_|rotation_delta_hand", re.I),
    "f33_f34_stage": re.compile(r"F3_3|F3\.3|F3_4|F3\.4|contact_place", re.I),
    "gate_d_stage": re.compile(r"GATE_D|Gate_D|root_cleanup|oriented_nearest_surface", re.I),
    "gradient_or_optimizer": re.compile(
        r"backward\(|optimizer\.step|AdamW?\(|requires_grad|zero_grad\(|total_loss|hand_loss",
        re.I,
    ),
    "acceptance_or_selector": re.compile(
        r"selected_update|selection_reason|accept|reject|PASS_|HOLD_|decision|threshold",
        re.I,
    ),
    "projection": re.compile(
        r"perspective_projection|transform_points_screen|project|reprojection|L2d|keypoint.*loss",
        re.I,
    ),
    "contact": re.compile(r"contact_loss|screen_lid|target_vertex|target_points|tip.*target", re.I),
    "collision": re.compile(r"collision|penetration|signed_distance|oriented.*depth|SDF", re.I),
}

ARTIFACT_NAME_RE = re.compile(
    r"hamer|mano|hand|kps|keypoint|guidance|h2m|camera|fov|f3|f31|f3_1|f3_3|"
    r"f3_4|gate[_-]?d|contact|target|lineage|preflight|root_cleanup|decision|metrics|config",
    re.I,
)

SKIP_DIR_NAMES = {
    ".git", "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    "node_modules", "models", "checkpoints", "cache", ".cache",
}


@dataclass(frozen=True)
class SourceHit:
    category: str
    file: str
    line: int
    text: str


@dataclass(frozen=True)
class ArtifactRecord:
    root_role: str
    path: str
    size_bytes: int
    modified_utc: str
    sha256: str
    hash_status: str


def utc_iso(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def iter_text_files(root: Path, allowed_top_level: tuple[str, ...]) -> Iterator[Path]:
    for top in allowed_top_level:
        candidate = root / top
        if not candidate.exists():
            continue
        if candidate.is_file():
            yield candidate
            continue
        for dirpath, dirnames, filenames in os.walk(candidate):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIR_NAMES]
            base = Path(dirpath)
            for name in filenames:
                path = base / name
                if path.suffix.lower() in TEXT_EXTENSIONS:
                    try:
                        if path.stat().st_size <= 8 * 1024 * 1024:
                            yield path
                    except OSError:
                        continue


def collect_source_hits(repo: Path) -> list[SourceHit]:
    hits: list[SourceHit] = []
    for path in iter_text_files(
        repo,
        (
            "src", "scripts", "tools", "configs", "third_party_patches",
            "third_party/Hunyuan3D-2/hy3dgen/shapegen/pipelines.py",
            "third_party/estimator/hamer",
        ),
    ):
        try:
            lines = path.read_text(errors="replace").splitlines()
        except OSError:
            continue
        rel = str(path.relative_to(repo)) if path.is_relative_to(repo) else str(path)
        for idx, line in enumerate(lines, start=1):
            compact = line.strip()
            if not compact:
                continue
            for category, pattern in SOURCE_PATTERNS.items():
                if pattern.search(line):
                    hits.append(SourceHit(category, rel, idx, compact[:800]))
    return hits


def iter_artifact_files(root: Path) -> Iterator[Path]:
    if not root.exists():
        return
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIR_NAMES]
        base = Path(dirpath)
        for name in filenames:
            if ARTIFACT_NAME_RE.search(name) or ARTIFACT_NAME_RE.search(str(base)):
                yield base / name


def collect_artifacts(
    roots: list[tuple[str, Path]], max_hash_bytes: int
) -> list[ArtifactRecord]:
    records: list[ArtifactRecord] = []
    seen: set[Path] = set()
    for role, root in roots:
        if not root.exists():
            continue
        for path in iter_artifact_files(root):
            try:
                resolved = path.resolve()
                if resolved in seen or not path.is_file():
                    continue
                seen.add(resolved)
                stat = path.stat()
                if stat.st_size <= max_hash_bytes:
                    try:
                        digest = sha256_file(path)
                        status = "hashed"
                    except OSError as exc:
                        digest = ""
                        status = f"hash_error:{type(exc).__name__}"
                else:
                    digest = ""
                    status = "skipped_too_large"
                records.append(
                    ArtifactRecord(
                        root_role=role,
                        path=str(path),
                        size_bytes=stat.st_size,
                        modified_utc=utc_iso(stat.st_mtime),
                        sha256=digest,
                        hash_status=status,
                    )
                )
            except OSError:
                continue
    records.sort(key=lambda item: (item.root_role, item.path))
    return records


def write_tsv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, object]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--v6-case-root", type=Path, required=True)
    parser.add_argument("--v6-run-root", type=Path, required=True)
    parser.add_argument("--v3-case-root", type=Path)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--max-hash-mb", type=float, default=256.0)
    args = parser.parse_args()

    repo = args.repo.resolve()
    v6_case_root = args.v6_case_root.resolve()
    v6_run_root = args.v6_run_root.resolve()
    v3_case_root = args.v3_case_root.resolve() if args.v3_case_root else None
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    missing = [
        str(path)
        for path in (repo, v6_case_root, v6_run_root)
        if not path.exists()
    ]
    if missing:
        print("[HOLD] required roots are missing:")
        for item in missing:
            print(f"  {item}")
        return 1

    source_hits = collect_source_hits(repo)
    roots: list[tuple[str, Path]] = [
        ("v6_case", v6_case_root),
        ("v6_run", v6_run_root),
    ]
    if v3_case_root and v3_case_root.exists():
        roots.append(("v3_case", v3_case_root))
    artifacts = collect_artifacts(
        roots, max_hash_bytes=int(args.max_hash_mb * 1024 * 1024)
    )

    write_tsv(
        out_dir / "source_hits.tsv",
        ["category", "file", "line", "text"],
        (asdict(item) for item in source_hits),
    )
    write_tsv(
        out_dir / "artifact_inventory.tsv",
        [
            "root_role", "path", "size_bytes", "modified_utc", "sha256",
            "hash_status",
        ],
        (asdict(item) for item in artifacts),
    )

    counts: dict[str, int] = {}
    for hit in source_hits:
        counts[hit.category] = counts.get(hit.category, 0) + 1

    likely_non_discriminating = (
        counts.get("direct_fingertip_vertices", 0) > 0
        and counts.get("contact", 0) > 0
    )
    summary = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "repo": str(repo),
        "v6_case_root": str(v6_case_root),
        "v6_run_root": str(v6_run_root),
        "v3_case_root": str(v3_case_root) if v3_case_root else None,
        "source_hit_counts": counts,
        "artifact_count": len(artifacts),
        "preliminary_warning": (
            "Direct fingertip/contact evidence is present. The accepted v6 result "
            "may be representation-invariant at the fingertips; do not treat it as "
            "proof of canonical-versus-mesh internal-joint consumption until the "
            "gradient/selector/acceptance path is manually confirmed."
            if likely_non_discriminating
            else "No automatic conclusion. Complete the manual loss-input manifest."
        ),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")

    md_lines = [
        "# v6 consumption-path inventory",
        "",
        f"Generated: `{summary['generated_utc']}`",
        "",
        "## Roots",
        "",
        f"- Repository: `{repo}`",
        f"- v6 case: `{v6_case_root}`",
        f"- v6 run: `{v6_run_root}`",
        f"- v3 case: `{v3_case_root}`" if v3_case_root else "- v3 case: not supplied",
        "",
        "## Source-hit counts",
        "",
    ]
    for key in sorted(counts):
        md_lines.append(f"- `{key}`: {counts[key]}")
    md_lines += [
        "",
        "## Preliminary warning",
        "",
        summary["preliminary_warning"],
        "",
        "This inventory is not the decision. Review `source_hits.tsv`, trace each",
        "accepted F3/F3.1/F3.3/F3.4/Gate-D term to its exact tensor producer,",
        "and fill `v6_loss_input_manifest.csv` before running the classifier.",
    ]
    (out_dir / "summary.md").write_text("\n".join(md_lines) + "\n")

    print(f"[PASS] SOURCE_HITS={out_dir / 'source_hits.tsv'}")
    print(f"[PASS] ARTIFACT_INVENTORY={out_dir / 'artifact_inventory.tsv'}")
    print(f"[PASS] SUMMARY={out_dir / 'summary.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
