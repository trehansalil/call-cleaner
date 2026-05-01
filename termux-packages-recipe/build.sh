TERMUX_PKG_HOMEPAGE=https://github.com/trehansalil/call-cleaner
TERMUX_PKG_DESCRIPTION="Sweep old call recordings on /sdcard with trash + restore"
TERMUX_PKG_LICENSE="MIT"
TERMUX_PKG_MAINTAINER="@trehansalil"
TERMUX_PKG_VERSION=0.2.0
TERMUX_PKG_SRCURL=https://files.pythonhosted.org/packages/source/c/call-cleaner/call-cleaner-${TERMUX_PKG_VERSION}.tar.gz
TERMUX_PKG_SHA256=__FILL_IN_AFTER_PYPI_PUBLISH__
TERMUX_PKG_DEPENDS="python, termux-api"
TERMUX_PKG_BUILD_IN_SRC=true

termux_step_make_install() {
    pip install . --prefix=$TERMUX_PREFIX
}
