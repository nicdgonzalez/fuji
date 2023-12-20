from __future__ import annotations

from typing import TYPE_CHECKING

import clap

from .servers import MinecraftServer

if TYPE_CHECKING:
    from typing import Annotated


class FujiCommands(clap.Extension):
    def __init__(self) -> None:
        self._config = {}

    @clap.command()
    def init(self, directory: str, /) -> None:
        """Run once to initialize Fuji.

        Parameters
        ----------
        directory : :class:`str`
            The directory to initialize Fuji in.
        """
        raise NotImplementedError

    @clap.command()
    def list(self, /) -> None:
        """List all servers."""
        raise NotImplementedError

    @clap.command()
    def start(self, name: str, /) -> None:
        """Start a server.

        Parameters
        ----------
        name : :class:`str`
            The name of the server to start.
        """
        raise NotImplementedError


def setup(parser: clap.Parser) -> None:
    parser.add_command(FujiCommands())
