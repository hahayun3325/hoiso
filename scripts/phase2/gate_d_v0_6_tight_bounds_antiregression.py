"""
Gate D v0.5 -- two-stage, ArtHOI-informed rigid-pose repair.

Structural changes from v0.1-v0.4, based on reading ArtHOI's actual
contact/penetration code (hrse/ho_align.py, hrse/losses.py):

  1. TWO STAGES, not one combined loss:
       Stage A (contact fit): optimize rigid pose using ONLY a contact
         attraction term, restricted to thumb+index (matching Gate B's
         "upper hand -> screen_lid" hypothesis and ArtHOI's
         active_fingers pattern), against a SMALL fixed target region
         on screen_lid (not the whole part).
       Stage B (penetration cleanup): freeze Stage A's result as an
         anchor, add a penetration term (reversed direction: object-
         vertices-inside-hand, since MANO is always watertight) plus a
         SOFT quadratic anchor loss (not a hard cliff like v0.4's).
  2. Small, fixed vertex subsets throughout (speed fix from prior round).
  3. Hard wall-clock budget -- abort and report if exceeded, rather than
     letting it run indefinitely (v0.4 cost 1.5h for a worse result).

Pre-registered decision rule (apply after running, do not tune further):
  PASS only if: fingertip-to-target distance meaningfully improves over
    the 14.65cm/9.49cm v0.2 baseline, penetration stays small/localized
    (not exceeding v0.1's original ~5-vertex/0.56cm scale), anchor drift
    stays small (a few cm, not tens), AND the visual GLB shows a
    plausible resting-on-the-lid pose.
  FAIL otherwise -- and if FAIL, this is the final Gate D attempt for
    this case. Freeze alapuse02v6n60 at Gate A+B+C.
"""
import time
import trimesh
import numpy as np
from pathlib import Path
from scipy.spatial import cKDTree
from scipy.optimize import minimize

TIME_BUDGET_SECONDS = 300  # hard 5-minute cap, per the cost lesson from v0.4

DATA = Path("/home/fredcui/foho_phase0")
TOKEN = "alapuse02v6n60"
RUN_ROOT = DATA / f"phase1_diagnostics/selector_v41_full_pipeline/runs/arctic_{TOKEN}_selector_v41_refined_pipeline"
CASE_ROOT = DATA / "phase2_gateA_part_recon/cases/alapuse02_v6_n60"
EXP_DIR = CASE_ROOT / "gate_c_experiment"
GATE_D_DIR = CASE_ROOT / "gate_d_v0_5_two_stage_arthoi_informed"
GATE_D_DIR.mkdir(parents=True, exist_ok=True)

t_start = time.time()

def check_budget():
    if time.time() - t_start > TIME_BUDGET_SECONDS:
        raise TimeoutError(
            f"[ABORT] exceeded {TIME_BUDGET_SECONDS}s budget -- "
            f"treat as FAIL_TIMEOUT, do not let this run longer."
        )

# ---------- load meshes (unchanged assets from prior rounds) ----------
T = np.load(EXP_DIR / f"{TOKEN}_object_only_h2m.npy")
hand = trimesh.load(RUN_ROOT / f"guidance_out/{TOKEN}_hand.ply", process=False)
part_dir = CASE_ROOT / "part_meshes_partfield_n2_vmap"
screen = trimesh.load(part_dir / "screen_lid.ply", process=False)
base = trimesh.load(part_dir / "keyboard_base.ply", process=False)
screen.apply_transform(T)
base.apply_transform(T)

hand_verts0 = np.asarray(hand.vertices)
hand_center0 = hand_verts0.mean(axis=0)

# ---------- restricted fingertip subset (thumb + index only) ----------
# MANO fingertip indices, per convention used throughout this investigation:
# [744=thumb, 320=index, 443=middle, 554=ring, 671=pinky]
# ArtHOI-informed: exclude ring/pinky by default (active_fingers pattern)
ACTIVE_TIP_IDX = [744, 320]  # thumb, index only

# ---------- small fixed target region on screen_lid ----------
# proxy for a "known contact patch": the screen_lid vertices closest to
# the hand's ORIGINAL position, taken as a small fixed set (mirrors
# ArtHOI's use of externally-specified, fixed contact correspondence
# rather than letting the optimizer discover an arbitrary point)
screen_verts = np.asarray(screen.vertices)
_dists_to_hand_center = np.linalg.norm(screen_verts - hand_center0, axis=1)
TARGET_PATCH_SIZE = 40
target_idx = np.argsort(_dists_to_hand_center)[:TARGET_PATCH_SIZE]
target_patch = screen_verts[target_idx]
target_tree = cKDTree(target_patch)
print(f"[setup] fixed target patch: {len(target_patch)} vertices on screen_lid")

# reversed containment check: object vertices inside the (always-
# watertight) hand mesh -- adopted directly from ArtHOI's compute_pen_masks
hand_faces = hand.faces
def object_verts_inside_hand(hand_verts, obj_points_sample):
    tmesh = trimesh.Trimesh(vertices=hand_verts, faces=hand_faces, process=False)
    return tmesh.contains(obj_points_sample)

# small fixed sample of object points for the penetration check (speed)
obj_sample, _ = trimesh.sample.sample_surface(screen, 300)
obj_sample = np.asarray(obj_sample)

def apply_rigid(verts, params, center):
    rx, ry, rz, tx, ty, tz = params
    R = trimesh.transformations.euler_matrix(rx, ry, rz)[:3, :3]
    return (verts - center) @ R.T + center + np.array([tx, ty, tz])

