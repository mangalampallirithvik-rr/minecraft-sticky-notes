# Minecraft Sticky Notes — Branded Final Edition

This package includes a custom original voxel-inspired notebook icon, designed for this app without Minecraft logos, characters, or copied official assets.

## Features
- Custom app icon embedded into the Windows EXE.
- Floating draggable sticky notes with local autosave.
- Notes don't stay on top of other apps by default; toggle TOP when wanted.
- Startup toggle in the note's ⋯ menu.
- × asks to hide the note, preserving its data; permanent deletion asks for confirmation.
- Hidden-note recovery panel, multiple notes, themes, formatting, checklist, duplicate/delete.
- Notes and layout are stored at `%LOCALAPPDATA%\\MinecraftStickyNotes\\notes.json`.

## Build the Windows EXE
1. Extract the entire ZIP to a permanent folder.
2. Install Python 3.11–3.13 from https://www.python.org/downloads/windows/. Enable **Add Python to PATH** and include Tcl/Tk.
3. Double-click `Build Windows App.bat`.
4. Run `dist\\MinecraftStickyNotes.exe`.
5. Right-click the EXE and pin it to the taskbar. The icon is embedded in the executable.
6. To launch at Windows sign-in, open a note's ⋯ menu and enable **Start with Windows**. Keep the EXE in the same permanent folder after enabling it.

## Files
- `MinecraftStickyNotes.pyw` — application source
- `MinecraftStickyNotes.ico` — original app icon in Windows icon format
- `Build Windows App.bat` — builds a windowed EXE with the icon
- `README.md` — setup instructions

The Python source was syntax-checked. The EXE must be built on Windows and has not been tested on your machine.
