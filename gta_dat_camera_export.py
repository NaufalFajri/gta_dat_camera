bl_info = {
    "name": "GTA SA Cutscene Camera (.dat) Exporter",
    "blender": (3, 6, 23),
    "category": "Import-Export",
    "author": "Tatara Hisoka",
    "version": (1, 0),
    "description": "Exports Blender camera + target animation to GTA San Andreas cutscene .dat",
}

import bpy
import math
import mathutils
from bpy.props import StringProperty, BoolProperty
from bpy_extras.io_utils import ExportHelper

# ---------------------------
# Helpers
# ---------------------------
def optimize(block):
    """Remove duplicate values but keep first and last in still sections."""
    if not block:
        return []

    optimized = [block[0]]
    prev_vals = tuple(block[0][1:])
    still_start = 0

    for i in range(1, len(block)):
        vals = tuple(block[i][1:])
        if vals != prev_vals:
            # value changed → keep previous as "end of still section"
            if i - still_start > 1:
                optimized.append(block[i-1])
            optimized.append(block[i])
            still_start = i
        prev_vals = vals

    # ensure last entry is kept
    if optimized[-1] != block[-1]:
        optimized.append(block[-1])

    return optimized


def get_anim_data(cam_obj, target_obj, cam_data, fps):
    """Sample camera animation frame-by-frame, adjust timeoffset for GTA export."""
    start = bpy.context.scene.frame_start
    end = bpy.context.scene.frame_end

    fovs, rots, poss, tgts = [], [], [], []

    for f in range(start, end + 1):
        bpy.context.scene.frame_set(f)
        t = (f - start) / fps

        # GTA expects ~30fps time, but Blender scene is 60fps → halve timeoffset
        t /= 2.0

        # FOV
        fov = math.degrees(cam_data.angle)
        fovs.append((t, fov, fov, fov))

        # Rotation (roty)
        rot = math.degrees(cam_obj.rotation_euler[1])
        rots.append((t, rot, rot, rot))

        # Camera Position
        x, y, z = cam_obj.location
        poss.append((t, x, y, z, x, y, z, x, y, z))

        # Target Position
        if target_obj:
            tx, ty, tz = target_obj.location
        else:
            forward = cam_obj.matrix_world.to_quaternion() @ mathutils.Vector((0, 0, -1))
            tx, ty, tz = cam_obj.location + forward * 1.0
        tgts.append((t, tx, ty, tz, tx, ty, tz, tx, ty, tz))

    return fovs, rots, poss, tgts

def write_dat(path, fovs, rots, poss, tgts):
    with open(path, "w") as f:
        # Block1: FOV
        f.write(f"{len(fovs)},\n")
        for t, v1, v2, v3 in fovs:
            f.write(f"{t:.6f}f,{v1:.6f},{v2:.6f},{v3:.6f},\n")
        f.write(";\n")

        # Block2: Rotation
        f.write(f"{len(rots)},\n")
        for t, v1, v2, v3 in rots:
            f.write(f"{t:.6f}f,{v1:.6f},{v2:.6f},{v3:.6f},\n")
        f.write(";\n")

        # Block3: Camera Position
        f.write(f"{len(poss)},\n")
        for t, x,y,z,_,_,_,_,_,_ in poss:
            f.write(f"{t:.6f}f,{x:.6f},{y:.6f},{z:.6f},{x:.6f},{y:.6f},{z:.6f},{x:.6f},{y:.6f},{z:.6f},\n")
        f.write(";\n")

        # Block4: Target Position
        f.write(f"{len(tgts)},\n")
        for t, x,y,z,_,_,_,_,_,_ in tgts:
            f.write(f"{t:.6f}f,{x:.6f},{y:.6f},{z:.6f},{x:.6f},{y:.6f},{z:.6f},{x:.6f},{y:.6f},{z:.6f},\n")
        f.write(";\n")

    print(f"✅ Exported cutscene to {path}")

# ---------------------------
# Operator
# ---------------------------
class EXPORT_OT_gta_sa_dat(bpy.types.Operator, ExportHelper):
    bl_idname = "export_scene.gta_sa_dat"
    bl_label = "Export GTA SA Camera (.dat)"
    filename_ext = ".dat"

    filter_glob: StringProperty(default="*.dat", options={'HIDDEN'})
    optimize_export: BoolProperty(
        name="Optimize Export",
        description="Remove redundant duplicate keyframes (keep only first & last)",
        default=True
    )

    def execute(self, context):
        cam_obj = bpy.data.objects.get("CutsceneCam")
        if not cam_obj:
            self.report({'ERROR'}, "No object named CutsceneCam found")
            return {'CANCELLED'}
        cam_data = cam_obj.data
        target_obj = bpy.data.objects.get("Target")

        fps = bpy.context.scene.render.fps
        fovs, rots, poss, tgts = get_anim_data(cam_obj, target_obj, cam_data, fps)

        # Optimize blocks if enabled
        if self.optimize_export:
            fovs = optimize(fovs)
            rots = optimize(rots)
            poss = optimize(poss)
            tgts = optimize(tgts)

        write_dat(self.filepath, fovs, rots, poss, tgts)
        self.report({'INFO'}, f"Exported GTA SA camera to {self.filepath}")
        return {'FINISHED'}

# ---------------------------
# Menu
# ---------------------------
def menu_func_export(self, context):
    self.layout.operator(EXPORT_OT_gta_sa_dat.bl_idname, text="GTA SA Cutscene Camera (.dat)")

def register():
    bpy.utils.register_class(EXPORT_OT_gta_sa_dat)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)

def unregister():
    bpy.utils.unregister_class(EXPORT_OT_gta_sa_dat)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)

if __name__ == "__main__":
    register()
