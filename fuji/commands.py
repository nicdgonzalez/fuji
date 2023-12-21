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
        """List all available servers."""
        raise NotImplementedError

    @clap.command()
    def create(self, name: str, /, *, accept_eula: bool = False) -> None:
        """Create a new server.

        Parameters
        ----------
        name : :class:`str`
            The name of the server to create.
        accept_eula : :class:`bool`
            Whether to accept the EULA without prompting the user.
        """
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


def setup(parser: clap.ArgumentParser) -> None:
    parser.add_extension(FujiCommands())
