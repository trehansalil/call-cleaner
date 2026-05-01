from call_cleaner import install_schedule


def test_emits_run_wrapper():
    out = install_schedule.render()
    assert "proot-distro login ubuntu" in out
    assert "/usr/local/bin/cleaner run --preset default" in out


def test_emits_purge_wrapper():
    out = install_schedule.render()
    assert "/usr/local/bin/cleaner purge" in out


def test_emits_termux_job_scheduler_calls():
    out = install_schedule.render()
    assert "termux-job-scheduler" in out
    assert "--script ~/.shortcuts/call-cleaner.sh" in out
    assert "--script ~/.shortcuts/call-cleaner-purge.sh" in out
    assert "--period-ms 86400000" in out
    assert "--persisted true" in out


def test_emits_pkg_install_step():
    out = install_schedule.render()
    assert "pkg install" in out
    assert "termux-api" in out
    assert "proot-distro" in out
