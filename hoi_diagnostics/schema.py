from dataclasses import dataclass
from pathlib import Path


@dataclass
class SampleRecord:
    sample_id: str
    dataset: str
    case: str
    method: str
    phase0_run_id: str
    pred_hand_mesh: Path
    pred_object_mesh: Path
    gt_hand_mesh: Path
    gt_object_mesh: Path
    align_npz: Path
    notes: str = ""
