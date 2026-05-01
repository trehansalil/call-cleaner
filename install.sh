#!/data/data/com.termux/files/usr/bin/bash
# Call Cleaner — Termux installer.
# Usage:  curl -fsSL https://raw.githubusercontent.com/trehansalil/call-cleaner/main/install.sh | bash
set -euo pipefail

EXPECTED_PREFIX="/data/data/com.termux/files/usr"
SRC_DIR="$HOME/.cache/call-cleaner-src"
REPO_URL="https://github.com/trehansalil/call-cleaner"

err() { printf "ERROR: %s\n" "$*" >&2; exit 1; }
info() { printf ">> %s\n" "$*"; }

# Step 1: env check.
if [ "${PREFIX:-}" != "$EXPECTED_PREFIX" ]; then
    err "This installer runs in Termux only (PREFIX=$EXPECTED_PREFIX expected). For PRoot Ubuntu, see the README's 'Power-user install' section."
fi

# Step 2: storage permission.
info "Granting storage access (idempotent — re-run is safe)..."
if ! command -v termux-setup-storage >/dev/null 2>&1; then
    err "termux-setup-storage not found. Make sure Termux itself is installed from F-Droid."
fi
termux-setup-storage || err "termux-setup-storage failed; please run it interactively and accept the prompt."

# Step 3: install required packages.
info "Installing required packages: python git termux-api..."
pkg update -y
pkg install -y python git termux-api || err "pkg install failed."

# Step 4: clone or update source.
if [ -d "$SRC_DIR/.git" ]; then
    info "Updating existing source at $SRC_DIR..."
    git -C "$SRC_DIR" pull --ff-only || err "git pull failed."
else
    info "Cloning $REPO_URL to $SRC_DIR..."
    git clone "$REPO_URL" "$SRC_DIR" || err "git clone failed."
fi

# Step 5: install into $PREFIX.
info "Running 'make install-termux'..."
make -C "$SRC_DIR" install-termux || err "make install-termux failed."

# Step 6: seed config (auto-detect, fall back to interactive).
info "Seeding config — detecting known recording folders..."
PYTHONPATH="$PREFIX/lib/call-cleaner" python3 -m call_cleaner.first_run --detect \
    || err "config seeding failed; you can run 'cleaner config init' manually later."

# Step 7: print + offer to run schedule setup.
echo
info "Install complete. To finish, you need to register the daily background job."
echo
"$PREFIX/bin/cleaner" install-schedule
echo
read -r -p "Run those commands now? [Y/n] " ans
case "$ans" in
    n|N|no|NO) info "Skipped. Re-run 'cleaner install-schedule' anytime to see them again." ;;
    *)
        info "Setting up daily schedule..."
        TMP=$(mktemp)
        "$PREFIX/bin/cleaner" install-schedule > "$TMP"
        bash "$TMP" || { rm -f "$TMP"; err "schedule setup failed; commands were in $TMP"; }
        rm -f "$TMP"
        info "Done. Verify with: cleaner doctor"
        ;;
esac
