from pathlib import Path
import numpy as np
import pandas as pd
import trimesh

from .schema import SampleRecord


def load_manifest(path: str | Path) -> list[SampleRecord]:
    df = pd.read_csv(path)
    records = []

    for _, row in df.iterrows():
        records.append(
            SampleRecord(
                sample_id=str(row["sample_id"]),
                dataset=str(row["dataset"]),
                case=str(row["case"]),
                method=str(row["method"]),
                phase0_run_id=str(row["phase0_run_id"]),
                pred_hand_mesh=Path(row["pred_hand_mesh"]),
                pred_object_mesh=Path(row["pred_object_mesh"]),
                gt_hand_mesh=Path(row["gt_hand_mesh"]),
                gt_object_mesh=Path(row["gt_object_mesh"]),
                align_npz=Path(row["align_npz"]),
                notes=str(row.get("notes", "")),
            )
        )

    return records


def load_geometry(path: str | Path):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Missing geometry: {path}")

    geom = trimesh.load(path, process=False)

    if isinstance(geom, trimesh.Scene):
        geom = trimesh.util.concatenate(tuple(geom.geometry.values()))

    if not hasattr(geom, "vertices"):
        raise ValueError(f"Geometry has no vertices: {path}")

    return geom


def load_similarity_transform(path: str | Path):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Missing alignment transform: {path}")

    data = np.load(path, allow_pickle=True)

    scale = None
    for k in ["scale", "sim_scale", "s"]:
        if k in data:
            scale = float(np.asarray(data[k]).reshape(-1)[0])
            break

    R = None
    for k in ["R", "rot", "rotation"]:
        if k in data:
            R = np.asarray(data[k], dtype=np.float64).reshape(3, 3)
            break

    t = None
    for k in ["t", "trans", "translation"]:
        if k in data:
            t = np.asarray(data[k], dtype=np.float64).reshape(3)
            break

    if scale is None or R is None or t is None:
        raise KeyError(
            f"{path} must contain scale/sim_scale/s, R/rot/rotation, and t/trans/translation. "
            f"Found keys: {list(data.keys())}"
        )

    return scale, R, t, list(data.keys())
