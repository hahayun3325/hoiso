from pathlib import Path

p = Path("third_party/Hunyuan3D-2/hy3dgen/shapegen/pipelines.py")
s = p.read_text()

helper_needle = "def transform_hunyuan2moge(mesh, RT):"
helper = r'''
def foho_export_p3d_mesh(mesh, save_path):
    """Export a PyTorch3D Meshes object for selector/debug inspection."""
    try:
        import os
        import trimesh
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        verts = mesh.verts_packed().detach().cpu().numpy()
        faces = mesh.faces_packed().detach().cpu().numpy()
        trimesh.Trimesh(vertices=verts, faces=faces, process=False).export(save_path)
        print(f"[FOHO_SELECTOR_DEBUG] exported {save_path}")
    except Exception as e:
        print(f"[FOHO_SELECTOR_DEBUG] export failed for {save_path}: {e}")


'''

if "def foho_export_p3d_mesh(" not in s:
    s = s.replace(helper_needle, helper + helper_needle)

export_needle = "                            # Hand to object. NOTE: gradients only flow through hand mesh, not obj mesh"
export_block = r'''                            selector_debug_dir = os.environ.get("FOHO_SELECTOR_DEBUG_DIR", "")
                            if selector_debug_dir:
                                foho_export_p3d_mesh(obj_mesh, f"{selector_debug_dir}/phase42_obj_raw_hunyuan_space_t{i}_opt{k}.ply")
                                foho_export_p3d_mesh(moge_obj_mesh, f"{selector_debug_dir}/phase42_obj_moge_space_t{i}_opt{k}.ply")
                                foho_export_p3d_mesh(transformed_obj_mesh, f"{selector_debug_dir}/phase42_obj_transformed_before_joint_t{i}_opt{k}.ply")

'''

if export_block.strip() not in s:
    s = s.replace(export_needle, export_block + export_needle)

p.write_text(s)
print("[OK] applied internal selector debug export patch")
