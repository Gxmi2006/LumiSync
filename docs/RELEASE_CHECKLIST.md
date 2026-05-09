# Release Checklist

Use this before tagging a public LumiSync release.

## Validation

- Run `python -m compileall lumisync konsl_aura_sync run_lumisync.py run_konsl_aura_sync.py tests`
- Run `python -m unittest discover -s tests`
- Run `python -m lumisync --setup-check`
- Run `python -m lumisync --diagnostics`
- Test `python -m lumisync --test-color 22CCFF`
- Confirm software fallback works with OpenRGB SDK Server stopped
- Confirm OpenRGB reconnects after restarting SDK Server

## Packaging

- Run `.\build.ps1`
- Copy the current `config.toml` beside `dist\LumiSync\LumiSync.exe`
- Run `.\dist\LumiSync\LumiSync.exe --diagnostics`
- Verify tray icon, hotkeys, config reload, and debug overlay

## Documentation

- Update `README.md`
- Update `docs/CONFIGURATION.md` if config changed
- Update `docs/BACKENDS.md` if backend behavior changed
- Update `CHANGELOG.md`
- Add screenshots or GIFs for visible UI changes

## GitHub

- Confirm issue templates still request diagnostics and logs
- Confirm release notes mention known limitations
- Tag with semantic versioning, for example `v0.2.1`
