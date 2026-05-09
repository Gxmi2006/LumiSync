$ErrorActionPreference = "Stop"

python -m PyInstaller `
  --noconfirm `
  --clean `
  --name "LumiSync" `
  --windowed `
  --collect-submodules win32com `
  --collect-submodules pycaw `
  --collect-submodules openrgb `
  .\run_lumisync.py
