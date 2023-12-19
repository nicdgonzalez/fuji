"""
Main
====

The main entry-point for the application. This is the file that is run when
executing `python -m fuji` or `fuji` from the command-line.

"""
from __future__ import annotations

import logging
import sys

from .commands import parser


def setup_logging() -> None:
    """Configure logging for the application."""
    handlers: list[logging.Handler] = []
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S %Z",
    )

    stream_handler = logging.StreamHandler(sys.stdout)
    handlers.append(stream_handler)

    # Add additional handlers (e.g. file handler) here.
    ...

    for handler in handlers:
        handler.setFormatter(formatter)
        logging.root.addHandler(handler)

    logging.root.setLevel(logging.INFO)


def main() -> int:
    """The main entry-point for the application.

    Returns
    -------
    int
        The exit code.
    """
    setup_logging()
    parser.parse()

    return 0


if __name__ == "__main__":
    sys.exit(main())