# ============ STAGE A: contact fit (attraction only) ============
def stage_a_loss(params):
    check_budget()
    v = apply_rigid(hand_verts0, params, hand_center0)
    tips = v[ACTIVE_TIP_IDX]
    d, _ = target_tree.query(tips)
    return d.mean() * 100.0  # same scale convention as ArtHOI's HO_interaction_loss

bounds_a = [(-0.2618, 0.2618)] * 3 + [(-0.04, 0.04)] * 3  # +-15deg, +-4cm
result_a = minimize(stage_a_loss, x0=np.zeros(6), method="L-BFGS-B",
                     bounds=bounds_a, options={"maxiter": 100})
print("[stage A] params:", result_a.x, "loss:", result_a.fun)

hand_verts_a = apply_rigid(hand_verts0, result_a.x, hand_center0)
tips_a = hand_verts_a[ACTIVE_TIP_IDX]
d_a, _ = target_tree.query(tips_a)
print(f"[stage A] tip-to-target distance: min={d_a.min()*100:.2f}cm mean={d_a.mean()*100:.2f}cm")

# ============ STAGE B: penetration cleanup (soft anchor) ============
anchor_center_a = hand_verts_a.mean(axis=0)

def stage_b_loss(params):
    check_budget()
    v = apply_rigid(hand_verts_a, params, anchor_center_a)

    # penetration term: sample object points inside hand (reversed direction)
    inside = object_verts_inside_hand(v, obj_sample)
    pen_term = 50.0 * inside.sum()  # simple count-based penalty (small sample -> cheap)

    # soft anchor: quadratic, no hard cliff (ArtHOI-style)
    drift = np.linalg.norm(v.mean(axis=0) - anchor_center_a)
    anchor_term = 5.0 * drift ** 2

    # keep tips near their stage-A target too (don't let cleanup destroy contact)
    tips = v[ACTIVE_TIP_IDX]
    d, _ = target_tree.query(tips)
    contact_term = d.mean() * 20.0  # lower weight than stage A -- secondary objective here

    return pen_term + anchor_term + contact_term

bounds_b = [(-0.0873, 0.0873)] * 3 + [(-0.02, 0.02)] * 3  # +-5deg, +-2cm
result_b = minimize(stage_b_loss, x0=np.zeros(6), method="L-BFGS-B",
                     bounds=bounds_b, options={"maxiter": 80})
print("[stage B] params:", result_b.x, "loss:", result_b.fun)

hand_verts_final = apply_rigid(hand_verts_a, result_b.x, anchor_center_a)

# ---------- final metrics ----------
tips_final = hand_verts_final[ACTIVE_TIP_IDX]
d_final, _ = target_tree.query(tips_final)
print(f"\n[FINAL] tip-to-target: min={d_final.min()*100:.2f}cm mean={d_final.mean()*100:.2f}cm")

total_drift = np.linalg.norm(hand_verts_final.mean(axis=0) - hand_center0)
print(f"[FINAL] total drift from original position: {total_drift*100:.2f}cm")

inside_final = object_verts_inside_hand(hand_verts_final, obj_sample)
print(f"[FINAL] object sample points inside hand: {int(inside_final.sum())} / {len(obj_sample)}")

print(f"\n[TIME] total elapsed: {time.time() - t_start:.1f}s (budget was {TIME_BUDGET_SECONDS}s)")

# ---------- anti-regression fallback ----------
# Baseline: the untouched original hand, scored on the SAME metrics used
# for the final candidate. If v0.6's result is not actually better than
# doing nothing, refuse to export it as an "improvement".
tips_baseline = hand_verts0[ACTIVE_TIP_IDX]
d_baseline, _ = target_tree.query(tips_baseline)
baseline_min_cm = d_baseline.min() * 100
baseline_mean_cm = d_baseline.mean() * 100
baseline_drift_cm = 0.0
inside_baseline = object_verts_inside_hand(hand_verts0, obj_sample)
baseline_inside = int(inside_baseline.sum())

final_min_cm = d_final.min() * 100
final_mean_cm = d_final.mean() * 100
final_drift_cm = total_drift * 100
final_inside = int(inside_final.sum())

print(f"\n[COMPARE] baseline: min={baseline_min_cm:.2f}cm mean={baseline_mean_cm:.2f}cm "
      f"drift={baseline_drift_cm:.2f}cm inside={baseline_inside}/{len(obj_sample)}")
print(f"[COMPARE] candidate: min={final_min_cm:.2f}cm mean={final_mean_cm:.2f}cm "
      f"drift={final_drift_cm:.2f}cm inside={final_inside}/{len(obj_sample)}")

is_better = (
    final_mean_cm < baseline_mean_cm
    and final_drift_cm <= 6.0
    and final_inside <= max(baseline_inside, 5)
)

if not is_better:
    print("\n[RESULT] NO_SAFE_UPDATE_FOUND -- candidate does not clearly "
          "improve on the untouched baseline within safety limits. "
          "Retaining ORIGINAL hand pose, not exporting the candidate.")
    hand_verts_final = hand_verts0.copy()
else:
    print("\n[RESULT] candidate accepted -- improves on baseline within limits.")

# ---------- save visual ----------
hand_new = hand.copy()
hand_new.vertices = hand_verts_final
hand_new.visual.vertex_colors = [255, 80, 80, 255]
screen.visual.vertex_colors = [80, 140, 255, 255]
base.visual.vertex_colors = [80, 220, 120, 255]
scene = trimesh.Scene([hand_new, screen, base])
out = GATE_D_DIR / "visuals" / f"{TOKEN}_gate_d_v0_5_two_stage.glb"
out.parent.mkdir(parents=True, exist_ok=True)
scene.export(out)
print("[OK] wrote", out)
