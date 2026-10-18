@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Install Python 3.11-3.13 from https://www.python.org/downloads/windows/
  echo Select Add Python to PATH and include Tcl/Tk.
  pause
  exit /b 1
)
py -3 -m pip install --upgrade pyinstaller
if errorlevel 1 goto failed
py -3 -m PyInstaller --noconfirm --clean --windowed --onefile --icon "MinecraftStickyNotes.ico" --name MinecraftStickyNotes MinecraftStickyNotes.pyw
if errorlevel 1 goto failed
echo.
echo BUILD COMPLETE: dist\MinecraftStickyNotes.exe
echo The custom notebook icon is embedded in the EXE.
echo Run the EXE from a permanent folder. In the note menu choose Start with Windows to enable auto-start.
echo Right-click the EXE to pin it to your taskbar for one-click launching.
pause
exit /b 0
:failed
echo Build failed. Check the error above.
pause
exit /b 1
