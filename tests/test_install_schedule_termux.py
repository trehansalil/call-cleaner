from call_cleaner import install_schedule


def test_termux_template_when_prefix_set(monkeypatch):
    monkeypatch.setenv("PREFIX", "/data/data/com.termux/files/usr")
    out = install_schedule.render()
    assert "$PREFIX/bin/cleaner run --preset default" in out
    assert "proot-distro login" not in out


def test_proot_template_when_prefix_unset(monkeypatch):
    monkeypatch.delenv("PREFIX", raising=False)
    out = install_schedule.render()
    assert "proot-distro login ubuntu" in out
    assert "/usr/local/bin/cleaner run --preset default" in out


def test_explicit_termux_flag_overrides_env(monkeypatch):
    monkeypatch.delenv("PREFIX", raising=False)  # PRoot env
    out = install_schedule.render(force="termux")
    assert "$PREFIX/bin/cleaner" in out
    assert "proot-distro login" not in out


def test_explicit_proot_flag_overrides_env(monkeypatch):
    monkeypatch.setenv("PREFIX", "/data/data/com.termux/files/usr")  # Termux env
    out = install_schedule.render(force="proot")
    assert "proot-distro login ubuntu" in out
    assert "$PREFIX/bin/cleaner" not in out


def test_termux_pkg_install_omits_proot_distro(monkeypatch):
    monkeypatch.setenv("PREFIX", "/data/data/com.termux/files/usr")
    out = install_schedule.render()
    # Termux env: should ask for termux-api, NOT proot-distro
    assert "pkg install termux-api" in out
    assert "proot-distro" not in out


def test_proot_pkg_install_includes_proot_distro(monkeypatch):
    monkeypatch.delenv("PREFIX", raising=False)
    out = install_schedule.render()
    assert "pkg install termux-api proot-distro" in out
