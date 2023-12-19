"""
Server
======

This module contains the implementation of the :class:`Server` class.

"""
from __future__ import annotations

import logging
import pathlib
import socket
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .commands import FujiCommands

_log = logging.getLogger(__name__)


class Server:
    """Represents a Minecraft server managed by Fuji."""

    def __init__(self, ctx: FujiCommands, name: str) -> None:
        self.ctx = ctx
        self.name = name
        self._ip_address: str | None = None
        self._port: int | None = None

    @property
    def path(self) -> pathlib.Path:
        """The path to the server's directory."""
        return self.ctx.root.joinpath("servers", self.name)

    @property
    def lock(self) -> pathlib.Path:
        """The path to the server's lock file."""
        return self.path.joinpath(".lock")

    @property
    def server_jar(self) -> pathlib.Path:
        """The path to the server's JAR file."""
        return self.path.joinpath("server.jar")

    @property
    def server_properties(self) -> pathlib.Path:
        """The path to the server's server.properties file."""
        return self.path.joinpath("server.properties")

    @property
    def ip_address(self) -> str:
        """The IP address of the server."""
        return self._ip_address

    @ip_address.setter
    def ip_address(self, value: str) -> None:
        self._ip_address = value

    @property
    def port(self) -> int:
        """The port of the server."""
        return self._port

    @port.setter
    def port(self, value: int) -> None:
        self._port = value

    def is_locked(self) -> bool:
        """Whether the server is currently locked."""
        return self.lock.exists()

    def get_address(self) -> tuple[str, int]:
        """Get the address of the server.

        Returns
        -------
        tuple[str, int]
            A tuple containing the IP address and port of the server.
        """
        if self.ip_address is not None and self.port is not None:
            return self.ip_address, self.port

        ip_address, port = "127.0.0.1", 25565
        n = len((ip_address, port))

        with self.server_properties.open() as f:
            for line in f:
                if line.startswith("server-ip="):
                    ip_address = line.split("=")[1]
                    print(ip_address)
                    n -= 1
                elif line.startswith("server-port="):
                    temp = line.split("=")[1]
                    if temp.isnumeric():
                        port = int(temp)
                    n -= 1
                else:
                    continue

                if n < 1:
                    break

        self.ip_address, self.port = ip_address, port
        return ip_address, port

    def is_online(self) -> bool:
        """Whether the server is currently online."""
        try:
            with socket.create_connection(self.get_address(), timeout=1):
                return True
        except OSError:
            return False
