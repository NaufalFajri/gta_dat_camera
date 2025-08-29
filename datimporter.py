import bpy
import math

# ---------------------------
# CONFIG
# ---------------------------
dat_path = r"D:\Games\GTA San Andreas\anim\dat\intro1a.dat"
project_fps = 60  # GTA SA fixed playback FPS
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
constraint.owner_space = 'LOCAL'
constraint.target_space = 'LOCAL'

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

print(f"Parsed: {len(rotation_data)} rot/FoV, {len(zoom_data)} zoom, {len(pos_data)} pos, {len(target_data)} target")

# ---------------------------
# FOV Conversion
# ---------------------------
def fov_to_blender_lens(fov_deg, sensor_width=36.0):
    """Convert GTA FoV (deg) to Blender camera lens (mm)."""
    fov_rad = math.radians(fov_deg)
    return (sensor_width / 2) / math.tan(fov_rad / 2)

# ---------------------------
# GTA-STYLE EXPANSION
# ---------------------------
def lerp(a, b, t):
    return a + (b - a) * t

def expand_block(block, fps):
    """Expand a .dat block into per-frame values using GTA-style step interpolation."""
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

    # append the last key
    frames.append((len(frames), block[-1][0], block[-1][1:]))
    return frames

# ---------------------------
# BUILD ANIMATION
# ---------------------------
pos_frames    = expand_block(pos_data, project_fps)
target_frames = expand_block(target_data, project_fps)
fov_frames    = expand_block(rotation_data, project_fps)  # Block1 is FoV
rot_frames    = expand_block(zoom_data, project_fps)      # Block2 is rotation if needed

total_frames = max(len(pos_frames), len(target_frames), len(fov_frames), len(rot_frames))
print(f"Expanded into {total_frames} frames at {project_fps} fps")

for f in range(total_frames):
    # Camera Position
    if f < len(pos_frames):
        _, _, pos = pos_frames[f]
        cam_obj.location = (pos[0], pos[1], pos[2])
        cam_obj.keyframe_insert(data_path="location", frame=f)

    # Target Position
    if f < len(target_frames):
        _, _, tgt = target_frames[f]
        target.location = (tgt[0], tgt[1], tgt[2])
        target.keyframe_insert(data_path="location", frame=f)

    # FOV (from Block1)
    if f < len(fov_frames):
        _, _, fov = fov_frames[f]
        cam_data.lens = fov_to_blender_lens(fov[0])
        cam_data.keyframe_insert(data_path="lens", frame=f)

    # Rotation (Block2)
    if f < len(rot_frames):
        _, _, rot = rot_frames[f]
        cam_obj.rotation_euler[1] = math.radians(rot[0])
        cam_obj.keyframe_insert(data_path="rotation_euler", frame=f)
        target.rotation_euler[1] = math.radians(rot[0])
        target.keyframe_insert(data_path="rotation_euler", frame=f)

print("✅ Import complete! Cutscene camera expanded frame-by-frame (GTA-style).")
