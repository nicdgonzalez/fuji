from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING

import clap

if TYPE_CHECKING:
    from builtins import list as List

parser = clap.ArgumentParser(
    "A command-line tool for managing Minecraft servers.",
    epilog="Thank you for using Fuji!",
)

extensions = [
    ".commands",
]

for extension in extensions:
    parser.extend(extension, package="fuji")


def logging_setup() -> None:
    """Configure logging for the application."""
    handlers: List[logging.Handler] = []
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S%z",
    )

    stream_handler = logging.StreamHandler(sys.stdout)
    handlers.append(stream_handler)

    # Add additional handlers here (e.g. file handler).
    ...

    for handler in handlers:
        handler.setFormatter(formatter)
        logging.root.addHandler(handler)

    logging.root.setLevel(logging.INFO)


def main() -> int:
    logging_setup()
    parser.parse()

    return 0


if __name__ == "__main__":
    sys.exit(main())
