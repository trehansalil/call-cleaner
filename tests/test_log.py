import logging

from call_cleaner import log


def test_setup_logger_writes_to_path(tmp_path):
    logfile = tmp_path / "run.log"
    logger = log.setup("test", logfile, max_bytes=1024, backup_count=2)
    logger.info("hello")
    for h in logger.handlers:
        h.flush()
    assert logfile.exists()
    assert "hello" in logfile.read_text()


def test_setup_logger_rotates(tmp_path):
    logfile = tmp_path / "run.log"
    logger = log.setup("rot", logfile, max_bytes=200, backup_count=2)
    for i in range(50):
        logger.info("line %d with padding xxxxxxxxxxxxxxxxxxxx", i)
    for h in logger.handlers:
        h.flush()
    rotated = list(tmp_path.glob("run.log*"))
    assert len(rotated) >= 2  # main + at least one backup


def test_setup_idempotent(tmp_path):
    logfile = tmp_path / "run.log"
    a = log.setup("dup", logfile)
    b = log.setup("dup", logfile)
    assert a is b
    assert len(a.handlers) == 1
