from pathlib import Path
import re

p = Path("third_party/Hunyuan3D-2/hy3dgen/shapegen/pipelines.py")
s = p.read_text()

backup = p.with_suffix(".py.backup_before_fix_before_mesh_v3")
backup.write_text(s)
print("[OK] backup:", backup)

# Remove old unsafe clone if it still exists.
unsafe_pattern = re.compile(
    r'\n(?P<indent>[ \t]+)try:\n'
    r'(?P=indent)[ \t]+foho_obj_mesh_before_phase42 = foho_clone_p3d_mesh\(transformed_obj_mesh\)\n'
    r'(?P=indent)except Exception as e:\n'
    r'(?P=indent)[ \t]+foho_obj_mesh_before_phase42 = None\n'
    r'(?P=indent)[ \t]+print\(f"\[FOHO_INTERNAL_SELECTOR_AUTO\] failed to save before_phase42 mesh: \{e\}"\)\n'
)

s, n_removed = unsafe_pattern.subn(
    '\n                            # Mesh clone is saved later, after transformed_obj_mesh exists.\n',
    s,
    count=1,
)
print(f"[OK] removed unsafe clone blocks: {n_removed}")

if "saved before_phase42 mesh at step" in s:
    print("[OK] safe clone already exists")
    p.write_text(s)
    raise SystemExit(0)

# Match the transformed_obj_mesh line even with trailing spaces.
assign_pattern = re.compile(
    r'(?P<line>^(?P<indent>[ \t]*)transformed_obj_mesh\s*=\s*transform_mesh_around_center_w_scale\(moge_obj_mesh,\s*RT_obj,\s*scale_obj\)\s*$)',
    re.MULTILINE,
)

matches = list(assign_pattern.finditer(s))
if not matches:
    raise RuntimeError("No transformed_obj_mesh assignment found.")

# Use the first object-stage assignment.
m = matches[0]
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

s = s[:insert_pos] + safe_block + s[insert_pos:]
p.write_text(s)

print("[OK] inserted safe clone after first transformed_obj_mesh assignment")
print("[OK] wrote", p)
