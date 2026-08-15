from pathlib import Path

p = Path("third_party/Hunyuan3D-2/hy3dgen/shapegen/pipelines.py")
s = p.read_text()

backup = p.with_suffix(".py.backup_before_exact_export_v5")
backup.write_text(s)
print("[OK] backup:", backup)

# 1. Make before_phase42 a clone, not a reference.
replacements = [
    (
        "foho_obj_mesh_before_phase42 = transformed_obj_mesh",
        "foho_obj_mesh_before_phase42 = transformed_obj_mesh.clone()  # FOHO V5: clone before Phase 4.2 candidate",
    ),
    (
        "foho_obj_mesh_before_phase42=transformed_obj_mesh",
        "foho_obj_mesh_before_phase42 = transformed_obj_mesh.clone()  # FOHO V5: clone before Phase 4.2 candidate",
    ),
]

changed_clone = 0
for old, new in replacements:
    if old in s and "FOHO V5: clone before Phase 4.2 candidate" not in s:
        s = s.replace(old, new, 1)
        changed_clone += 1

if "FOHO V5: clone before Phase 4.2 candidate" in s:
    print("[OK] before_phase42 clone patch present")
else:
    print("[WARN] did not find direct before_phase42 assignment to patch; inspect manually")

# 2. Remove old V4 phase42 export block if it exists, because it may be too late.
lines = s.splitlines()
out = []
skip = False

for line in lines:
    if "FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V4_PHASE42" in line:
        skip = True
        continue

    if skip:
        if 'print(' in line and "FOHO_INTERNAL_SELECTOR_AUTO" in line:
            skip = False
            out.append(line)
        continue

    out.append(line)

s = "\n".join(out) + "\n"

# 3. Insert new V5 phase42 export immediately before selection overwrite.
# The safest anchor is the branch that checks selected_name == before_phase42.
anchor = '''                            if selected_name == "before_phase42"'''
block = r'''                            # FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V5_PHASE42_TRUE_CANDIDATE
                            # Export the true Phase 4.2 candidate before any selector overwrite.
                            try:
                                _foho_os = __import__("os")
                                _foho_export_dir = _foho_os.environ.get("FOHO_INTERNAL_SELECTOR_EXPORT_DIR", "") or _foho_os.environ.get("FOHO_SELECTOR_DEBUG_DIR", "")
                                if _foho_export_dir:
                                    _foho_os.makedirs(_foho_export_dir, exist_ok=True)
                                    foho_export_p3d_mesh(
                                        transformed_obj_mesh,
                                        _foho_os.path.join(_foho_export_dir, "selector_candidate_phase42_before_joint.ply"),
                                    )
                                    print(f"[FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V5] true_phase42_candidate={_foho_os.path.join(_foho_export_dir, 'selector_candidate_phase42_before_joint.ply')}")
                                else:
                                    print("[FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V5] skipped true phase42 export: export dir empty")
                            except Exception as e:
                                print(f"[FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V5] true phase42 export failed: {e}")

'''

if "FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V5_PHASE42_TRUE_CANDIDATE" not in s:
    if anchor not in s:
        raise RuntimeError('Could not find anchor: if selected_name == "before_phase42"')
    s = s.replace(anchor, block + anchor, 1)
    print("[OK] inserted V5 true phase42 export block")
else:
    print("[OK] V5 true phase42 export block already present")

p.write_text(s)
print("[OK] wrote", p)
