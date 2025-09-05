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
import numpy as np
from mathutils import Vector
from bpy.props import StringProperty, BoolProperty, FloatVectorProperty
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

def get_max_frame(obj):
    scene_end = bpy.context.scene.frame_end
    if not obj or not obj.animation_data or not obj.animation_data.action:
        return scene_end
    frames = [kp.co[0] for fc in obj.animation_data.action.fcurves for kp in fc.keyframe_points]
    return int(max(frames)) if frames else scene_end
    
def get_fov_deg(cam_data):
    aspect = 16 / 9
    if cam_data.sensor_fit == 'VERTICAL':
        # Step 1: compute vertical FOV
        fov_v = 2 * math.atan((cam_data.sensor_height / 2) / cam_data.lens)
        # Step 2: convert to horizontal FOV for 16:9
        fov_h = 2 * math.atan(math.tan(fov_v / 2) * aspect)
        return math.degrees(fov_h)
    else:  # HORIZONTAL or AUTO (treat as horizontal)
        # Direct horizontal FOV
        fov_h = 2 * math.atan((cam_data.sensor_width / 2) / cam_data.lens)
        return math.degrees(fov_h)

def get_anim_data(cam_obj, target_obj, cam_data, fps, offset, roter):
    """Sample camera animation frame-by-frame, adjust timeoffset for GTA export."""
    max_cam = get_max_frame(cam_obj)
    max_tgt = get_max_frame(target_obj)
    start = 0
    end = max(max_cam, max_tgt)
    fovs, rots, poss, tgts = [], [], [], []
    ox, oy, oz = offset
    roter = False
    for f in range(start, end + 1):
        bpy.context.scene.frame_set(f)
        t = (f - start) / fps

        # FOV
        fov = get_fov_deg(cam_data)
        fovs.append((t, fov))

        # Rotation (Roll)
        if roter:
            rot = math.degrees(cam_obj.rotation_euler[1])
        else:
            rot = 0
        rots.append((t, rot))    

        # Camera Position
        x, y, z = cam_obj.location
        poss.append((t, x+ox, y+oy, z+oz))
        
        # Target Position
        if target_obj:
            tx, ty, tz = target_obj.location
        else:
            forward = cam_obj.matrix_world.to_quaternion() @ mathutils.Vector((0, 0, -1))
            tx, ty, tz = cam_obj.location + forward * 1.0
        tgts.append((t, tx+ox, ty+oy, tz+oz))

    return fovs, rots, poss, tgts

def write_dat(path, fovs, rots, poss, tgts):
    with open(path, "w") as f:
        # Block1: FOV
        f.write(f"{len(fovs)},\n")
        for t, v1 in fovs:
            f.write(f"{np.float32(t)}f,{np.float32(v1)},{np.float32(v1)},{np.float32(v1)},\n")
            # f.write(f"{np.float32(t)}f,{np.float32(v1)},0,0,\n")
        f.write(";\n")

        # Block2: Rotation
        f.write(f"{len(rots)},\n")
        for t, v1 in rots:
            f.write(f"{np.float32(t)}f,{np.float32(v1)},{np.float32(v1)},{np.float32(v1)},\n")
            # f.write(f"{np.float32(t)}f,{np.float32(v1)},0,0,\n")
        f.write(";\n")

        # Block3: Camera Position
        f.write(f"{len(poss)},\n")
        for t, x,y,z in poss:
            f.write(f"{np.float32(t)}f,{np.float32(x)},{np.float32(y)},{np.float32(z)},{np.float32(x)},{np.float32(y)},{np.float32(z)},{np.float32(x)},{np.float32(y)},{np.float32(z)},\n")
            # f.write(f"{np.float32(t)}f,{np.float32(x)},{np.float32(y)},{np.float32(z)},0,0,0,0,0,0,\n")
        f.write(";\n")

        # Block4: Target Position
        f.write(f"{len(tgts)},\n")
        for t, x,y,z in tgts:
            f.write(f"{np.float32(t)}f,{np.float32(x)},{np.float32(y)},{np.float32(z)},{np.float32(x)},{np.float32(y)},{np.float32(z)},{np.float32(x)},{np.float32(y)},{np.float32(z)},\n")
            # f.write(f"{np.float32(t)}f,{np.float32(x)},{np.float32(y)},{np.float32(z)},0,0,0,0,0,0,\n")
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
    export_rotation: BoolProperty(
        name="Export Rotation Y",
        description="Export Y-axis rotation block. Used in GTA III intro cutscenes, unused in later GTA titles (VC/SA).",
        default=False
    )
    offsetposition: FloatVectorProperty(
        name="Offset Position",
        description="Offset applied to camera and target positions on export",
        default=(0.0, 0.0, 0.0),
        subtype='TRANSLATION'
    )    
    def execute(self, context):
        cam_obj = bpy.data.objects.get("CutsceneCam")
        if not cam_obj:
            self.report({'ERROR'}, "No object named CutsceneCam found")
            return {'CANCELLED'}
        cam_data = cam_obj.data
        target_obj = bpy.data.objects.get("Target")
        fps = bpy.context.scene.render.fps
        fovs, rots, poss, tgts = get_anim_data(cam_obj, target_obj, cam_data, fps, self.offsetposition, self.export_rotation)
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
