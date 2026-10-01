bl_info = {
    "name": "GTA Cutscene Camera (.dat)",
    "author": "Tatara Hisoka, NaufalFajri",
    "version": (1, 0, 0),
    "blender": (3, 6, 0),
    "location": "File > Import / Export",
    "description": "Import and export GTA cutscene camera .dat files",
    "category": "Import-Export",
}

if "bpy" in locals():
    import importlib
    if "gta_dat_camera_import" in locals():
        importlib.reload(gta_dat_camera_import)
    if "gta_dat_camera_export" in locals():
        importlib.reload(gta_dat_camera_export)

import bpy
from . import gta_dat_camera_import
from . import gta_dat_camera_export


def register():
    gta_dat_camera_import.register()
    gta_dat_camera_export.register()


def unregister():
    gta_dat_camera_export.unregister()
    gta_dat_camera_import.unregister()


if __name__ == "__main__":
    register()
