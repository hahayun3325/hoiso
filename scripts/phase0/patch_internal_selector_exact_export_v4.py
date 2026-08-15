from pathlib import Path

p = Path("third_party/Hunyuan3D-2/hy3dgen/shapegen/pipelines.py")
s = p.read_text()

backup = p.with_suffix(".py.backup_before_exact_export_v4")
backup.write_text(s)
print("[OK] backup:", backup)

# Helper should already exist from earlier patches.
if "def foho_export_p3d_mesh(" not in s:
    raise RuntimeError("Missing foho_export_p3d_mesh helper. Apply debug export patch first.")

# If V4 already exists, do not duplicate.
if "FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V4_PHASE42" in s and "FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V4_SELECTED" in s:
    print("[OK] V4 export blocks already exist")
    raise SystemExit(0)

# Insert Phase 4.2 candidate export before the auto selector decision print.
phase42_anchor = '''                                print(
                                    f"[FOHO_INTERNAL_SELECTOR_AUTO] "
'''

phase42_block = r'''                                # FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V4_PHASE42
                                try:
                                    _foho_os = __import__("os")
                                    _foho_export_dir = _foho_os.environ.get("FOHO_INTERNAL_SELECTOR_EXPORT_DIR", "") or _foho_os.environ.get("FOHO_SELECTOR_DEBUG_DIR", "")
                                    if _foho_export_dir:
                                        _foho_os.makedirs(_foho_export_dir, exist_ok=True)
                                        foho_export_p3d_mesh(
                                            transformed_obj_mesh,
                                            _foho_os.path.join(_foho_export_dir, "selector_candidate_phase42_before_joint.ply"),
                                        )
                                        print(f"[FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V4] phase42_candidate={_foho_os.path.join(_foho_export_dir, 'selector_candidate_phase42_before_joint.ply')}")
                                    else:
                                        print("[FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V4] skipped phase42 export: export dir empty")
                                except Exception as e:
                                    print(f"[FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V4] phase42 export failed: {e}")

'''

inserted_phase42 = 0
if "FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V4_PHASE42" not in s:
    if phase42_anchor not in s:
        raise RuntimeError("Could not find multiline FOHO_INTERNAL_SELECTOR_AUTO print anchor.")
    s = s.replace(phase42_anchor, phase42_block + phase42_anchor, 1)
    inserted_phase42 = 1

# Insert selected export immediately before the active selected-print line.
selected_anchor = '''                            print(f"[FOHO_INTERNAL_SELECTOR] selected={selected_name}; applied before joint step {i}")
'''

selected_block = r'''                            # FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V4_SELECTED
                            try:
                                _foho_os = __import__("os")
                                _foho_export_dir = _foho_os.environ.get("FOHO_INTERNAL_SELECTOR_EXPORT_DIR", "") or _foho_os.environ.get("FOHO_SELECTOR_DEBUG_DIR", "")
                                if _foho_export_dir:
                                    _foho_os.makedirs(_foho_export_dir, exist_ok=True)
                                    if "foho_obj_mesh_before_phase42" in locals() and foho_obj_mesh_before_phase42 is not None:
                                        foho_export_p3d_mesh(
                                            foho_obj_mesh_before_phase42,
                                            _foho_os.path.join(_foho_export_dir, "selector_candidate_before_phase42.ply"),
                                        )
                                    foho_export_p3d_mesh(
                                        transformed_obj_mesh,
                                        _foho_os.path.join(_foho_export_dir, "selector_selected_before_joint.ply"),
                                    )
                                    print(f"[FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V4] export_dir={_foho_export_dir}; selected={selected_name}")
                                else:
                                    print("[FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V4] skipped selected export: export dir empty")
                            except Exception as e:
                                print(f"[FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V4] selected export failed: {e}")

'''

inserted_selected = 0
if "FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V4_SELECTED" not in s:
    if selected_anchor not in s:
        raise RuntimeError("Could not find active selected-print anchor.")
    s = s.replace(selected_anchor, selected_block + selected_anchor, 1)
    inserted_selected = 1

p.write_text(s)

print("[OK] inserted phase42 V4 blocks:", inserted_phase42)
print("[OK] inserted selected V4 blocks:", inserted_selected)
