# GTA DAT Camera

Blender Addon for import and export of GTA Camera files. 

## Supported Features
- [X] Import
  - [X] TimeOffset (Blender uses FPS instead of time so the import will be converted to 60fps)
  - [X] FoV
  - [X] Roll
  - [X] Camera Position
  - [X] Target
  - [ ] Hermite Curve Bezier
- [X] Export
  - [X] TimeOffset
  - [X] FoV
  - [X] Roll (from Camera only)
  - [X] Camera Position
  - [X] Target (otherwise use rotation from Camera)
  - [ ] Hermite Curve Bezier
- [X] Version
  - [X] III
  - [X] VC
  - [X] SA
  - [X] LCS
  - [X] VCS
  
## Installation

1. [Download](https://github.com/NaufalFajri/gta_dat_camera/archive/refs/heads/main.zip) the addon zip file from the latest main branch
2. Import the downloaded .zip file by selecting it from *(User) Preferences/Addons/Install from File*
3. Set the addon "GTA SA Cutscene Camera (.dat) Importer" & "GTA SA Cutscene Camera (.dat) Exporter" to enabled
4. Import dat from Import tab	
