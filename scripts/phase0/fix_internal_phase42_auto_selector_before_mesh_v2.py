from pathlib import Path
import re

p = Path("third_party/Hunyuan3D-2/hy3dgen/shapegen/pipelines.py")
s = p.read_text()

backup = p.with_suffix(".py.backup_before_fix_before_mesh_v2")
backup.write_text(s)
print("[OK] backup:", backup)

# ------------------------------------------------------------
# 1. Remove unsafe clone block, even if whitespace differs.
# ------------------------------------------------------------
unsafe_pattern = re.compile(
    r'\n(?P<indent>[ \t]+)try:\n'
    r'(?P=indent)[ \t]+foho_obj_mesh_before_phase42 = foho_clone_p3d_mesh\(transformed_obj_mesh\)\n'
    r'(?P=indent)except Exception as e:\n'
    r'(?P=indent)[ \t]+foho_obj_mesh_before_phase42 = None\n'
    r'(?P=indent)[ \t]+print\(f"\[FOHO_INTERNAL_SELECTOR_AUTO\] failed to save before_phase42 mesh: \{e\}"\)\n'
)

s_new, n_removed = unsafe_pattern.subn(
    '\n                            # Mesh clone is saved later, after transformed_obj_mesh exists.\n',
    s,
    count=1,
)
s = s_new
print(f"[OK] removed unsafe clone blocks: {n_removed}")

# ------------------------------------------------------------
# 2. Find object optimization marker.
# ------------------------------------------------------------
object_marker = 'info_str = f\'Object optimization step {i}, optimizing object transformation\''
object_idx = s.find(object_marker)
if object_idx == -1:
    raise RuntimeError("Could not find object optimization marker.")

# ------------------------------------------------------------
# 3. Find the last transformed_obj_mesh assignment before object optimization.
# ------------------------------------------------------------
assign_re = re.compile(
    r'^(?P<indent>[ \t]*)transformed_obj_mesh\s*=\s*transform_mesh_around_center_w_scale\(moge_obj_mesh,\s*RT_obj,\s*scale_obj\)\s*$',
    re.MULTILINE,
)

matches = [m for m in assign_re.finditer(s) if m.start() < object_idx]
if not matches:
    print("[DEBUG] nearby transformed_obj_mesh lines:")
    for line in s.splitlines():
        if "transformed_obj_mesh" in line:
            print(line)
    raise RuntimeError("Could not find transformed_obj_mesh assignment before object optimization marker.")

m = matches[-1]
indent = m.group("indent")
insert_pos = m.end()

safe_block = f'''
{indent}if os.environ.get("FOHO_ENABLE_INTERNAL_PHASE42_SELECTOR", "0") == "1" and foho_obj_mesh_before_phase42 is None:
{indent}    try:
{indent}        foho_obj_mesh_before_phase42 = foho_clone_p3d_mesh(transformed_obj_mesh)
{indent}        before_score_dbg = foho_score_p3d_mesh(foho_obj_mesh_before_phase42)
{indent}        print(
{indent}            f"[FOHO_INTERNAL_SELECTOR_AUTO] saved before_phase42 mesh "
{indent}            f"at step {{i}}; frag={{before_score_dbg['fragmentation_score']:.6f}}, "
{indent}            f"comp={{before_score_dbg['components']}}"
{indent}        )
{indent}    except Exception as e:
{indent}        foho_obj_mesh_before_phase42 = None
{indent}        print(f"[FOHO_INTERNAL_SELECTOR_AUTO] failed to save before_phase42 mesh after transform: {{e}}")
'''

if "saved before_phase42 mesh at step" not in s:
    s = s[:insert_pos] + safe_block + s[insert_pos:]
    print("[OK] inserted safe before_phase42 mesh clone after transformed_obj_mesh assignment")
else:
    print("[SKIP] safe before_phase42 mesh clone already exists")

p.write_text(s)
print("[OK] wrote", p)
