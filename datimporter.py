import bpy

# ---------------------------
# CONFIG
# ---------------------------
dat_path = r"D:\Games\GTA San Andreas\anim\z\intro1a (2).dat"
fps = 60  # playback framerate
# ---------------------------

# Set FPS
bpy.context.scene.render.fps = fps

# Clean old objects (optional)
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

# Expected: 4 blocks
rotation_data = blocks[0] if len(blocks) > 0 else []
zoom_data     = blocks[1] if len(blocks) > 1 else []
pos_data      = blocks[2] if len(blocks) > 2 else []
target_data   = blocks[3] if len(blocks) > 3 else []

print(f"Parsed: {len(rotation_data)} rot, {len(zoom_data)} zoom, {len(pos_data)} pos, {len(target_data)} target")


# ---------------------------
# APPLY ANIMATION
# ---------------------------

# Camera Position (Block3)
for row in pos_data:
    t, x, y, z = row[0], row[1], row[2], row[3]  # only Lane1
    frame = round(t * fps)
    cam_obj.location = (x, y, z)
    cam_obj.keyframe_insert(data_path="location", frame=frame)

# Target Position (Block4)
for row in target_data:
    t, x, y, z = row[0], row[1], row[2], row[3]  # only Lane1
    frame = round(t * fps)
    target.location = (x, y, z)
    target.keyframe_insert(data_path="location", frame=frame)

# Zoom (Block2) - GTA → Blender conversion (*10, with 0 check)
for row in zoom_data:
    t, zoom = row[0], row[1]  # only Lane1
    frame = round(t * fps)
    
    if zoom == 0.0:
        cam_data.lens = 10.0  # fallback value
    else:
        cam_data.lens = zoom * 10.0
    
    cam_data.keyframe_insert(data_path="lens", frame=frame)


# Rotation (Block1) - optional
# If camera already tracks target, this block is usually redundant
# But you could apply roll angle from here if needed
for row in rotation_data:
    t, rot = row[0], row[1]
    frame = round(t * fps)
    cam_obj.rotation_euler[2] = rot  # apply as Z roll (approx)
    cam_obj.keyframe_insert(data_path="rotation_euler", frame=frame)


print("✅ Import complete! Cutscene camera animated at 60 fps.")
