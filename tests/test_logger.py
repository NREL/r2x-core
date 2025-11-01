"""Test for logging."""


def test_logger_setup_with_log_file(tmp_path):
    """Test logger setup with file output."""
    from r2x_core.logger import setup_logging

    log_file = tmp_path / "test.log"

    setup_logging(level="DEBUG", log_file=str(log_file), module="r2x_core")

    assert log_file.exists()


def test_logger_setup_with_tracing(tmp_path):
    """Test logger setup with tracing enabled."""
    from r2x_core.logger import setup_logging

    log_file = tmp_path / "test_trace.log"

    setup_logging(
        level="TRACE",
        tracing=True,
        log_file=str(log_file),
        module="r2x_core",
    )

    assert log_file.exists()
