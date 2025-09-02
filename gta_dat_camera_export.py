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
from mathutils import Vector
from bpy.props import StringProperty, BoolProperty
from bpy_extras.io_utils import ExportHelper

# ---------------------------
# Helpers
# ---------------------------
def get_roll_from_object(cam_obj):
    """Compute camera roll in degrees from a Blender camera object."""
    mat = cam_obj.matrix_world

    # Camera forward (-Z in Blender) and up (+Y)
    forward = -mat.col[2].xyz.normalized()
    up = mat.col[1].xyz.normalized()

    # World up
    world_up = Vector((0, 0, 1))

    # Project camera up onto plane perpendicular to forward
    proj = (up - forward * up.dot(forward)).normalized()

    # Roll angle
    roll_rad = math.atan2(proj.cross(world_up).dot(forward), proj.dot(world_up))
    return math.degrees(roll_rad)
    
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

def get_anim_data(cam_obj, target_obj, cam_data, fps):
    """Sample camera animation frame-by-frame, adjust timeoffset for GTA export."""
    start = bpy.context.scene.frame_start
    end = bpy.context.scene.frame_end

    fovs, rots, poss, tgts = [], [], [], []

    for f in range(start, end + 1):
        bpy.context.scene.frame_set(f)
        t = (f - start) / fps

        # FOV
        fov = get_fov_deg(cam_data)
        fovs.append((t, fov, 0, 0))

        # Rotation (Roll)
        # TODO : roll are incorrect without target_obj, need fix this
        if target_obj:
            rot = math.degrees(cam_obj.rotation_euler[1])
        else:
            rot = get_roll_from_object(cam_obj)
        rots.append((t, rot, 0, 0))

        # Camera Position
        x, y, z = cam_obj.location
        poss.append((t, x, y, z, 0, 0, 0, 0, 0, 0))

        # Target Position
        if target_obj:
            tx, ty, tz = target_obj.location
        else:
            forward = cam_obj.matrix_world.to_quaternion() @ mathutils.Vector((0, 0, -1))
            tx, ty, tz = cam_obj.location + forward * 1.0
        tgts.append((t, tx, ty, tz, 0, 0, 0, 0, 0, 0))

    return fovs, rots, poss, tgts

def write_dat(path, fovs, rots, poss, tgts):
    with open(path, "w") as f:
        # Block1: FOV
        f.write(f"{len(fovs)},\n")
        for t, v1, _, _ in fovs:
            f.write(f"{t:.9f}f,{v1:.9f},0,0,\n")
        f.write(";\n")

        # Block2: Rotation
        f.write(f"{len(rots)},\n")
        for t, v1, _, _ in rots:
            f.write(f"{t:.9f}f,{v1:.9f},0,0,\n")
        f.write(";\n")

        # Block3: Camera Position
        f.write(f"{len(poss)},\n")
        for t, x,y,z,_,_,_,_,_,_ in poss:
            f.write(f"{t:.9f}f,{x:.9f},{y:.9f},{z:.9f},0,0,0,0,0,0,\n")
        f.write(";\n")

        # Block4: Target Position
        f.write(f"{len(tgts)},\n")
        for t, x,y,z,_,_,_,_,_,_ in tgts:
            f.write(f"{t:.9f}f,{x:.9f},{y:.9f},{z:.9f},0,0,0,0,0,0,\n")
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
