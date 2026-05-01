#!/data/data/com.termux/files/usr/bin/bash
exec proot-distro login ubuntu --shared-tmp -- \
  /usr/local/bin/cleaner purge >> ~/cleaner.log 2>&1
