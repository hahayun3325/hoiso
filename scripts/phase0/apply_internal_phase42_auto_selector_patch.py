from pathlib import Path

p = Path("third_party/Hunyuan3D-2/hy3dgen/shapegen/pipelines.py")
s = p.read_text()

backup = p.with_suffix(".py.backup_before_auto_selector")
backup.write_text(s)
print("[OK] backup:", backup)

# ---------------------------------------------------------------------
# 1. Add helper functions for cloning/scoring PyTorch3D meshes.
# ---------------------------------------------------------------------
helper_anchor = "def foho_export_p3d_mesh(mesh, save_path):"

helper_block = r'''
def foho_clone_p3d_mesh(mesh):
    """Clone a PyTorch3D Meshes object without gradients."""
    try:
        from pytorch3d.structures import Meshes
        verts = mesh.verts_packed().detach().clone()
        faces = mesh.faces_packed().detach().clone()
        return Meshes(verts=[verts], faces=[faces])
    except Exception as e:
        print(f"[FOHO_INTERNAL_SELECTOR_AUTO] clone failed: {e}")
        return None


def foho_score_p3d_mesh(mesh):
    """Compute cheap mesh quality score for a PyTorch3D Meshes object."""
    try:
        import numpy as np
        import trimesh

        verts = mesh.verts_packed().detach().cpu().numpy()
        faces = mesh.faces_packed().detach().cpu().numpy()

        tri = trimesh.Trimesh(vertices=verts, faces=faces, process=False)
        comps = tri.split(only_watertight=False)
        face_counts = np.array([len(c.faces) for c in comps], dtype=float)

        largest_ratio = face_counts.max() / max(len(tri.faces), 1) if len(face_counts) else 0.0
        frag = (len(comps) - 1) + (1.0 - largest_ratio)

        return {
            "components": int(len(comps)),
            "largest_face_ratio": float(largest_ratio),
            "fragmentation_score": float(frag),
            "watertight": bool(tri.is_watertight),
        }
    except Exception as e:
        print(f"[FOHO_INTERNAL_SELECTOR_AUTO] score failed: {e}")
        return {
            "components": 999,
            "largest_face_ratio": 0.0,
            "fragmentation_score": 999.0,
            "watertight": False,
        }


'''

if "def foho_score_p3d_mesh(" not in s:
    if helper_anchor not in s:
        raise RuntimeError("Could not find foho_export_p3d_mesh helper anchor.")
    s = s.replace(helper_anchor, helper_block + helper_anchor, 1)
    print("[OK] inserted auto selector helper functions")
else:
    print("[SKIP] auto selector helper functions already exist")

# ---------------------------------------------------------------------
# 2. Add mesh-state variable after existing selector state variables.
# ---------------------------------------------------------------------
state_anchor = "        foho_phase42_selector_applied = False\n"

state_insert = """        foho_obj_mesh_before_phase42 = None
"""

if "foho_obj_mesh_before_phase42" not in s:
    if state_anchor not in s:
        raise RuntimeError("Could not find selector state anchor.")
    s = s.replace(state_anchor, state_anchor + state_insert, 1)
    print("[OK] inserted foho_obj_mesh_before_phase42 state")
else:
    print("[SKIP] foho_obj_mesh_before_phase42 already exists")

# ---------------------------------------------------------------------
# 3. Save a clone of the object mesh before Phase 4.2.
# ---------------------------------------------------------------------
save_anchor = '''                            foho_obj_state_before_phase42 = {
                                "scale_obj": scale_obj.clone().detach(),
                                "trans_obj": trans_obj.clone().detach(),
                                "rotation_obj": rotation_obj.clone().detach(),
                                "obj_latents": obj_latents.clone().detach(),
                            }
                            print(f"[FOHO_INTERNAL_SELECTOR] saved before_phase42 state at step {i}")
'''

save_replacement = '''                            foho_obj_state_before_phase42 = {
                                "scale_obj": scale_obj.clone().detach(),
                                "trans_obj": trans_obj.clone().detach(),
                                "rotation_obj": rotation_obj.clone().detach(),
                                "obj_latents": obj_latents.clone().detach(),
                            }
                            try:
                                foho_obj_mesh_before_phase42 = foho_clone_p3d_mesh(transformed_obj_mesh)
                            except Exception as e:
                                foho_obj_mesh_before_phase42 = None
                                print(f"[FOHO_INTERNAL_SELECTOR_AUTO] failed to save before_phase42 mesh: {e}")
                            print(f"[FOHO_INTERNAL_SELECTOR] saved before_phase42 state at step {i}")
'''

