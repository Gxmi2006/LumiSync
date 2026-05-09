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

Copy-Item -Path .\config.toml -Destination .\dist\LumiSync\config.toml -Force

if (Test-Path .\assets) {
  Copy-Item -Path .\assets -Destination .\dist\LumiSync\assets -Recurse -Force
}

Write-Host "Built dist\LumiSync\LumiSync.exe"
Write-Host "Copied config.toml beside the executable"
