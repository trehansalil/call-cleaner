"""Print the exact native-Termux setup steps for scheduling.

Two wrapper templates: one for native Termux (direct call) and one for
PRoot Ubuntu (proot-distro login wrapper). Choice is based on the runtime
$PREFIX env var, with a `force` override for testing.
"""
from __future__ import annotations

from . import paths as paths_mod

WRAPPER_PROOT_SH = """\
#!/data/data/com.termux/files/usr/bin/bash
exec proot-distro login ubuntu --shared-tmp -- \\
  /usr/local/bin/cleaner run --preset default >> ~/cleaner.log 2>&1
"""

WRAPPER_PROOT_PURGE_SH = """\
#!/data/data/com.termux/files/usr/bin/bash
exec proot-distro login ubuntu --shared-tmp -- \\
  /usr/local/bin/cleaner purge >> ~/cleaner.log 2>&1
"""

WRAPPER_TERMUX_SH = """\
#!/data/data/com.termux/files/usr/bin/bash
exec $PREFIX/bin/cleaner run --preset default >> ~/cleaner.log 2>&1
"""

WRAPPER_TERMUX_PURGE_SH = """\
#!/data/data/com.termux/files/usr/bin/bash
exec $PREFIX/bin/cleaner purge >> ~/cleaner.log 2>&1
"""


def render(*, force: str | None = None) -> str:
    """Return the install-schedule shell snippet for the active env.

    `force` may be 'termux' or 'proot' to override env detection (used in tests).
    """
    if force == "termux":
        is_termux = True
    elif force == "proot":
        is_termux = False
    else:
        is_termux = paths_mod.is_termux()

    if is_termux:
        run_body = WRAPPER_TERMUX_SH
        purge_body = WRAPPER_TERMUX_PURGE_SH
    else:
        run_body = WRAPPER_PROOT_SH
        purge_body = WRAPPER_PROOT_PURGE_SH

    pkg_line = "pkg install termux-api" if is_termux else "pkg install termux-api proot-distro"
    return f"""\
# Run these commands in NATIVE TERMUX (not inside PRoot Ubuntu).

{pkg_line}
mkdir -p ~/.shortcuts

# Run trampoline:
cat > ~/.shortcuts/call-cleaner.sh <<'WRAPPER'
{run_body}WRAPPER
chmod +x ~/.shortcuts/call-cleaner.sh

# Purge trampoline:
cat > ~/.shortcuts/call-cleaner-purge.sh <<'WRAPPER'
{purge_body}WRAPPER
chmod +x ~/.shortcuts/call-cleaner-purge.sh

# Schedule both daily:
termux-job-scheduler --script ~/.shortcuts/call-cleaner.sh \\
  --period-ms 86400000 --persisted true --network unmetered
termux-job-scheduler --script ~/.shortcuts/call-cleaner-purge.sh \\
  --period-ms 86400000 --persisted true
"""
