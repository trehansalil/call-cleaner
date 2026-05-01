# Changelog

All notable changes to Call Cleaner. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: [SemVer](https://semver.org/).

## [0.2.0] — 2026-05-01

### Added
- Native Termux support (no PRoot required). Install via `curl -fsSL https://raw.githubusercontent.com/trehansalil/call-cleaner/main/install.sh | bash`.
- `notifier.py` — best-effort Termux-API integration: Android notifications on completion, low-storage alert, low-battery / battery-saver run skipping.
- `first_run.py` — auto-detect known call-recording paths (OnePlus, Samsung, Xiaomi, Google Phone). Falls back to interactive line-by-line prompts.
- `install.sh` — Termux-side bootstrap.
- Env-aware `install_schedule` — emits the appropriate wrapper script for native Termux vs PRoot.
- Doctor checks for `termux-notification` reachability and `~/.shortcuts/call-cleaner.sh` presence.
- `Makefile` `install-termux` target writing into `$PREFIX`.
- `Makefile` `release` target for tagged version bumps.
- PyPI release workflow (`.github/workflows/release.yml`) using trusted publishing (OIDC, no token in repo).
- CI `termux-shape` job verifying `make install-termux` produces the expected layout.
- MIT LICENSE.
- INSTALL.md, CHANGELOG.md, RELEASE_RUNBOOK.md.

### Changed
- Dual-target architecture. Existing PRoot install path is unchanged; `paths.is_termux()` is the single env distinction.
- README restructured: Termux install at the top; PRoot install as "Power-user / Linux install".
- `pyproject.toml` expanded with full PyPI metadata (authors, license, classifiers, project URLs, scripts entry).
- `bin/cleaner` shim probes both `/usr/local/lib/call-cleaner` and `$PREFIX/lib/call-cleaner` for the package.

### Unchanged (no breaking changes)
- Trash data model (sidecar JSON shape).
- Config schema.
- Scanner semantics.
- TUI hotkeys.

## [0.1.0] — 2026-04-27

### Added
- Initial PRoot-only release. Sweep + trash + restore + curses TUI + multi-folder presets + scheduling via termux-job-scheduler. 89 tests, all passing in CI.
