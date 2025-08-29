import bpy
import math


# ---------------------------
# CONFIG
# ---------------------------
dat_path = r"D:\Games\GTA San Andreas\anim\z\intro1a (2).dat"
project_fps = 60  # target FPS (inputed)
# ---------------------------

# Set scene FPS
bpy.context.scene.render.fps = project_fps

# Clean old objects
for obj in bpy.context.scene.objects:
    if obj.name.startswith("CutsceneCam") or obj.name.startswith("Target"):
        bpy.data.objects.remove(obj, do_unlink=True)

# Create new camera and target empty
cam_data = bpy.data.cameras.new("CutsceneCam")
cam_obj = bpy.data.objects.new("CutsceneCam", cam_data)
bpy.context.collection.objects.link(cam_obj)

target = bpy.data.objects.new("Target", None)
bpy.context.collection.objects.link(target)

# Make camera look at target
constraint = cam_obj.constraints.new(type='TRACK_TO')
constraint.target = target
constraint.track_axis = 'TRACK_NEGATIVE_Z'
constraint.up_axis = 'UP_Y'


# ---------------------------
# PARSE .DAT FILE
# ---------------------------
def parse_dat(path):
    blocks = []
    with open(path, "r", errors="ignore") as f:
        data = f.read().replace("f", "")  # remove 'f' suffix
    sections = data.split(";")  # each block ends with ;
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


blocks = parse_dat(dat_path)

rotation_data = blocks[0] if len(blocks) > 0 else []
zoom_data     = blocks[1] if len(blocks) > 1 else []
pos_data      = blocks[2] if len(blocks) > 2 else []
target_data   = blocks[3] if len(blocks) > 3 else []

print(f"Parsed: {len(rotation_data)} rot, {len(zoom_data)} zoom, {len(pos_data)} pos, {len(target_data)} target")

# ---------------------------
# FOV
# ---------------------------
def fov_to_blender_lens(fov_deg, sensor_width=36.0):
    """Convert GTA FoV (deg) to Blender camera lens (mm)."""
    fov_rad = math.radians(fov_deg)
    return (sensor_width / 2) / math.tan(fov_rad / 2)

# ---------------------------
# INTERPOLATION HELPERS
# ---------------------------
def lerp(a, b, t):
    return a + (b - a) * t

def interpolate(block, t):
    """Linear interpolation of block data at time t."""
    if not block:
        return None

    # before first key
    if t <= block[0][0]:
        return block[0][1:]

    # after last key
    if t >= block[-1][0]:
        return block[-1][1:]

    # find two keys around t
    for i in range(len(block)-1):
        t0, *v0 = block[i]
        t1, *v1 = block[i+1]
        if t0 <= t <= t1:
            factor = (t - t0) / (t1 - t0) if (t1 - t0) != 0 else 0
            return [lerp(v0[j], v1[j], factor) for j in range(len(v0))]

    return block[-1][1:]


# ---------------------------
# RESAMPLING + ANIMATION
# ---------------------------
# Get total duration from longest block
def get_last_time(block):
    return block[-1][0] if block else 0.0

duration = max(
    get_last_time(pos_data),
    get_last_time(target_data),
    get_last_time(zoom_data),
    get_last_time(rotation_data)
)

total_frames = round(duration * project_fps)
print(f"Resampling {duration:.2f}s → {total_frames} frames at {project_fps} fps")

for f in range(total_frames + 1):
    t = f / project_fps

    # Camera Position (Block3)
    pos = interpolate(pos_data, t)
    if pos:
        cam_obj.location = (pos[0], pos[1], pos[2])
        cam_obj.keyframe_insert(data_path="location", frame=f)

    # Target Position (Block4)
    tgt = interpolate(target_data, t)
    if tgt:
        target.location = (tgt[0], tgt[1], tgt[2])
        target.keyframe_insert(data_path="location", frame=f)

    # Zoom / FOV
    fov = interpolate(rotation_data, t)  # from Block1 actually
    if fov:
        cam_data.lens = fov_to_blender_lens(fov[0])
        cam_data.keyframe_insert(data_path="lens", frame=f)

    # Rotation (Block1)
    # rot = interpolate(rotation_data, t)
    # if rot:
        # cam_obj.rotation_euler[2] = rot[0]  # Z roll
        # cam_obj.keyframe_insert(data_path="rotation_euler", frame=f)


print("✅ Import complete! Cutscene camera resampled at fixed fps.")
