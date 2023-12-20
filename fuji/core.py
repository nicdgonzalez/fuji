from __future__ import annotations

import logging
import json
import pathlib
from typing import TYPE_CHECKING

from .servers import MinecraftServer

if TYPE_CHECKING:
    from builtins import list as List
    from builtins import dict as Dict
    from typing import Any

_log = logging.getLogger(__name__)


class Fuji:
    DEFAULT_ROOT = pathlib.Path.home().joinpath(".fuji")
    CONFIG_JSON = pathlib.Path(__file__).parents[1].joinpath("config.json")

    def __init__(self, directory: str = str(DEFAULT_ROOT)) -> None:
        self._config = NotImplemented
        self._root = self._config.get("root", directory)

    def load_config(self) -> Dict[str, Any]:
        """Read from the configuration file."""
        default_data = {
            "root": str(self.DEFAULT_ROOT),
        }

        try:
            data = json.loads(self.CONFIG_JSON.read_text())
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            _log.warning(
                f"Using default configuration. Unable to load existing: {exc}"
            )
            data = default_data

        return data

    def init(self, directory: str = str(DEFAULT_ROOT)) -> None:
        """Run once to initialize Fuji.

        Parameters
        ----------
        directory : :class:`str`
            The directory to initialize Fuji in.
        """
        root = pathlib.Path(directory).expanduser()

        if root.exists():
            raise FileExistsError(f"Directory '{root}' already exists.")

        root.mkdir(parents=True, exist_ok=True)
        subdirectories = ("backups", "logs", "jars", "servers")

        for subdirectory in subdirectories:
            root.joinpath(subdirectory).mkdir()

        _log.info(f"Initialized Fuji in {root}.")

    @property
    def servers(self) -> List[MinecraftServer]:
        """A list of all servers."""
        ...
