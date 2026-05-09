$ErrorActionPreference = "Stop"

python -m PyInstaller `
  --noconfirm `
  --clean `
  --name "LumiSync" `
  --windowed `
  --specpath ".\build\specs" `
  --collect-submodules win32com `
  --collect-submodules pycaw `
  --collect-submodules openrgb `
  .\run_lumisync.py

python -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --name "LumiSync Setup" `
  --windowed `
  --distpath ".\dist\LumiSync" `
  --workpath ".\build\LumiSyncSetup" `
  --specpath ".\build\specs" `
  .\run_lumisync_setup.py
