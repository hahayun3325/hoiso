from pathlib import Path

p = Path("third_party/Hunyuan3D-2/hy3dgen/shapegen/pipelines.py")
s = p.read_text()

backup = p.with_suffix(".py.backup_before_exact_export_v5b")
backup.write_text(s)
print("[OK] backup:", backup)

if "def foho_export_p3d_mesh(" not in s:
    raise RuntimeError("Missing foho_export_p3d_mesh helper.")

if "def foho_clone_p3d_mesh(" not in s:
    raise RuntimeError("Missing foho_clone_p3d_mesh helper.")

# ---------------------------------------------------------------------
# 1. Add variable for true Phase 4.2 candidate.
# ---------------------------------------------------------------------
if "foho_obj_mesh_phase42_before_joint = None" not in s:
    anchor = "        foho_obj_mesh_before_phase42 = None\n"
    if anchor not in s:
        raise RuntimeError("Could not find foho_obj_mesh_before_phase42 init anchor.")
    s = s.replace(
        anchor,
        anchor + "        foho_obj_mesh_phase42_before_joint = None\n",
        1,
    )
    print("[OK] added foho_obj_mesh_phase42_before_joint init")
else:
    print("[OK] phase42 candidate variable already exists")

# ---------------------------------------------------------------------
# 2. Remove old V4 PHASE42 block, because it exports too late.
# ---------------------------------------------------------------------
lines = s.splitlines()
out = []
i = 0
removed = 0

while i < len(lines):
    line = lines[i]

    if "FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V4_PHASE42" in line:
        removed += 1
        i += 1

        # skip until the real auto-selector print block starts
        while i < len(lines):
            if (
                lines[i].lstrip().startswith("print(")
                and i + 1 < len(lines)
                and "FOHO_INTERNAL_SELECTOR_AUTO" in lines[i + 1]
            ):
                break
            i += 1
        continue

    out.append(line)
    i += 1

s = "\n".join(out) + "\n"
print("[OK] removed old V4 phase42 blocks:", removed)

# ---------------------------------------------------------------------
# 3. Insert true phase42 export BEFORE selector may overwrite object mesh.
# ---------------------------------------------------------------------
anchor = '''                                if before_frag + margin < current_frag and foho_obj_state_before_phase42 is not None:
'''

insert = r'''                                # FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V5B_TRUE_PHASE42
                                # Save/export the true Phase 4.2 candidate before selector overwrite.
                                try:
                                    _foho_os = __import__("os")
                                    _foho_export_dir = _foho_os.environ.get("FOHO_INTERNAL_SELECTOR_EXPORT_DIR", "") or _foho_os.environ.get("FOHO_SELECTOR_DEBUG_DIR", "")

                                    foho_obj_mesh_phase42_before_joint = foho_clone_p3d_mesh(transformed_obj_mesh)

                                    if _foho_export_dir:
                                        _foho_os.makedirs(_foho_export_dir, exist_ok=True)
                                        foho_export_p3d_mesh(
                                            foho_obj_mesh_phase42_before_joint,
                                            _foho_os.path.join(_foho_export_dir, "selector_candidate_phase42_before_joint.ply"),
                                        )
                                        print(
                                            f"[FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V5B] "
                                            f"true_phase42_candidate={_foho_os.path.join(_foho_export_dir, 'selector_candidate_phase42_before_joint.ply')}"
                                        )
                                    else:
                                        print("[FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V5B] skipped true phase42 export: export dir empty")
                                except Exception as e:
                                    print(f"[FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V5B] true phase42 export failed: {e}")

'''

if "FOHO_INTERNAL_SELECTOR_EXACT_EXPORT_V5B_TRUE_PHASE42" not in s:
    if anchor not in s:
        raise RuntimeError("Could not find before/current selection branch anchor.")
    s = s.replace(anchor, insert + anchor, 1)
    print("[OK] inserted V5B true phase42 export block")
else:
    print("[OK] V5B true phase42 export block already exists")

p.write_text(s)
print("[OK] wrote", p)
