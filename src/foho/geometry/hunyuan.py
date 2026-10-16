"""Run Hunyuan HOI mesh generation."""

from __future__ import annotations

import argparse
import os
import sys
from typing import List
from pathlib import Path
import uuid

from foho.case_artifacts import unique_image_cases

from foho.configs import third_party_root

def _setup_sys_path(project_root: str) -> None:
    tp = third_party_root()
    hy3dgen_root = os.path.join(tp, "Hunyuan3D-2")
    sys.path.append(tp)
    sys.path.append(os.path.join(tp, "estimator"))
    sys.path.append(hy3dgen_root)
    sys.path.append(os.path.join(hy3dgen_root, "hy3dgen"))
    sys.path.append(project_root)


def _collect_images(image_dir: str) -> List[str]:
    return [
        os.path.join(image_dir, name)
        for name in sorted(os.listdir(image_dir))
        if name.lower().endswith((".png", ".jpg", ".jpeg"))
        and os.path.isfile(os.path.join(image_dir, name))
    ]


def _hunyuan_minimal_demo(image_list: List[str], save_path: str) -> None:
    cases = unique_image_cases(image_list)
    root = Path(save_path).resolve()
    pending = []
    for case, source in cases:
        target = root / f"{case}_hoi_mesh.ply"
        if target.is_symlink():
            raise ValueError(f"Mesh output is a symlink: {target}")
        if target.exists():
            if not target.is_file() or target.stat().st_size == 0:
                raise ValueError(f"Existing mesh output is not a nonempty file: {target}")
            print(f"{case} already exists, skipping")
        else:
            pending.append((case, source, target))
    if not pending:
        print("No new images to process.")
        return

    from PIL import Image
    import torch
    from hy3dgen.shapegen import (
        Hunyuan3DDiTFlowMatchingPipeline,
        FaceReducer,
        FloaterRemover,
        DegenerateFaceRemover,
    )

    root.mkdir(parents=True, exist_ok=True)
    pipeline = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained("tencent/Hunyuan3D-2")
    for case, source, target in pending:
        with Image.open(source) as opened:
            image = opened.convert("RGBA")
        try:
            image.putdata([
                (255, 255, 255, 0) if pixel[:3] == (255, 255, 255) else pixel
                for pixel in image.getdata()
            ])
            meshes = pipeline(
                image=image,
                num_inference_steps=30,
                mc_algo="mc",
                generator=torch.manual_seed(2025),
                multi_view=False,
            )
            if not isinstance(meshes, (list, tuple)) or len(meshes) != 1 or meshes[0] is None:
                raise ValueError(f"Expected exactly one Hunyuan mesh for case {case}")
            mesh = FloaterRemover()(meshes[0])
            mesh = DegenerateFaceRemover()(mesh)
            mesh = FaceReducer()(mesh)
            # A failed export stays visibly partial and is never mistaken for a mesh to reuse.
            partial = root / f".{case}.{uuid.uuid4().hex}.partial.ply"
            with partial.open("xb"):
                pass
            mesh.export(str(partial))
            if not partial.is_file() or partial.stat().st_size == 0:
                raise ValueError(f"Empty mesh export for case {case}")
            os.link(partial, target)  # Refuse a concurrently created destination.
            partial.unlink()
            print(f"Mesh saved with name {target}")
        finally:
            image.close()


def run(project_root: str, image_dir: str, save_dir: str) -> None:
    _setup_sys_path(project_root)
    image_list = _collect_images(image_dir)
    _hunyuan_minimal_demo(image_list, save_dir)
    print("Saved Hunyuan HOI meshes to", save_dir)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project_root", required=True)
    parser.add_argument("--image_dir", required=True)
    parser.add_argument("--save_dir", required=True)
    args = parser.parse_args()

    run(project_root=args.project_root, image_dir=args.image_dir, save_dir=args.save_dir)


if __name__ == "__main__":
    main()
