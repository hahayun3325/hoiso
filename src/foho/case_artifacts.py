"""Filename contract for the image -> geometry -> H2M handoff.

Known artifact suffixes are reserved. Case IDs may contain underscores and "hoi".
Multiple inputs for one output are rejected; views must be selected upstream.
"""
from pathlib import Path
import re

_IMAGE_SUFFIX = re.compile(r"(?:_cropped_hoi(?:_wo_bckg)?(?:_(?:0|1|True|False))?|_occ_obj)$")

def image_case_id(path):
    stem = Path(path).stem
    case = _IMAGE_SUFFIX.sub("", stem)
    if not case or case in (".", ".."):
        raise ValueError(f"Empty case ID in image: {path}")
    return case

def mesh_case_id(path):
    stem = Path(path).stem
    if not stem.endswith("_hoi_mesh") or not stem[:-9]:
        raise ValueError(f"Expected <case>_hoi_mesh.ply: {path}")
    return stem[:-9]

def unique_image_cases(paths):
    """Return sorted (case, path) pairs, rejecting ambiguous case ownership."""
    result = []
    seen = {}
    for path in sorted(map(Path, paths)):
        if not path.is_file():
            raise FileNotFoundError(f"Image is not a file: {path}")
        case = image_case_id(path)
        if case in seen:
            raise ValueError(f"Multiple images for case {case}: {seen[case]} and {path}")
        seen[case] = path
        result.append((case, path))
    if not result:
        raise FileNotFoundError("No input images found")
    return result
