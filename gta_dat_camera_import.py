bl_info = {
    "name": "GTA SA Cutscene Camera (.dat) Importer",
    "blender": (3, 6, 23),
    "category": "Import-Export",
    "author": "Tatara Hisoka",
    "version": (1, 0),
    "description": "Imports GTA San Andreas cutscene camera .dat files as Blender cameras",
}

import bpy
import math
from bpy.props import StringProperty
from bpy_extras.io_utils import ImportHelper
from bpy.props import BoolProperty, EnumProperty

# ---------------------------
# FOV Conversion
# ---------------------------
def fov_to_blender_lens(fov_deg, sensor_width=36.0):
    fov_rad = math.radians(fov_deg)
    return (sensor_width / 2) / math.tan(fov_rad / 2)

# ---------------------------
# Parser
# ---------------------------
def parse_dat(path):
    blocks = []
    with open(path, "r", errors="ignore") as f:
        data = f.read().replace("f", "")
    sections = data.split(";")
    for sec in sections:
        lines = [l.strip() for l in sec.splitlines() if l.strip()]
        if not lines:
            continue
        count_line = lines[0].replace(",", "").strip()
        try:
            count = int(count_line)
        except:
            continue
        entries = []
        for line in lines[1:]:
            nums = [float(x) for x in line.split(",") if x]
            if nums:
                entries.append(nums)
        blocks.append(entries)
    return blocks

# ---------------------------
# Interpolation
# ---------------------------
def lerp(a, b, t):
    return a + (b - a) * t

def expand_block(block, fps):
    if not block:
        return []
    frames = []
    for i in range(len(block)-1):
        t0, *v0 = block[i]
        t1, *v1 = block[i+1]
        nframes = round((t1 - t0) * fps)
        if nframes <= 0:
            continue
        for f in range(nframes):
            factor = f / nframes
            frame_vals = [lerp(v0[j], v1[j], factor) for j in range(len(v0))]
            frames.append((len(frames), t0 + f/fps, frame_vals))
    frames.append((len(frames), block[-1][0], block[-1][1:]))
    return frames

def cleanup_redundant_keys(obj):
    """Remove duplicate keyframes but keep first and last of still sections."""
    if not obj.animation_data or not obj.animation_data.action:
        return
    for fc in obj.animation_data.action.fcurves:
        kps = fc.keyframe_points
        if len(kps) < 3:
            continue

        to_remove = []
        prev_val = None
        still_start = None

        for i, kp in enumerate(kps):
            val = kp.co[1]

            if prev_val is None or val != prev_val:
                # value changed
                if still_start is not None and i - still_start > 1:
                    # mark middle duplicates for removal
                    to_remove.extend(range(still_start+1, i-1))
                still_start = i
            prev_val = val

        # handle last segment
        if still_start is not None and len(kps) - still_start > 2:
            to_remove.extend(range(still_start+1, len(kps)-1))

        # actually remove keys (reverse order so indices stay valid)
        for idx in sorted(set(to_remove), reverse=True):
            kps.remove(kps[idx])

        kps.update()

