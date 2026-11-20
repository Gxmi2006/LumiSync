#!/usr/bin/env sh
# Build a standalone Linux app with PyInstaller: dist/LumiSync/LumiSync
set -e

python3 -m PyInstaller \
  --noconfirm \
  --clean \
  --name "LumiSync" \
  --windowed \
  --collect-submodules openrgb \
  --collect-submodules Xlib \
  ./run_lumisync.py

cp ./config.toml ./dist/LumiSync/config.toml

if [ -d ./assets ]; then
  cp -r ./assets ./dist/LumiSync/assets
fi

echo "Built dist/LumiSync/LumiSync"
echo "Copied config.toml beside the executable"
