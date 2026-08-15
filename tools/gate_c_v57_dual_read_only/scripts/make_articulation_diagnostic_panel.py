from __future__ import annotations

import argparse
from pathlib import Path
import json

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image


def draw(ax, image, target, zero, predicted, title):
    if image is not None:
        ax.imshow(image)
    ax.scatter(target[:, 0], target[:, 1], marker="x", label="target")
    ax.scatter(zero[:, 0], zero[:, 1], marker="o", facecolors="none", label="zero")
    if predicted is not None:
        ax.scatter(predicted[:, 0], predicted[:, 1], marker="+", label="linear prediction")
        for a, b in zip(zero, predicted):
            ax.plot([a[0], b[0]], [a[1], b[1]], linewidth=0.6)
    ax.set_title(title)
    ax.set_aspect("equal")
    if image is None:
        ax.invert_yaxis()
    ax.legend(fontsize=7)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preflight-dir", required=True)
    ap.add_argument("--analysis-dir", required=True)
    ap.add_argument("--image", default="")
    ap.add_argument("--blocks", nargs="*", default=["active_articulation", "translation_plus_active", "all_articulation_upper_bound"])
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    pre = Path(args.preflight_dir)
    ana = Path(args.analysis_dir)
    target = np.load(pre / "target_keypoints.npy")
    zero = np.load(pre / "zero_projection.npy")
    image = Image.open(args.image).convert("RGB") if args.image else None
    panels = [("zero", None)]
    for b in args.blocks:
        p = ana / f"predicted_keypoints__{b}.npy"
        if p.is_file():
            panels.append((b, np.load(p)))
    fig, axes = plt.subplots(1, len(panels), figsize=(5 * len(panels), 5), squeeze=False)
    for ax, (name, pred) in zip(axes[0], panels):
        draw(ax, image, target, zero, pred, name)
    fig.tight_layout()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=180, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
