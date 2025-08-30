import bpy
import math
import os

# ---------------------------
# CONFIG
# ---------------------------
export_path = r"D:\Games\GTA San Andreas\anim\dat\exported_camera.dat"
fps = bpy.context.scene.render.fps
# sensor_width = 36.0  # must match import
# ---------------------------

# def lens_to_fov(lens, sensor_width=36.0):
    # """Convert Blender lens (mm) back to GTA FoV (degrees)."""
    # return math.degrees(2.0 * math.atan((sensor_width / 2.0) / lens))

def get_anim_data(cam_obj, target_obj, cam_data, fps):
    """Sample camera animation frame-by-frame."""
    start = bpy.context.scene.frame_start
    end = bpy.context.scene.frame_end

    fovs, rots, poss, tgts = [], [], [], []

    for f in range(start, end + 1):
        bpy.context.scene.frame_set(f)
        t = (f - start) / fps  # timeoffset

        # FOV
        fov = fov = math.degrees(cam_data.angle)
        fovs.append((t, fov, fov, fov))

        # Rotation (just export Z roll for now)
        rot = math.degrees(cam_obj.rotation_euler[1])
        rots.append((t, rot, rot, rot))

        # Camera Position
        x, y, z = cam_obj.location
        poss.append((t, x, y, z, x, y, z, x, y, z))

        # Target Position
        tx, ty, tz = target_obj.location
        tgts.append((t, tx, ty, tz, tx, ty, tz, tx, ty, tz))

    return fovs, rots, poss, tgts

# def optimize(block):
    # """Remove duplicate consecutive values, keep time continuity."""
    # optimized = []
    # prev = None
    # for entry in block:
        # vals = tuple(entry[1:])  # skip time
        # if vals != prev:
            # optimized.append(entry)
            # prev = vals
    # return optimized

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
        for t, x,y,z,x,y,z,x,y,z in poss:
            f.write(f"{t:.6f}f,{x:.6f},{y:.6f},{z:.6f},{x:.6f},{y:.6f},{z:.6f},{x:.6f},{y:.6f},{z:.6f},\n")
        f.write(";\n")

        # Block4: Target Position
        f.write(f"{len(tgts)},\n")
        for t, x,y,z,x,y,z,x,y,z in tgts:
            f.write(f"{t:.6f}f,{x:.6f},{y:.6f},{z:.6f},{x:.6f},{y:.6f},{z:.6f},{x:.6f},{y:.6f},{z:.6f},\n")
        f.write(";\n")

    print(f"✅ Exported cutscene to {path}")

# ---------------------------
# RUN EXPORT
# ---------------------------
cam_obj = bpy.data.objects.get("CutsceneCam")
target_obj = bpy.data.objects.get("Target")
cam_data = cam_obj.data

fovs, rots, poss, tgts = get_anim_data(cam_obj, target_obj, cam_data, fps)

# optimize
# fovs = optimize(fovs)
# rots = optimize(rots)
# poss = optimize(poss)
# tgts = optimize(tgts)

# write
write_dat(export_path, fovs, rots, poss, tgts)
