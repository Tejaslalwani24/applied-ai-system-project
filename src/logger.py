import logging
import sys
from pathlib import Path


def setup_logging(log_file: str = "groovematch.log", level: int = logging.INFO) -> None:
    """Configure root logger with console + file handlers (idempotent)."""
    root = logging.getLogger()
    if root.handlers:
        return  # already configured

    root.setLevel(level)
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    root.addHandler(ch)

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(fmt)
    root.addHandler(fh)
