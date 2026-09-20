from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys


def _default_log_dir() -> Path:
    """Choose a predictable log directory.

    When running from the source checkout, keep logs inside the repository so
    they are easy to find during development. A packaged executable falls back
    to LocalAppData, which is writable for normal Windows users.
    """
    cwd = Path.cwd()

    if (cwd / "main.py").is_file() and (cwd / "src").is_dir():
        return cwd / "logs"

    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base) / "ScreenTranslator" / "logs"

    return cwd / "logs"


def setup_logging(debug: bool = False, log_dir: Path | None = None) -> logging.Logger:
    directory = log_dir or _default_log_dir()
    directory.mkdir(parents=True, exist_ok=True)
    log_file = directory / "screen_translator.log"

    logger = logging.getLogger("screen_translator")
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    logger.propagate = False

    # Reconfigure cleanly in case the application is initialized more than once
    # in the same interpreter (tests/dev reloads).
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        try:
            handler.close()
        except Exception:
            pass

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=2_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    logger.addHandler(file_handler)

    # Always expose useful runtime diagnostics in the terminal. Debug mode
    # simply increases console verbosity.
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    console.setLevel(logging.DEBUG if debug else logging.INFO)
    logger.addHandler(console)

    logger.info("Log file: %s", log_file.resolve())
    return logger
