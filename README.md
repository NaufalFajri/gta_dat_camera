# GTA Cutscene Camera (.dat) Blender Addon

Blender addon to import and export cutscene camera animation files (`.dat`) for classic 3D-era Grand Theft Auto games (GTA III, Vice City, San Andreas, LCS, VCS).

---

## Features

### Import
- [x] **Camera Position & Target Tracking**: Automatically sets up camera and tracking target constraint (`CutsceneCam` & `Target`).
- [x] **Field of View (FoV)**: Automatically converts GTA cutscene FOV into Blender camera focal length.
- [x] **Camera Roll**: Reads camera roll/rotation.
- [x] **Time Offset to Keyframes**: Converts time offsets directly to a 60 FPS keyframe timeline.
- [x] **Optimize Keyframes**: Removes redundant duplicate keyframes in static camera sections while preserving transition endpoints.
- [x] **Cubic Bézier Curve Interpolation**: Accurate 60 FPS curve sampling matching GTA's in-game engine and handle data.

### Export
- [x] **Camera & Target Coordinates**: Samples camera position and target points frame-by-frame.
- [x] **Field of View (FoV)**: Converts Blender focal length to GTA FOV format.
- [x] **Roll / Rotation**: Exports roll rotation.
- [x] **Position Offset**: Apply custom XYZ position offsets directly on export.
- [x] **Rotation Y Toggle**: Option to export Y rotation block (used in GTA III intro cutscenes).
- [x] **Optimize Export**: Trims identical consecutive frames to minimize `.dat` file size.
- [ ] Hermite Curve Bezier interpolation *(planned)*

### Supported Games
| Game | Import | Export | Notes |
| :--- | :---: | :---: | :--- |
| **GTA III** | :white_check_mark: | :white_check_mark: | Supports Y rotation for intro cutscenes |
| **GTA Vice City** | :white_check_mark: | :white_check_mark: | Full support |
| **GTA San Andreas** | :white_check_mark: | :white_check_mark: | Full support |
| **GTA Liberty City Stories** | :white_check_mark: | :white_check_mark: | Full support |
| **GTA Vice City Stories** | :white_check_mark: | :white_check_mark: | Full support |

---

## Requirements
- **Blender 3.0+** (tested and supported on Blender 3.6 LTS)

---

## Installation

1. **Download**:
   - Download this repository as a `.zip` file from [Releases](https://github.com/NaufalFajri/gta_dat_camera/releases) or click **Code > Download ZIP**.
2. **Install in Blender**:
   - Open Blender.
   - Go to **Edit** > **Preferences** > **Add-ons**.
   - Click **Install...** (or **Install from Disk** in Blender 4.2+).
   - Select the downloaded `.zip` file.
3. **Enable**:
   - Search for **"GTA Cutscene Camera"** in the Add-ons search bar.
   - Check the checkbox to enable **GTA Cutscene Camera (.dat)**.

---

## How to Use

### Importing a Camera (`.dat`)
1. Go to **File** > **Import** > **GTA Cutscene Camera (.dat)**.
2. Select your `.dat` cutscene camera file.
3. Adjust import options if needed:
   - **Interpolation** *(default: Cubic Bézier 60 FPS)*: Sample exact in-game curves at 60 FPS, or choose Linear Keyframes for sparse legacy import.
   - **Optimize Keyframes** *(default: On)*: Cleans up redundant duplicate keyframes on still sections.
4. Click **Import GTA Camera (.dat)**.
5. The importer will:
   - Create `CutsceneCam` (camera object with tracking constraint and keyframed focal length / position).
   - Create `Target` (empty object that the camera tracks).
   - Automatically set scene playback to **60 FPS** matching GTA's time base.

### Exporting to Camera (`.dat`)
1. Ensure your scene has:
   - A camera object named `CutsceneCam`.
   - *(Optional)* An empty object named `Target` for tracking. If no `Target` object is present, the camera's forward direction will be used.
2. Go to **File** > **Export** > **GTA Cutscene Camera (.dat)**.
3. Configure export settings in the file dialog:
   - **Optimize Export** *(default: On)*: Reduces file size by pruning duplicate consecutive frames.
   - **Export Rotation Y** *(default: Off)*: Enable if exporting camera for GTA III intro cutscenes.
   - **Offset Position**: Add XYZ coordinates offset if the scene needs translation in the GTA world space.
4. Click **Export GTA Camera (.dat)**.

---

## License & Credits
- **Author**: Tatara Hisoka, NaufalFajri
