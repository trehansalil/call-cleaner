# Call Cleaner

Sweep old call recordings on `/sdcard/Music/Recordings/Call Recordings` (and other folders you configure) into a trash directory, with a 30-day retention window. Designed to run inside a `proot-distro` Ubuntu on Termux on a OnePlus phone, with daily scheduling via `termux-job-scheduler`.

## Install (PRoot side)

One-time venv setup (only the first time, so `make` can find pip/pytest):

```sh
cd /root/call-cleaner
python3 -m venv .venv
```

Then:

```sh
make dev          # installs the package in editable mode + pytest
make test         # runs the suite
make install      # copies bin + share + package into /usr/local/
```

## First run

```sh
cleaner config init        # writes ~/.config/call-cleaner/config.toml
cleaner config edit        # tweak folders / ages if needed
cleaner scan               # dry-run preview
cleaner run                # actually trash old files
```

## Restore from trash

```sh
cleaner trash list                # see ids + original paths
cleaner trash restore <id>        # put one back
cleaner trash empty --force       # nuke everything in trash now
```

## Schedule daily runs (native Termux side)

```sh
cleaner install-schedule          # prints exact commands to paste outside PRoot
```

## Health check

```sh
cleaner doctor
```
