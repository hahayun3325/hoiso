from pathlib import Path

p = Path("third_party/Hunyuan3D-2/hy3dgen/shapegen/pipelines.py")
s = p.read_text()

# 1. Add helper function if missing.
needle = "def foho_export_p3d_mesh("
helper = r'''
def foho_save_native_obj_render(renderer, obj_mesh, moge_normal, save_path):
    """Save a native pipeline-view object render for selector visualization."""
    try:
        with torch.cuda.amp.autocast(enabled=False):
            rendered_normal, _ = render_normal_and_disparity(renderer, obj_mesh)
        plot_in_grid(rendered_normal, moge_normal, save_path=save_path)
        print(f"[FOHO_SELECTOR_RENDER] saved {save_path}")
    except Exception as e:
        print(f"[FOHO_SELECTOR_RENDER] failed to save {save_path}: {e}")


'''

if "def foho_save_native_obj_render(" not in s:
    idx = s.find(needle)
    if idx == -1:
        raise RuntimeError("Could not find foho_export_p3d_mesh helper anchor.")
    s = s[:idx] + helper + s[idx:]


# 2. Save before-Phase-4.2 native render right after before mesh is cloned.
old_before = """foho_obj_mesh_before_phase42 = foho_clone_p3d_mesh(transformed_obj_mesh)
                                    before_score_dbg = foho_score_p3d_mesh(foho_obj_mesh_before_phase42)"""

new_before = """foho_obj_mesh_before_phase42 = foho_clone_p3d_mesh(transformed_obj_mesh)
                                    if debugging and save_dir:
                                        foho_save_native_obj_render(
                                            renderer,
                                            foho_obj_mesh_before_phase42,
                                            moge_normal * moge_obj_mask[..., None],
                                            f"{save_dir}/foho_selector_before_phase42_native.png",
                                        )
                                    before_score_dbg = foho_score_p3d_mesh(foho_obj_mesh_before_phase42)"""

if old_before in s and "foho_selector_before_phase42_native.png" not in s:
    s = s.replace(old_before, new_before)
else:
    print("[WARN] before-phase42 render patch already present or anchor missing")


# 3. Save selected candidate native render inside selector application block.
# This assumes selector_selected_before_joint.ply/export logic already exists.
anchor = """print(f"[FOHO_INTERNAL_SELECTOR_AUTO] selected={selected_name}"""
insert = r'''
                                if debugging and save_dir:
                                    try:
                                        foho_save_native_obj_render(
                                            renderer,
                                            transformed_obj_mesh,
                                            moge_normal * moge_obj_mask[..., None],
                                            f"{save_dir}/foho_selector_selected_before_joint_native.png",
                                        )
                                    except Exception as e:
                                        print(f"[FOHO_SELECTOR_RENDER] failed selected render: {e}")
'''

if anchor in s and "foho_selector_selected_before_joint_native.png" not in s:
    pos = s.find(anchor)
    line_start = s.rfind("\n", 0, pos)
    s = s[:line_start] + insert + s[line_start:]
else:
    print("[WARN] selected render patch already present or selector anchor missing")


# 4. Save after Phase 4.2 native render before joint.
# Use the true candidate filename if your current branch has that stage.
anchor2 = """current_score = foho_score_p3d_mesh(transformed_obj_mesh)"""
insert2 = r'''
                                if debugging and save_dir:
                                    try:
                                        foho_save_native_obj_render(
                                            renderer,
                                            transformed_obj_mesh,
                                            moge_normal * moge_obj_mask[..., None],
                                            f"{save_dir}/foho_selector_phase42_before_joint_native.png",
                                        )
                                    except Exception as e:
                                        print(f"[FOHO_SELECTOR_RENDER] failed phase42 render: {e}")
'''

if anchor2 in s and "foho_selector_phase42_before_joint_native.png" not in s:
    pos = s.find(anchor2)
    line_start = s.rfind("\n", 0, pos)
    s = s[:line_start] + insert2 + s[line_start:]
else:
    print("[WARN] phase42 render patch already present or anchor missing")

p.write_text(s)
print("[OK] patched", p)
