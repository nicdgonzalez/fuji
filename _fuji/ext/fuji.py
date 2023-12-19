from __future__ import annotations

import json
import logging
import pathlib
from typing import TYPE_CHECKING, overload

import clap

if TYPE_CHECKING:
    from builtins import dict as Dict
    from typing import Any, Optional

# fmt: off
__all__ = (
    "FujiCommands",
)
# fmt: on

_log = logging.getLogger(__name__)


class FujiCommands(clap.Extension):
    """Commands related to the Fuji directory and configuration."""

    DEFAULT_ROOT = pathlib.Path.home().joinpath(".fuji")
    CONFIG_FILE = pathlib.Path(__file__).parents[2].joinpath("config.json")

    def __init__(self) -> None:
        self.config = self.load_config()
        self._root = self.config.get("root", self.DEFAULT_ROOT)

    @property
    def root(self) -> pathlib.Path:
        return self._root

    @root.setter
    def root(self, value: pathlib.Path) -> None:
        self._root = value
        self.config["root"] = str(value)

    def load_config(self) -> dict[str, Any]:
        """Read from the configuration file.

        Returns
        -------
        dict[str, Any]
            The contents of the configuration file.
        """
        default_data = {"root": str(self.DEFAULT_ROOT)}

        try:
            return json.loads(self.CONFIG_FILE.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            _log.warning("Failed to read configuration file.")
            self.save_config(default_data)
            return default_data

    @overload
    def save_config(self) -> None:
        pass

    @overload
    def save_config(self, data: dict[str, Any], /) -> None:
        pass

    def save_config(self, data: Optional[Dict[str, Any]] = None) -> None:
        """Write to the configuration file.

        Parameters
        ----------
        data : dict[str, Any]
            The data to write to the configuration file.
        """
        if not data:
            data = self.config

        with self.CONFIG_FILE.open("w") as f:
            json.dump(data, f, indent=4)

    @clap.command()
    def init(self, directory: str = str(DEFAULT_ROOT), /) -> None:
        """Setup the Fuji directory.

        Parameters
        ----------
        directory : :class:`str`
            The directory to setup Fuji in.
        """
        root = pathlib.Path(directory).expanduser().resolve()

        if root.exists():
            _log.warning(f"Directory '{root}' already exists.")
            return

        _log.info(f"Initializing Fuji directory at '{root}'.")
        directories = ("backups", "logs", "jars", "servers")

        for d in directories:
            assert root.joinpath(d).exists() is False
            subdirectory = root.joinpath(d)
            _log.debug(f"Creating subdirectory '{subdirectory}'.")
            subdirectory.mkdir(parents=True)

        self.root = root
        _log.info(f"Fuji directory initialized at '{root}'.")


def setup(parser: clap.Parser) -> None:
    parser.add_command(FujiCommands())