if "failed to save before_phase42 mesh" not in s:
    if save_anchor not in s:
        raise RuntimeError("Could not find before_phase42 save block.")
    s = s.replace(save_anchor, save_replacement, 1)
    print("[OK] updated before_phase42 save block with mesh clone")
else:
    print("[SKIP] before_phase42 save block already updated")

# ---------------------------------------------------------------------
# 4. Replace the selector decision block before joint optimization.
# ---------------------------------------------------------------------
start = s.find('                        if os.environ.get("FOHO_ENABLE_INTERNAL_PHASE42_SELECTOR", "0") == "1" and not foho_phase42_selector_applied:')
if start == -1:
    raise RuntimeError("Could not find selector decision block start.")

end_marker = '                        info_str = f\'Joint optimization step {i}, optimizing hands and object together\'\n'
end = s.find(end_marker, start)
if end == -1:
    raise RuntimeError("Could not find joint optimization info_str after selector block.")

old_block = s[start:end]

new_block = r'''                        if os.environ.get("FOHO_ENABLE_INTERNAL_PHASE42_SELECTOR", "0") == "1" and not foho_phase42_selector_applied:
                            choice = os.environ.get("FOHO_INTERNAL_PHASE42_SELECTOR_CHOICE", "phase42_before_joint")

                            selected_name = "phase42_before_joint"

                            if choice == "auto_fragmentation":
                                current_score = foho_score_p3d_mesh(transformed_obj_mesh)
                                before_score = foho_score_p3d_mesh(foho_obj_mesh_before_phase42) if foho_obj_mesh_before_phase42 is not None else {
                                    "fragmentation_score": 999.0,
                                    "components": 999,
                                    "largest_face_ratio": 0.0,
                                    "watertight": False,
                                }

                                current_frag = float(current_score["fragmentation_score"])
                                before_frag = float(before_score["fragmentation_score"])
                                margin = float(os.environ.get("FOHO_INTERNAL_SELECTOR_MARGIN", "0.0"))

                                if before_frag + margin < current_frag and foho_obj_state_before_phase42 is not None:
                                    scale_obj = foho_obj_state_before_phase42["scale_obj"].clone().to(device)
                                    trans_obj = foho_obj_state_before_phase42["trans_obj"].clone().to(device)
                                    rotation_obj = foho_obj_state_before_phase42["rotation_obj"].clone().to(device)
                                    obj_latents = foho_obj_state_before_phase42["obj_latents"].clone().to(device)
                                    if foho_obj_mesh_before_phase42 is not None:
                                        transformed_obj_mesh = foho_obj_mesh_before_phase42.to(device)
                                    selected_name = "before_phase42"
                                else:
                                    selected_name = "phase42_before_joint"

                                print(
                                    f"[FOHO_INTERNAL_SELECTOR_AUTO] "
                                    f"before_frag={before_frag:.6f}, current_frag={current_frag:.6f}, "
                                    f"margin={margin:.6f}, selected={selected_name}"
                                )

                            elif choice in ["before_phase42", "pre_phase42", "initial"]:
                                if foho_obj_state_before_phase42 is None:
                                    print("[FOHO_INTERNAL_SELECTOR] before_phase42 state missing; keeping phase42_before_joint")
                                    selected_name = "phase42_before_joint"
                                else:
                                    scale_obj = foho_obj_state_before_phase42["scale_obj"].clone().to(device)
                                    trans_obj = foho_obj_state_before_phase42["trans_obj"].clone().to(device)
                                    rotation_obj = foho_obj_state_before_phase42["rotation_obj"].clone().to(device)
                                    obj_latents = foho_obj_state_before_phase42["obj_latents"].clone().to(device)
                                    if foho_obj_mesh_before_phase42 is not None:
                                        transformed_obj_mesh = foho_obj_mesh_before_phase42.to(device)
                                    selected_name = "before_phase42"

                            elif choice in ["phase42_before_joint", "phase42", "current"]:
                                selected_name = "phase42_before_joint"

                            else:
                                selected_name = "phase42_before_joint"
                                print(f"[FOHO_INTERNAL_SELECTOR] unknown choice={choice}; keeping phase42_before_joint")

                            foho_phase42_selector_applied = True
                            print(f"[FOHO_INTERNAL_SELECTOR] selected={selected_name}; applied before joint step {i}")
'''

if "FOHO_INTERNAL_SELECTOR_AUTO" not in old_block:
    s = s[:start] + new_block + s[end:]
    print("[OK] replaced selector decision block with auto_fragmentation support")
else:
    print("[SKIP] selector decision block already has auto support")

p.write_text(s)
print("[OK] wrote", p)
