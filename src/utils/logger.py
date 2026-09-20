from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path


def _default_log_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base) / "ScreenTranslator" / "logs"
    return Path.cwd() / "logs"


def setup_logging(debug: bool = False, log_dir: Path | None = None) -> logging.Logger:
    directory = log_dir or _default_log_dir()
    directory.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("screen_translator")
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    logger.propagate = False

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    file_handler = RotatingFileHandler(
        directory / "screen_translator.log",
        maxBytes=2_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    logger.addHandler(file_handler)

    if debug:
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        console.setLevel(logging.DEBUG)
        logger.addHandler(console)

    return logger
