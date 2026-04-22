from __future__ import annotations

import logging

import pytest

from pophealth_observatory.logging_config import configure_logging, log_with_fallback


@pytest.fixture(autouse=True)
def _isolate_package_logger():
    logger = logging.getLogger("pophealth_observatory")
    old_handlers = list(logger.handlers)
    old_level = logger.level
    old_propagate = logger.propagate

    logger.handlers.clear()
    logger.setLevel(logging.NOTSET)
    logger.propagate = True

    yield

    logger.handlers.clear()
    logger.handlers.extend(old_handlers)
    logger.setLevel(old_level)
    logger.propagate = old_propagate


def test_configure_logging_is_idempotent() -> None:
    logger = configure_logging(level="INFO")
    first_handler_count = len(logger.handlers)

    logger = configure_logging(level="DEBUG")

    assert len(logger.handlers) == first_handler_count
    assert logger.level == logging.DEBUG
    assert logger.propagate is False


def test_configure_logging_uses_env_level(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOGLEVEL", "WARNING")

    logger = configure_logging()

    assert logger.level == logging.WARNING


def test_configure_logging_falls_back_on_invalid_level() -> None:
    logger = configure_logging(level="not-a-level")

    assert logger.level == logging.INFO


def test_log_with_fallback_emits_log_and_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    logger = configure_logging(level="INFO")

    log_with_fallback(logger, logging.INFO, "hello-log", fallback_print=True)
    captured = capsys.readouterr()

    assert "hello-log" in captured.err
    assert "hello-log" in captured.out


def test_log_with_fallback_can_disable_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    logger = configure_logging(level="INFO")

    log_with_fallback(logger, logging.INFO, "log-only", fallback_print=False)

    assert capsys.readouterr().out == ""
