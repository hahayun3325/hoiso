from pathlib import Path

p = Path("third_party/Hunyuan3D-2/hy3dgen/shapegen/pipelines.py")
s = p.read_text()

backup = p.with_suffix(".py.backup_before_exact_export_v5c_unique")
backup.write_text(s)
print("[OK] backup:", backup)

if "def foho_export_p3d_mesh(" not in s:
    raise RuntimeError("Missing foho_export_p3d_mesh helper.")

anchor = '''                                if before_frag + margin < current_frag and foho_obj_state_before_phase42 is not None:
'''

block = r'''                                # FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V5C_TRUE_PHASE42_UNIQUE
                                # Save the true Phase 4.2 candidate to a unique filename before selector overwrite.
                                try:
                                    _foho_os = __import__("os")
                                    _foho_export_dir = _foho_os.environ.get("FOHO_INTERNAL_SELECTOR_EXPORT_DIR", "") or _foho_os.environ.get("FOHO_SELECTOR_DEBUG_DIR", "")
                                    if _foho_export_dir:
                                        _foho_os.makedirs(_foho_export_dir, exist_ok=True)
                                        _foho_true_path = _foho_os.path.join(
                                            _foho_export_dir,
                                            "selector_candidate_phase42_before_joint_true.ply",
                                        )
                                        foho_export_p3d_mesh(transformed_obj_mesh, _foho_true_path)
                                        print(f"[FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V5C] true_phase42_candidate={_foho_true_path}")
                                    else:
                                        print("[FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V5C] skipped true phase42 export: export dir empty")
                                except Exception as e:
                                    print(f"[FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V5C] true phase42 export failed: {e}")

'''

if "FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V5C_TRUE_PHASE42_UNIQUE" not in s:
    if anchor not in s:
        raise RuntimeError("Could not find before/current selection branch anchor.")
    s = s.replace(anchor, block + anchor, 1)
    print("[OK] inserted V5C unique true phase42 export block")
else:
    print("[OK] V5C unique true phase42 export block already exists")

p.write_text(s)
print("[OK] wrote", p)
