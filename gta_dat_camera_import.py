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

def convert_block_60fps(block):
    if not block:
        return []

    frames = []
    used = set()

    for entry in block:
        t = entry[0]
        vals = entry[1:]

        frame = int(t * 60)

        while frame in used:
            frame += 1

        used.add(frame)
        frames.append((frame, vals))

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

def fix_scene_change(obj):
    """
    Ensure transform channels stay synchronized.

    If rotation has a key at frame F but location does not,
    copy/move next location key to frame F to avoid interpolation glitches.
    """
    if not obj.animation_data or not obj.animation_data.action:
        return

    action = obj.animation_data.action

    # collect fcurves
    loc_curves = [fc for fc in action.fcurves if fc.data_path == "location"]
    rot_curves = [fc for fc in action.fcurves if fc.data_path == "rotation_euler"]

    if not loc_curves or not rot_curves:
        return

    # gather all frames where rotation keys exist
    rot_frames = set()
    for fc in rot_curves:
        for kp in fc.keyframe_points:
            rot_frames.add(int(kp.co[0]))

    # gather location frames
    loc_frames = set()
    for fc in loc_curves:
        for kp in fc.keyframe_points:
            loc_frames.add(int(kp.co[0]))

    for frame in sorted(rot_frames):
        if frame in loc_frames:
            continue  # already synchronized

        # find next location key
        next_frame = None
        for f in sorted(loc_frames):
            if f > frame:
                next_frame = f
                break

        if next_frame is None:
            continue

        # copy value from next key
        for fc in loc_curves:
            value = fc.evaluate(next_frame)
            fc.keyframe_points.insert(frame, value)

        loc_frames.add(frame)

    # ensure linear interpolation
    for fc in loc_curves:
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'


# ---------------------------
# Operator
# ---------------------------
class IMPORT_OT_gta_sa_dat(bpy.types.Operator, ImportHelper):
    bl_idname = "import_scene.gta_sa_dat"
    bl_label = "Import GTA Camera (.dat)"
    bl_options = {"REGISTER", "UNDO"}

    filename_ext = ".dat"
    filter_glob: StringProperty(default="*.dat", options={'HIDDEN'})

    optimize_keyframe: BoolProperty(
        name="Optimize Keyframes",
        description="Remove redundant duplicate keyframes (keep only first & last) for editing",
        default=True
    )
    fix_scene_change1: BoolProperty(
        name="Fix Scene Change",
        description="Synchronize location and rotation keyframe timings at scene transitions to avoid interpolation glitches",
        default=True
    )
    def execute(self, context):
        dat_path = self.filepath
        fps = 60  # Prefered value, GTA TimeOffset running on 60fps instead 30fps
        scene = context.scene
        scene.render.fps = fps
            
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

        pos_frames    = convert_block_60fps(pos_data)
        target_frames = convert_block_60fps(target_data)
        fov_frames    = convert_block_60fps(rotation_data)
        rot_frames    = convert_block_60fps(zoom_data)

        all_frames = []

        # Camera Position
        for frame, pos in pos_frames:
            cam_obj.location = (pos[0], pos[1], pos[2])
            cam_obj.keyframe_insert("location", frame=frame)
            all_frames.append(frame)

        # Target Position
        for frame, tgt in target_frames:
            target.location = (tgt[0], tgt[1], tgt[2])
            target.keyframe_insert("location", frame=frame)
            all_frames.append(frame)

        # FOV
        for frame, fov in fov_frames:
            cam_data.lens = fov_to_blender_lens(fov[0])
            cam_data.keyframe_insert("lens", frame=frame)
            all_frames.append(frame)

        # Rotation
        for frame, rot in rot_frames:
            cam_obj.rotation_euler[1] = math.radians(rot[0])
            cam_obj.keyframe_insert("rotation_euler", frame=frame)

            target.rotation_euler[1] = math.radians(rot[0])
            target.keyframe_insert("rotation_euler", frame=frame)
            all_frames.append(frame)

        scene.frame_start = 0
        scene.frame_end = max(all_frames) if all_frames else 0


        # Set interpolation to LINEAR
        for obj in [cam_obj, target]:
            for fc in obj.animation_data.action.fcurves:
                for kp in fc.keyframe_points:
                    kp.interpolation = 'LINEAR'
                    
        if self.fix_scene_change1:
            for obj in [cam_obj, target]:
                fix_scene_change(obj)
            if cam_data.animation_data and cam_data.animation_data.action:
                fix_scene_change(cam_data)
                
        # Clean duplicates: keep only first & last of identical sections
        if self.optimize_keyframe:
            for obj in [cam_obj, target]:
                cleanup_redundant_keys(obj)
            # also clean FOV (lens fcurve lives in cam_data)
            if cam_data.animation_data and cam_data.animation_data.action:
                for fc in cam_data.animation_data.action.fcurves:
                    cleanup_redundant_keys(cam_data)
        self.report({'INFO'}, f"Imported GTA cutscene ({scene.frame_end} frames at {fps} fps)")
        return {'FINISHED'}

# ---------------------------
# Menu
# ---------------------------
def menu_func_import(self, context):
    self.layout.operator(IMPORT_OT_gta_sa_dat.bl_idname, text="GTA Cutscene Camera (.dat)")

def register():
    bpy.utils.register_class(IMPORT_OT_gta_sa_dat)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)

def unregister():
    bpy.utils.unregister_class(IMPORT_OT_gta_sa_dat)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)

if __name__ == "__main__":
    register()
