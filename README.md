# Call Cleaner

[![tests](https://github.com/trehansalil/call-cleaner/actions/workflows/test.yml/badge.svg)](https://github.com/trehansalil/call-cleaner/actions/workflows/test.yml)

Sweep old call recordings on your Android phone (`/sdcard/...`) into a 30-day trash, then auto-purge. Designed for OnePlus + other Android phones running Termux. Includes a curses TUI, native scheduling via `termux-job-scheduler`, and Android notifications via Termux:API.

## Install on a OnePlus phone (or any Android with Termux)

Prerequisites:
- [Termux from F-Droid](https://f-droid.org/en/packages/com.termux/) (the Play Store version is unmaintained — must be F-Droid).
- [Termux:API app from F-Droid](https://f-droid.org/en/packages/com.termux.api/) (for notifications).

Then in Termux:

```sh
curl -fsSL https://raw.githubusercontent.com/trehansalil/call-cleaner/main/install.sh | bash
```

The installer will:
1. Verify storage permission.
2. Install Python, git, termux-api.
3. Clone Call Cleaner.
4. Auto-detect known call-recording folders (OnePlus, Samsung, Xiaomi, Google).
5. Offer to register the daily background job.

After install:

```sh
cleaner doctor          # verify health
cleaner scan            # dry-run preview
cleaner run             # actually trash old files
cleaner trash list      # see what's in trash
cleaner trash restore <id>
cleaner tui             # curses interactive UI
```

See [INSTALL.md](INSTALL.md) for manual install steps if you prefer not to curl-pipe.

## What it does

- Scans configured folders on `/sdcard` for audio files older than N days.
- Moves matching files to `/sdcard/.CallCleanerTrash/` with sidecar JSON metadata (so `restore` is just a rename).
- Auto-purges anything in trash for more than 30 days.
- Fires Android notifications on completion (and on low storage).
- Skips runs when battery is low or battery-saver is on.

## Configuration

Lives at `~/.config/call-cleaner/config.toml`. Edit with `cleaner config edit`. Example:

```toml
default_preset = "default"

[trash]
dir = "/sdcard/.CallCleanerTrash"
retention_days = 30

[paths]
calls = "/sdcard/Music/Recordings/Call Recordings"

[[preset.default.rules]]
folder = "@calls"
age_days = 90
action = "trash"

[[preset.aggressive.rules]]
folder = "@calls"
age_days = 14
action = "trash"
```

## Power-user / Linux install (PRoot Ubuntu, generic Linux)

For developers, contributors, or users running inside a `proot-distro` Ubuntu rather than native Termux:

```sh
git clone https://github.com/trehansalil/call-cleaner
cd call-cleaner
python3 -m venv .venv
make dev
make test
make install      # writes /usr/local/{bin,share,lib}
```

Then `cleaner config init && cleaner install-schedule`.

## License

MIT — see [LICENSE](LICENSE).
