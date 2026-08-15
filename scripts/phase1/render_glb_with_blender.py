import sys
from pathlib import Path
import bpy
from mathutils import Vector
import math

argv = sys.argv
if "--" not in argv:
    raise SystemExit("Usage: blender -b --python render_glb_with_blender.py -- input.glb output.png")
args = argv[argv.index("--") + 1:]
glb_path = Path(args[0])
out_path = Path(args[1])

bpy.ops.object.delete()

bpy.ops.import_scene.gltf(filepath=str(glb_path))

objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
if not objs:
    raise RuntimeError(f"No mesh objects imported from {glb_path}")

# Compute scene bounding box.
mins = Vector((1e9, 1e9, 1e9))
maxs = Vector((-1e9, -1e9, -1e9))
for obj in objs:
    for corner in obj.bound_box:
        w = obj.matrix_world @ Vector(corner)
        mins.x = min(mins.x, w.x); mins.y = min(mins.y, w.y); mins.z = min(mins.z, w.z)
        maxs.x = max(maxs.x, w.x); maxs.y = max(maxs.y, w.y); maxs.z = max(maxs.z, w.z)

center = (mins + maxs) / 2
size = max((maxs - mins).length, 1e-4)

# Camera.
cam_data = bpy.data.cameras.new("Camera")
cam = bpy.data.objects.new("Camera", cam_data)
bpy.context.collection.objects.link(cam)
cam.location = center + Vector((0, -2.2 * size, 0.8 * size))
direction = center - cam.location
cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
cam_data.lens = 55
bpy.context.scene.camera = cam

# Light.
light_data = bpy.data.lights.new("KeyLight", "AREA")
light = bpy.data.objects.new("KeyLight", light_data)
bpy.context.collection.objects.link(light)
light.location = center + Vector((0, -1.0 * size, 2.0 * size))
light_data.energy = 600
light_data.size = 5

# Render settings.
bpy.context.scene.render.resolution_x = 900
bpy.context.scene.render.resolution_y = 700
bpy.context.scene.eevee.taa_render_samples = 64
bpy.context.scene.render.image_settings.file_format = "PNG"
bpy.context.scene.render.filepath = str(out_path)

out_path.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.render.render(write_still=True)
print("[OK] wrote", out_path)
