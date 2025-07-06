"""Custom logging configuration using loguru with colors and VSCode integration."""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from loguru import Logger


def setup_logging(
    console_level: str = "INFO",
    file_level: str = "DEBUG",
    logs_dir: str | Path = "logs",
) -> None:
    """Setup loguru logging with console and file outputs.

    Args:
        console_level: Log level for console output (DEBUG, INFO, WARNING, ERROR)
        file_level: Log level for file output (DEBUG, INFO, WARNING, ERROR)
        logs_dir: Directory to store log files
    """
    # Remove default handler
    logger.remove()

    # Create logs directory
    logs_path = Path(logs_dir)
    logs_path.mkdir(exist_ok=True)

    # Console handler with colors and VSCode click-to-file support
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{file}:{line}</cyan> | "
        "<level>{message}</level>"
    )

    logger.add(
        sys.stderr,
        format=console_format,
        level=console_level,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )

    # File handler with detailed format
    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
        "{level: <8} | "
        "{file}:{line} | "
        "{message}"
    )

    logger.add(
        logs_path / "floridify.log",
        format=file_format,
        level=file_level,
        rotation="10 MB",
        retention="30 days",
        compression="gz",
        backtrace=True,
        diagnose=True,
    )

    # Separate error log
    logger.add(
        logs_path / "floridify_errors.log",
        format=file_format,
        level="ERROR",
        rotation="5 MB",
        retention="90 days",
        compression="gz",
        backtrace=True,
        diagnose=True,
    )


def get_logger(name: str | None = None) -> Logger:
    """Get a logger instance.

    Args:
        name: Optional logger name (defaults to calling module)

    Returns:
        Loguru logger instance
    """
    if name:
        return logger.bind(name=name)

    return logger


# Auto-setup logging when module is imported
setup_logging()
