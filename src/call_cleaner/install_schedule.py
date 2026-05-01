"""Print the exact native-Termux setup steps for scheduling."""
from __future__ import annotations

WRAPPER_SH = """\
#!/data/data/com.termux/files/usr/bin/bash
exec proot-distro login ubuntu --shared-tmp -- \\
  /usr/local/bin/cleaner run --preset default >> ~/cleaner.log 2>&1
"""

WRAPPER_PURGE_SH = """\
#!/data/data/com.termux/files/usr/bin/bash
exec proot-distro login ubuntu --shared-tmp -- \\
  /usr/local/bin/cleaner purge >> ~/cleaner.log 2>&1
"""


def render() -> str:
    return f"""\
# Run these commands in NATIVE TERMUX (not inside PRoot Ubuntu).

pkg install termux-api proot-distro
mkdir -p ~/.shortcuts

# Run trampoline:
cat > ~/.shortcuts/call-cleaner.sh <<'WRAPPER'
{WRAPPER_SH}WRAPPER
chmod +x ~/.shortcuts/call-cleaner.sh

# Purge trampoline:
cat > ~/.shortcuts/call-cleaner-purge.sh <<'WRAPPER'
{WRAPPER_PURGE_SH}WRAPPER
chmod +x ~/.shortcuts/call-cleaner-purge.sh

# Schedule both daily:
termux-job-scheduler --script ~/.shortcuts/call-cleaner.sh \\
  --period-ms 86400000 --persisted true --network unmetered
termux-job-scheduler --script ~/.shortcuts/call-cleaner-purge.sh \\
  --period-ms 86400000 --persisted true
"""
