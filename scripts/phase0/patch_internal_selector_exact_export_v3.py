from pathlib import Path

p = Path("third_party/Hunyuan3D-2/hy3dgen/shapegen/pipelines.py")
s = p.read_text()

backup = p.with_suffix(".py.backup_before_exact_export_v3")
backup.write_text(s)
print("[OK] backup:", backup)

# 1. Ensure PyTorch3D mesh export helper exists.
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
    if helper_needle not in s:
        raise RuntimeError("Cannot find transform_hunyuan2moge anchor for helper insertion.")
    s = s.replace(helper_needle, helper + helper_needle, 1)
    print("[OK] inserted foho_export_p3d_mesh helper")
else:
    print("[OK] foho_export_p3d_mesh helper already exists")

lines = s.splitlines()
out = []

inserted_phase42 = 0
inserted_selected = 0

for idx, line in enumerate(lines):
    stripped = line.strip()
    indent = line[: len(line) - len(line.lstrip())]

    # 2. Export current Phase 4.2 candidate right before the auto selector decision log.
    if (
        "FOHO_INTERNAL_SELECTOR_AUTO" in line
        and "before_frag=" in line
        and "current_frag=" in line
        and "selected=" in line
        and "FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V3_PHASE42" not in "\n".join(out[-8:])
    ):
        out.append(f'{indent}# FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V3_PHASE42')
        out.append(f'{indent}try:')
        out.append(f'{indent}    _foho_os = __import__("os")')
        out.append(f'{indent}    _foho_export_dir = _foho_os.environ.get("FOHO_INTERNAL_SELECTOR_EXPORT_DIR", "") or _foho_os.environ.get("FOHO_SELECTOR_DEBUG_DIR", "")')
        out.append(f'{indent}    if _foho_export_dir:')
        out.append(f'{indent}        _foho_os.makedirs(_foho_export_dir, exist_ok=True)')
        out.append(f'{indent}        foho_export_p3d_mesh(transformed_obj_mesh, _foho_os.path.join(_foho_export_dir, "selector_candidate_phase42_before_joint.ply"))')
        out.append(f'{indent}        print(f"[FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V3] phase42_candidate={{_foho_os.path.join(_foho_export_dir, \'selector_candidate_phase42_before_joint.ply\')}}")')
        out.append(f'{indent}    else:')
        out.append(f'{indent}        print("[FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V3] skipped phase42 export: export dir empty")')
        out.append(f'{indent}except Exception as e:')
        out.append(f'{indent}    print(f"[FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V3] phase42 export failed: {{e}}")')
        inserted_phase42 += 1

    # 3. Export before candidate and selected candidate directly before the active selected-print line.
    if (
        "FOHO_INTERNAL_SELECTOR" in line
        and "selected={selected_name}; applied before joint step" in line
        and "FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V3_SELECTED" not in "\n".join(out[-12:])
    ):
        out.append(f'{indent}# FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V3_SELECTED')
        out.append(f'{indent}try:')
        out.append(f'{indent}    _foho_os = __import__("os")')
        out.append(f'{indent}    _foho_export_dir = _foho_os.environ.get("FOHO_INTERNAL_SELECTOR_EXPORT_DIR", "") or _foho_os.environ.get("FOHO_SELECTOR_DEBUG_DIR", "")')
        out.append(f'{indent}    if _foho_export_dir:')
        out.append(f'{indent}        _foho_os.makedirs(_foho_export_dir, exist_ok=True)')
        out.append(f'{indent}        if "foho_obj_mesh_before_phase42" in locals() and foho_obj_mesh_before_phase42 is not None:')
        out.append(f'{indent}            foho_export_p3d_mesh(foho_obj_mesh_before_phase42, _foho_os.path.join(_foho_export_dir, "selector_candidate_before_phase42.ply"))')
        out.append(f'{indent}        foho_export_p3d_mesh(transformed_obj_mesh, _foho_os.path.join(_foho_export_dir, "selector_selected_before_joint.ply"))')
        out.append(f'{indent}        print(f"[FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V3] export_dir={{_foho_export_dir}}; selected={{selected_name}}")')
        out.append(f'{indent}    else:')
        out.append(f'{indent}        print("[FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V3] skipped selected export: export dir empty")')
        out.append(f'{indent}except Exception as e:')
        out.append(f'{indent}    print(f"[FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V3] selected export failed: {{e}}")')
        inserted_selected += 1

    out.append(line)

s2 = "\n".join(out) + "\n"
p.write_text(s2)

print("[OK] inserted phase42 export blocks:", inserted_phase42)
print("[OK] inserted selected export blocks:", inserted_selected)

if inserted_phase42 == 0 or inserted_selected == 0:
    raise RuntimeError("Did not insert expected export blocks. Inspect selector code anchors.")
