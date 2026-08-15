from pathlib import Path

p = Path("third_party/Hunyuan3D-2/hy3dgen/shapegen/pipelines.py")
s = p.read_text()

backup = p.with_suffix(".py.backup_before_fix_before_mesh")
backup.write_text(s)
print("[OK] backup:", backup)

# Remove the old unsafe clone attempt that happens before transformed_obj_mesh exists.
bad_block = '''                            try:
                                foho_obj_mesh_before_phase42 = foho_clone_p3d_mesh(transformed_obj_mesh)
                            except Exception as e:
                                foho_obj_mesh_before_phase42 = None
                                print(f"[FOHO_INTERNAL_SELECTOR_AUTO] failed to save before_phase42 mesh: {e}")
'''

if bad_block in s:
    s = s.replace(
        bad_block,
        '''                            # Mesh clone is saved later, after transformed_obj_mesh exists.
''',
        1,
    )
    print("[OK] removed unsafe before_phase42 mesh clone")
else:
    print("[WARN] unsafe clone block not found; maybe already removed")

# Insert safe clone after transformed_obj_mesh is created inside the object optimization block.
object_start = s.find("Object optimization step {i}, optimizing object transformation")
joint_start = s.find("Joint optimization step {i}, optimizing hands and object together", object_start)

if object_start == -1 or joint_start == -1:
    raise RuntimeError("Could not locate object/joint optimization region.")

region = s[object_start:joint_start]

needle = "transformed_obj_mesh = transform_mesh_around_center_w_scale(moge_obj_mesh, RT_obj, scale_obj)\n"
insert = '''transformed_obj_mesh = transform_mesh_around_center_w_scale(moge_obj_mesh, RT_obj, scale_obj)
                            if os.environ.get("FOHO_ENABLE_INTERNAL_PHASE42_SELECTOR", "0") == "1" and foho_obj_mesh_before_phase42 is None:
                                try:
                                    foho_obj_mesh_before_phase42 = foho_clone_p3d_mesh(transformed_obj_mesh)
                                    before_score_dbg = foho_score_p3d_mesh(foho_obj_mesh_before_phase42)
                                    print(
                                        f"[FOHO_INTERNAL_SELECTOR_AUTO] saved before_phase42 mesh "
                                        f"at step {i}; frag={before_score_dbg['fragmentation_score']:.6f}, "
                                        f"comp={before_score_dbg['components']}"
                                    )
                                except Exception as e:
                                    foho_obj_mesh_before_phase42 = None
                                    print(f"[FOHO_INTERNAL_SELECTOR_AUTO] failed to save before_phase42 mesh after transform: {e}")
'''

if "saved before_phase42 mesh at step" not in s:
    if needle not in region:
        raise RuntimeError("Could not find transformed_obj_mesh assignment inside object optimization region.")
    region = region.replace(needle, insert, 1)
    s = s[:object_start] + region + s[joint_start:]
    print("[OK] inserted safe before_phase42 mesh clone after transformed_obj_mesh assignment")
else:
    print("[SKIP] safe before_phase42 mesh clone already exists")

p.write_text(s)
print("[OK] wrote", p)