# ---------------------------
# Operator
# ---------------------------
class IMPORT_OT_gta_sa_dat(bpy.types.Operator, ImportHelper):
    bl_idname = "import_scene.gta_sa_dat"
    bl_label = "Import GTA SA Camera (.dat)"
    bl_options = {"REGISTER", "UNDO"}

    filename_ext = ".dat"
    filter_glob: StringProperty(default="*.dat", options={'HIDDEN'})

    optimize_keyframe: BoolProperty(
        name="Optimize Keyframes",
        description="Remove redundant duplicate keyframes (keep only first & last)",
        default=True
    )

    block_import: EnumProperty(
        name="Block Import",
        description="Choose which lane to import (Default or unused)",
        items=[
            ('DEFAULT', "Default (Lane 1)", ""),
            ('UNUSED1', "Unused 1 (Lane 2)", ""),
            ('UNUSED2', "Unused 2 (Lane 3)", ""),
        ],
        default='DEFAULT'
    )

    def execute(self, context):
        dat_path = self.filepath
        fps = 60  # GTA SA fixed playback FPS
        scene = context.scene
        scene.render.fps = fps
        lane_index = 0
        if self.block_import == 'UNUSED1':
            lane_index = 1
        elif self.block_import == 'UNUSED2':
            lane_index = 2
            
        # Clean old objects
        for obj in scene.objects:
            if obj.name.startswith("CutsceneCam") or obj.name.startswith("Target"):
                bpy.data.objects.remove(obj, do_unlink=True)

        # Create new camera + target
        cam_data = bpy.data.cameras.new("CutsceneCam")
        cam_obj = bpy.data.objects.new("CutsceneCam", cam_data)
        context.collection.objects.link(cam_obj)

        target = bpy.data.objects.new("Target", None)
        context.collection.objects.link(target)

        constraint = cam_obj.constraints.new(type='TRACK_TO')
        constraint.target = target
        constraint.track_axis = 'TRACK_NEGATIVE_Z'
        constraint.up_axis = 'UP_Y'
        constraint.owner_space = 'LOCAL'
        constraint.target_space = 'LOCAL'

        # Parse file
        blocks = parse_dat(dat_path)
        rotation_data = blocks[0] if len(blocks) > 0 else []
        zoom_data     = blocks[1] if len(blocks) > 1 else []
        pos_data      = blocks[2] if len(blocks) > 2 else []
        target_data   = blocks[3] if len(blocks) > 3 else []

        pos_frames    = expand_block(pos_data, fps)
        target_frames = expand_block(target_data, fps)
        fov_frames    = expand_block(rotation_data, fps)
        rot_frames    = expand_block(zoom_data, fps)

        total_frames = max(len(pos_frames), len(target_frames), len(fov_frames), len(rot_frames))
        scene.frame_start = 0
        scene.frame_end = total_frames

        # Insert animation
        for f in range(total_frames):
            if f < len(pos_frames):
                _, _, pos = pos_frames[f]
                cam_obj.location = (pos[lane_index*3], pos[lane_index*3+1], pos[lane_index*3+2])
                cam_obj.keyframe_insert("location", frame=f)

            if f < len(target_frames):
                _, _, tgt = target_frames[f]
                target.location = (tgt[lane_index*3], tgt[lane_index*3+1], tgt[lane_index*3+2])
                target.keyframe_insert("location", frame=f)

            if f < len(fov_frames):
                _, _, fov = fov_frames[f]
                cam_data.lens = fov_to_blender_lens(fov[lane_index])
                cam_data.keyframe_insert("lens", frame=f)

            if f < len(rot_frames):
                _, _, rot = rot_frames[f]
                cam_obj.rotation_euler[1] = math.radians(rot[lane_index])
                cam_obj.keyframe_insert("rotation_euler", frame=f)
                target.rotation_euler[1] = math.radians(rot[lane_index])
                target.keyframe_insert("rotation_euler", frame=f)

        # Set interpolation to LINEAR
        for obj in [cam_obj, target]:
            for fc in obj.animation_data.action.fcurves:
                for kp in fc.keyframe_points:
                    kp.interpolation = 'LINEAR'
        # Clean duplicates: keep only first & last of identical sections
        if self.optimize_keyframe:
            for obj in [cam_obj, target]:
                cleanup_redundant_keys(obj)
            # also clean FOV (lens fcurve lives in cam_data)
            if cam_data.animation_data and cam_data.animation_data.action:
                for fc in cam_data.animation_data.action.fcurves:
                    cleanup_redundant_keys(cam_data)
        self.report({'INFO'}, f"Imported GTA SA cutscene ({total_frames} frames at {fps} fps)")
        return {'FINISHED'}

# ---------------------------
# Menu
# ---------------------------
def menu_func_import(self, context):
    self.layout.operator(IMPORT_OT_gta_sa_dat.bl_idname, text="GTA SA Cutscene Camera (.dat)")

def register():
    bpy.utils.register_class(IMPORT_OT_gta_sa_dat)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)

def unregister():
    bpy.utils.unregister_class(IMPORT_OT_gta_sa_dat)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)

if __name__ == "__main__":
    register()
