"""Align Hunyuan HOI mesh to MoGe mesh and write transforms."""

from __future__ import annotations

import argparse
import os

from pathlib import Path
from foho.case_artifacts import mesh_case_id


def _alignment_pairs(hunyuan_mesh_dir: str, moge_out_dir: str):
    meshes = sorted(Path(hunyuan_mesh_dir).glob("*_hoi_mesh.ply"))
    if not meshes:
        raise FileNotFoundError(f"No Hunyuan HOI meshes found in {hunyuan_mesh_dir}")
    pairs = []
    missing = []
    for source in meshes:
        case = mesh_case_id(source)
        moge_dir = Path(moge_out_dir) / f"{case}_cropped_hoi"
        target = next((moge_dir / name for name in ("mesh.ply", "pointcloud.ply", "mesh.glb")
                       if (moge_dir / name).is_file() and (moge_dir / name).stat().st_size > 0), None)
        if not source.is_file() or source.stat().st_size == 0:
            missing.append(f"{case}: Hunyuan mesh is empty or not a file ({source})")
        elif target is None:
            missing.append(f"{case}: no nonempty MoGe mesh/pointcloud in {moge_dir}")
        else:
            pairs.append((source, target))
    if missing:
        raise FileNotFoundError("Incomplete H2M inputs; no alignment started: " + "; ".join(missing))
    return pairs


def run(hunyuan_mesh_dir: str, moge_out_dir: str, h2m_rt_dir: str) -> None:
    pairs = _alignment_pairs(hunyuan_mesh_dir, moge_out_dir)
    from foho.alignment.mesh_align import align_meshes_impl
    Path(h2m_rt_dir).mkdir(parents=True, exist_ok=True)
    for source, target in pairs:
        align_meshes_impl(
            source_mesh_path=str(source),
            target_mesh_path=str(target),
            transform_path=os.path.join(h2m_rt_dir, source.stem),
            transformed_mesh_path=None,
            fixed_scale=False,
            outliers=0.2,
            test_rotations=False,
            test_reflections=False,
            on_surface=False,
            iterations_coarse=50,
            count_source_coarse=1000,
            count_target_coarse=5000,
            iterations_fine=100,
            count_source_fine=5000,
            count_target_fine=10000,
            min_scale=0.7,
            max_scale=3.0,
            plot=False,
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hunyuan_mesh_dir", required=True)
    parser.add_argument("--moge_out_dir", required=True)
    parser.add_argument("--h2m_rt_dir", required=True)
    args = parser.parse_args()

    run(
        hunyuan_mesh_dir=args.hunyuan_mesh_dir,
        moge_out_dir=args.moge_out_dir,
        h2m_rt_dir=args.h2m_rt_dir,
    )


if __name__ == "__main__":
    main()
