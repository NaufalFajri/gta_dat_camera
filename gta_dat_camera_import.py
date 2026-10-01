import bpy
import math
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy_extras.io_utils import ImportHelper

# ---------------------------
# FOV Conversion
# ---------------------------
def fov_to_blender_lens(fov_deg, sensor_width=36.0):
    fov_deg = max(1.0, min(179.0, fov_deg))
    fov_rad = math.radians(fov_deg)
    return (sensor_width / 2.0) / math.tan(fov_rad / 2.0)

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
# Cubic Bézier 60 FPS Sampler
# ---------------------------
def sample_bezier_block_60fps(block, is_3d=False):
    """
    Samples a GTA .dat curve block frame-by-frame at 60 FPS using Cubic Bézier interpolation.
    1D format: [t, point, in_handle, out_handle]
    3D format: [t, px, py, pz, in_x, in_y, in_z, out_x, out_y, out_z]
    """
    if not block:
        return []

    entries = sorted(block, key=lambda x: x[0])
    t_end = entries[-1][0]
    total_frames = int(round(t_end * 60))
    dim = 3 if is_3d else 1

    curr = 0
    max_idx = len(entries) - 1

    samples = []
    for f in range(total_frames + 1):
        t = f / 60.0
        while curr < max_idx - 1 and t > entries[curr + 1][0]:
            curr += 1

        e0 = entries[curr]
        e1 = entries[min(curr + 1, max_idx)]

        t0 = e0[0]
        t1 = e1[0]
        dt = t1 - t0

        p0 = e0[1:1 + dim]
        p1 = e1[1:1 + dim]

        # Camera cut threshold (<= 2 frames at 60fps or exact same timestamp)
        # Immediately switch cleanly to the new shot when time passes t0
        if dt <= 0.035:
            val = p1 if t > t0 else p0
        else:
            u = max(0.0, min(1.0, (t - t0) / dt))
            if is_3d:
                c1 = e0[7:10] if len(e0) >= 10 else p0
                c2 = e1[4:7] if len(e1) >= 10 else p1
            else:
                c1 = [e0[3]] if len(e0) >= 4 else p0
                c2 = [e1[2]] if len(e1) >= 4 else p1

            # Check for cut-marker extreme handles (e.g. 1.7e8)
            if any(abs(x) > 1e5 for x in c1) or any(abs(x) > 1e5 for x in c2):
                val = p1 if t > t0 else p0
            else:
                u2 = u * u
                u3 = u2 * u
                om = 1.0 - u
                om2 = om * om
                om3 = om2 * om
                b0 = om3
                b1 = 3.0 * om2 * u
                b2 = 3.0 * om * u2
                b3 = u3
                if is_3d:
                    val = [b0 * p0[k] + b1 * c1[k] + b2 * c2[k] + b3 * p1[k] for k in range(3)]
                else:
                    val = [b0 * p0[0] + b1 * c1[0] + b2 * c2[0] + b3 * p1[0]]

        samples.append((f, val if is_3d else val[0]))

    return samples

# ---------------------------
# Sparse Linear Fallback
# ---------------------------
def convert_block_60fps(block):
    if not block:
        return []

    frames = []
    used = set()

    for entry in block:
        t = entry[0]
        vals = entry[1:]

        frame = int(round(t * 60))

        while frame in used:
            frame += 1

        used.add(frame)
        frames.append((frame, vals))

    return frames

# ---------------------------
# Keyframe Cleanup & Optimization
# ---------------------------
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

            if prev_val is None or abs(val - prev_val) > 1e-4:
                # value changed
                if still_start is not None and i - still_start > 1:
                    to_remove.extend(range(still_start + 1, i - 1))
                still_start = i
            prev_val = val

        # handle last segment
        if still_start is not None and len(kps) - still_start > 2:
            to_remove.extend(range(still_start + 1, len(kps) - 1))

        # actually remove keys (reverse order so indices stay valid)
        for idx in sorted(set(to_remove), reverse=True):
            kps.remove(kps[idx])

        kps.update()

def apply_fcurve_samples(action, data_path, array_index, samples, interpolation='LINEAR'):
    """
    Fast assignment of keyframe points to an action's fcurve using foreach_set.
    """
    if not samples:
        return None
    fc = action.fcurves.find(data_path, index=array_index)
    if not fc:
        fc = action.fcurves.new(data_path=data_path, index=array_index)

    num = len(samples)
    fc.keyframe_points.add(num)
    flat_co = [0.0] * (num * 2)
    for i, (fr, val) in enumerate(samples):
        flat_co[i * 2] = float(fr)
        flat_co[i * 2 + 1] = float(val)

    fc.keyframe_points.foreach_set('co', flat_co)
    for kp in fc.keyframe_points:
        kp.interpolation = interpolation
    fc.update()
    return fc

