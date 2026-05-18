# T-Metric Voicemail Manager

A small Windows desktop app for working through T-Metrics voicemail downloads without constantly digging through File Explorer.

The app watches the T-Metrics download folder, copies new voicemail WAV files into its own workspace, and gives you a cleaner queue for listening, reviewing, renaming, deleting, and taking notes.

## What It Does

- Watches the T-Metrics voicemail download folder for new `.wav` files.
- Copies voicemail files into an app-managed workspace under AppData.
- Lets you listen to voicemails with a waveform progress bar.
- Saves notes next to each voicemail.
- Tracks reviewed voicemails and can hide them from the list.
- Can keep the manager window always on top.
- Can restore the T-Metrics message popup when it appears.
- Can auto-close the T-Metrics download folder window after new files arrive.
- Supports custom notification sounds.
- Includes dark, light, and cartoon themes.

## App Folders

The app uses these folders:

```text
%APPDATA%\T-Metrics, Inc\ACD Agent Module\Downloads
```

T-Metrics download source folder.

```text
%APPDATA%\T-Metrics, Inc\VoicemailManager\Voicemail_Workspace
```

App workspace for copied voicemail files and notes.

```text
%APPDATA%\T-Metrics, Inc\VoicemailManager\Voicemail_Sounds
```

Notification sound folder. Add `.wav`, `.mp3`, `.flac`, or `.ogg` files here and they will appear in Settings.

## Using The App

Run the app and leave it open while T-Metrics is downloading voicemails.

New voicemail files appear in the list automatically. Selecting one loads the audio. Press the play button to listen. Once a voicemail is played, it is marked reviewed.

Use the text box on the right for notes. Notes are saved automatically.

The bottom buttons handle common voicemail actions:

- `Rename`: rename the selected voicemail.
- `Mark Unreviewed`: remove the reviewed status.
- `Delete`: move the selected voicemail to deleted storage for up to 30 days.
- `Delete All`: move all workspace voicemails to deleted storage for up to 30 days.

## Settings

Open Settings from the gear button in the top-right corner.

Settings are saved immediately when changed. There is no separate save step.

Available settings:

- `Audio Output`: choose the device used for voicemail playback and notification sounds.
- `Notification Sound`: choose the sound played when the T-Metrics popup is restored.
- Play button beside notification sound: preview the selected notification sound.
- Folder button beside notification sound: open the custom notification sounds folder.
- `Theme`: choose dark, light, or cartoon mode.
- `Recover Deleted Voicemails`: restore a voicemail that was deleted within the last 30 days.
- `Include .txt Note In Drag And Drop`: when enabled, dragging a voicemail also includes its note file.
- `Ask Before Deleting Voicemails`: controls whether delete actions show a confirmation prompt each time.
- `Open T-Metric Ringtones Folder`: open `%APPDATA%\T-Metrics, Inc\SIP Softphone\Ringtones` so `.wav` ringtone files can be added.
- `Feature Information`: open the in-app feature guide.
- `Open T-Metric Voicemail Folder`: open the original T-Metrics download folder.

The `Default Sound` notification option plays the bundled `restore_sound.wav`.

## Development Setup

This project uses Python and PyQt6.

Create a virtual environment:

```powershell
python -m venv .venv
```

Install dependencies:

```powershell
.\.venv\Scripts\pip.exe install -r requirements.txt
```

Run the app:

```powershell
.\.venv\Scripts\python.exe main.py
```

If the global `python` command opens the Microsoft Store or fails, use the venv interpreter directly as shown above.

## Build The EXE

Build with PyInstaller:

```powershell
.\.venv\Scripts\pyinstaller.exe --clean "T-Metric Voicemail Manager.spec"
```

The built app will be created under:

```text
dist\T-Metric Voicemail Manager.exe
```

The spec file bundles:

- `URMC.ico`
- `restore_sound.wav`
- `default_sounds`
- `assets`

The app is built as a windowed application, so it should not open a terminal window when launched.

## Notes For Maintenance

- Main entry point: `main.py`
- Main window and app behavior: `manager.py`
- Dialogs and custom widgets: `ui_components.py`
- Paths, styles, and constants: `constants.py`
- PyInstaller build config: `T-Metric Voicemail Manager.spec`

When adding new visual assets, place them under `assets` so PyInstaller includes them.

When adding default notification sounds, place them under `default_sounds`. On startup, the app copies missing default sounds into the user's AppData notification sound folder.
