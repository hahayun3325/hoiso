from pathlib import Path

p = Path("third_party/Hunyuan3D-2/hy3dgen/shapegen/pipelines.py")
s = p.read_text()

backup = p.with_suffix(".py.backup_before_selector_candidate_export_v2")
backup.write_text(s)
print("[OK] backup:", backup)

if "FOHO_INTERNAL_SELECTOR_EXPORT" in s:
    print("[OK] export block already exists")
    raise SystemExit(0)

marker = '''                            foho_phase42_selector_applied = True
                            print(f"[FOHO_INTERNAL_SELECTOR] selected={selected_name}; applied before joint step {i}")
'''

if marker not in s:
    raise RuntimeError(
        "Could not find selector-applied marker. "
        "Run: grep -n \"selected=.*applied before joint\" third_party/Hunyuan3D-2/hy3dgen/shapegen/pipelines.py"
    )

insert = r'''                            # FOHO DEBUG: export exact selector candidates in the same runtime frame.
                            try:
                                export_dir = os.environ.get("FOHO_INTERNAL_SELECTOR_EXPORT_DIR", "")
                                if export_dir:
                                    os.makedirs(export_dir, exist_ok=True)

                                    if foho_obj_mesh_before_phase42 is not None:
                                        foho_export_p3d_mesh(
                                            foho_obj_mesh_before_phase42,
                                            os.path.join(export_dir, "selector_candidate_before_phase42.ply"),
                                        )

                                    foho_export_p3d_mesh(
                                        transformed_obj_mesh,
                                        os.path.join(export_dir, "selector_selected_before_joint.ply"),
                                    )

                                    print(
                                        f"[FOHO_INTERNAL_SELECTOR_EXPORT] export_dir={export_dir}; "
                                        f"selected={selected_name}"
                                    )
                                else:
                                    print("[FOHO_INTERNAL_SELECTOR_EXPORT] skipped: FOHO_INTERNAL_SELECTOR_EXPORT_DIR empty")
                            except Exception as e:
                                print(f"[FOHO_INTERNAL_SELECTOR_EXPORT] failed: {e}")

                            foho_phase42_selector_applied = True
                            print(f"[FOHO_INTERNAL_SELECTOR] selected={selected_name}; applied before joint step {i}")
'''

s = s.replace(marker, insert, 1)
p.write_text(s)

print("[OK] inserted export block")
print("[OK] wrote", p)