# ---------------------------
# Operator
# ---------------------------
class IMPORT_OT_gta_sa_dat(bpy.types.Operator, ImportHelper):
    bl_idname = "import_scene.gta_sa_dat"
    bl_label = "Import GTA Camera (.dat)"
    bl_options = {"REGISTER", "UNDO"}

    filename_ext = ".dat"
    filter_glob: StringProperty(default="*.dat", options={'HIDDEN'})

    interpolation_mode: EnumProperty(
        name="Interpolation",
        description="Choose how camera curve interpolation is calculated",
        items=[
            ('BEZIER_60FPS', "Cubic Bézier (60 FPS)", "Sample exact cubic Bézier curves at 60 FPS (Game-accurate)"),
            ('LINEAR_SPARSE', "Linear Keyframes", "Import sparse keyframes with linear interpolation (legacy)")
        ],
        default='BEZIER_60FPS'
    )

    optimize_keyframe: BoolProperty(
        name="Optimize Keyframes",
        description="Remove redundant duplicate keyframes from static camera sections",
        default=True
    )

    def execute(self, context):
        dat_path = self.filepath
        fps = 60  # Preferred value, GTA cutscenes run on a 60 FPS time base
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

        # Parse file blocks
        blocks = parse_dat(dat_path)
        fov_data    = blocks[0] if len(blocks) > 0 else []
        rot_data    = blocks[1] if len(blocks) > 1 else []
        pos_data    = blocks[2] if len(blocks) > 2 else []
        target_data = blocks[3] if len(blocks) > 3 else []

        all_frames = []

        if self.interpolation_mode == 'BEZIER_60FPS':
            # High-fidelity 60 FPS Cubic Bézier sampling
            pos_samples = sample_bezier_block_60fps(pos_data, is_3d=True)
            tgt_samples = sample_bezier_block_60fps(target_data, is_3d=True)
            fov_samples = sample_bezier_block_60fps(fov_data, is_3d=False)
            rot_samples = sample_bezier_block_60fps(rot_data, is_3d=False)

            # Ensure animation data
            cam_obj.animation_data_create()
            cam_act = bpy.data.actions.new("CutsceneCamAction")
            cam_obj.animation_data.action = cam_act

            target.animation_data_create()
            target_act = bpy.data.actions.new("TargetAction")
            target.animation_data.action = target_act

            cam_data.animation_data_create()
            cam_data_act = bpy.data.actions.new("CamDataAction")
            cam_data.animation_data.action = cam_data_act

            # Camera Position
            if pos_samples:
                apply_fcurve_samples(cam_act, "location", 0, [(fr, p[0]) for fr, p in pos_samples])
                apply_fcurve_samples(cam_act, "location", 1, [(fr, p[1]) for fr, p in pos_samples])
                apply_fcurve_samples(cam_act, "location", 2, [(fr, p[2]) for fr, p in pos_samples])
                all_frames.extend([fr for fr, _ in pos_samples])

            # Target Position
            if tgt_samples:
                apply_fcurve_samples(target_act, "location", 0, [(fr, p[0]) for fr, p in tgt_samples])
                apply_fcurve_samples(target_act, "location", 1, [(fr, p[1]) for fr, p in tgt_samples])
                apply_fcurve_samples(target_act, "location", 2, [(fr, p[2]) for fr, p in tgt_samples])
                all_frames.extend([fr for fr, _ in tgt_samples])

            # FOV (Lens)
            if fov_samples:
                apply_fcurve_samples(cam_data_act, "lens", 0, [(fr, fov_to_blender_lens(v)) for fr, v in fov_samples])
                all_frames.extend([fr for fr, _ in fov_samples])

            # Roll (Rotation Euler Y)
            if rot_samples:
                rot_radians = [(fr, math.radians(v)) for fr, v in rot_samples]
                apply_fcurve_samples(cam_act, "rotation_euler", 1, rot_radians)
                apply_fcurve_samples(target_act, "rotation_euler", 1, rot_radians)
                all_frames.extend([fr for fr, _ in rot_samples])

        else:
            # Sparse linear keyframes (legacy)
            pos_frames    = convert_block_60fps(pos_data)
            target_frames = convert_block_60fps(target_data)
            fov_frames    = convert_block_60fps(fov_data)
            rot_frames    = convert_block_60fps(rot_data)

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

            # Set interpolation to LINEAR
            for obj in [cam_obj, target]:
                if obj.animation_data and obj.animation_data.action:
                    for fc in obj.animation_data.action.fcurves:
                        for kp in fc.keyframe_points:
                            kp.interpolation = 'LINEAR'
            if cam_data.animation_data and cam_data.animation_data.action:
                for fc in cam_data.animation_data.action.fcurves:
                    for kp in fc.keyframe_points:
                        kp.interpolation = 'LINEAR'

        scene.frame_start = 0
        scene.frame_end = max(all_frames) if all_frames else 0

        # Optional clean duplicates on still sections
        if self.optimize_keyframe:
            for obj in [cam_obj, target]:
                cleanup_redundant_keys(obj)
            if cam_data.animation_data and cam_data.animation_data.action:
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
