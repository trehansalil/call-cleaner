# Manual install (Termux)

If you don't want to curl-pipe a script, here are the equivalent steps to run by hand in a Termux session.

## Prerequisites

1. Install [Termux from F-Droid](https://f-droid.org/en/packages/com.termux/). The Play Store version is unmaintained.
2. Install the [Termux:API app from F-Droid](https://f-droid.org/en/packages/com.termux.api/).

## Steps

```sh
# 1. Storage permission (idempotent)
termux-setup-storage

# 2. Required packages
pkg update -y
pkg install -y python git termux-api

# 3. Clone the source
git clone https://github.com/trehansalil/call-cleaner ~/.cache/call-cleaner-src

# 4. Install into $PREFIX
make -C ~/.cache/call-cleaner-src install-termux

# 5. Auto-detect recording folders + write seed config
python3 -m call_cleaner.first_run --detect

# 6. Register the daily background job (prints commands; copy/paste them)
cleaner install-schedule

# 7. Verify
cleaner doctor
cleaner scan        # dry-run; shows what would be trashed
```

## Troubleshooting

- **`cleaner: command not found`** — Termux's `$PREFIX/bin` should be on `$PATH`; restart the Termux session.
- **`config not found`** — re-run `python3 -m call_cleaner.first_run --detect` or `cleaner config init`.
- **`trash dir not writable`** — re-run `termux-setup-storage` and accept the prompt.
- **No notifications firing** — install the Termux:API Android app from F-Droid; without it, `pkg install termux-api` doesn't fire notifications.
- **`cleaner doctor` reports stale runs** — `termux-job-scheduler` may not have registered. Re-run `cleaner install-schedule` and copy the printed commands.

## Uninstall

```sh
rm -rf ~/.cache/call-cleaner-src
rm $PREFIX/bin/cleaner
rm -rf $PREFIX/share/call-cleaner $PREFIX/lib/call-cleaner
rm -rf ~/.config/call-cleaner ~/.local/share/call-cleaner
rm -rf ~/.shortcuts/call-cleaner*.sh
# Optional: empty trash
rm -rf /sdcard/.CallCleanerTrash
```
