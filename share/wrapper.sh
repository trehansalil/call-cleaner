#!/data/data/com.termux/files/usr/bin/bash
exec proot-distro login ubuntu --shared-tmp -- \
  /usr/local/bin/cleaner run --preset default >> ~/cleaner.log 2>&1
