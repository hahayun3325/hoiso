from pathlib import Path
import argparse
import trimesh
import numpy as np


def load_mesh(path):
    path = Path(path)
    mesh = trimesh.load(path, process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    return mesh


def summarize(name, path):
    path = Path(path)
    if not path.exists():
        print(f"[MISSING] {name}: {path}")
        return None

    mesh = load_mesh(path)
    comps = mesh.split(only_watertight=False)
    faces = np.array([len(c.faces) for c in comps], dtype=float)
    largest = float(faces.max() / max(len(mesh.faces), 1)) if len(faces) else 0.0

    center = mesh.vertices.mean(axis=0)
    bounds = mesh.bounds

    print(f"\n===== {name} =====")
    print("path:", path)
    print("verts:", len(mesh.vertices))
    print("faces:", len(mesh.faces))
    print("components:", len(comps))
    print("largest_face_ratio:", largest)
    print("fragmentation_score:", (len(comps) - 1) + (1.0 - largest))
    print("center:", center.tolist())
    print("bounds_min:", bounds[0].tolist())
    print("bounds_max:", bounds[1].tolist())

    return mesh


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run_id", required=True)
    args = ap.parse_args()

    home = Path.home()
    run = home / "foho_phase0/runs" / args.run_id
    debug = home / "foho_phase0/inspection/oakink_000" / args.run_id / "internal_selector_debug"

    before = debug / "selector_candidate_before_phase42.ply"
    after = debug / "selector_candidate_phase42_before_joint_true.ply"
    if not after.exists():
        after = debug / "selector_candidate_phase42_before_joint.ply"
    selected = debug / "selector_selected_before_joint.ply"

    final_obj = run / "guidance_out/oakink_obj.ply"
    final_hand = run / "guidance_out/oakink_hand.ply"

    if not final_obj.exists():
        hits = sorted((run / "guidance_out").glob("*obj*.ply"))
        final_obj = hits[0] if hits else final_obj

    if not final_hand.exists():
        hits = sorted((run / "guidance_out").glob("*hand*.ply"))
        final_hand = hits[0] if hits else final_hand

    m_before = summarize("candidate_before_phase42", before)
    m_after = summarize("candidate_phase42_before_joint", after)
    m_selected = summarize("selector_selected_before_joint", selected)
    m_obj = summarize("final_obj", final_obj)
    m_hand = summarize("final_hand", final_hand)

    if m_obj is not None and m_hand is not None:
        c_obj = m_obj.vertices.mean(axis=0)
        c_hand = m_hand.vertices.mean(axis=0)
        print("\n===== final hand-object center distance =====")
        print(float(np.linalg.norm(c_obj - c_hand)))


if __name__ == "__main__":
    main()
