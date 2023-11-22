"""
Commands
========

This module contains the commands that are available to the user.

"""
from __future__ import annotations

import json
import logging
import os
import pathlib
import socket
import subprocess
import sys
from typing import Annotated, Any, cast

import clap
import requests
from clap.metadata import Short
from overrides import override

from .tmux import TmuxSession

PAPERMC_API_VERSION = "v2"
EDITOR = os.environ.get("EDITOR", "vim")

_log = logging.getLogger(__name__)


def get_paper_jar(
    server_jar: pathlib.Path,
    *,
    version: str | None = None,
    build: int | None = None,
) -> tuple[str, bytes]:
    """Get the Paper JAR file for the specified version and build.

    Parameters
    ----------
    server_jar : pathlib.Path
        The path to the server JAR file. This is used to compare the latest
        version of PaperMC to the currently installed version.
    version : str, optional
        The version of Minecraft to use.
    build : int, optional
        The build of Paper to use.

    Returns
    -------
    tuple[str, bytes]
        The name of the Paper JAR file and its contents.
    """
    _log.info(f"Getting JAR for PaperMC: {version}#{build}")
    url = f"https://papermc.io/api/{PAPERMC_API_VERSION}/projects/paper"
    data: dict[str, Any]

    # We are essentially web scraping to determine the missing information
    # (version and/or build) which means we are at the mercy of PaperMC's API.
    # If the API changes, this will need to be updated accordingly. This is
    # why we occasionally assert that certain keys are in the data.

    if version is None:
        if (response := requests.get(url)).status_code != 200:
            raise RuntimeError(
                f"Failed to get latest version of PaperMC: {response.text}"
            )

        data = response.json()
        assert "versions" in data, "Data does not contain 'versions'."
        version = data["versions"][-1]
        _log.info(f"Using version '{version}' of PaperMC.")

    url += f"/versions/{version}/builds"
    if (response := requests.get(url)).status_code != 200:
        raise RuntimeError(
            f"Failed to get latest build of PaperMC: {response.text}"
        )

    if build is None:
        data = response.json()["builds"][-1]
    else:
        tmp = response.json()
        assert "builds" in tmp, "Response does not contain 'builds'."
        builds = tmp["builds"]

        valid_build = False
        for b in builds:
            if b["build"] == build:
                valid_build = True
                data = b
                break

        if not valid_build:
            raise RuntimeError(
                f"Build '{build}' is not valid for version '{version}'."
            )

    build = build or data["build"]
    _log.info(f"Using build '{build}' of PaperMC.")

    assert (
        "downloads" in data
        and "application" in data["downloads"]
        and "name" in data["downloads"]["application"]
    ), "Data does not contain 'downloads.application.name'."
    filename: str = data["downloads"]["application"]["name"]

    if server_jar.resolve().name == filename:
        _log.info("PaperMC is already up to date.")
        return filename, server_jar.read_bytes()

    url += f"/{build}/downloads/{filename}"

    _log.info(f"PaperMC is not up to date. Downloading from '{url}'...")
    if (response := requests.get(url)).status_code != 200:
        raise RuntimeError(f"Failed to download PaperMC: {response.text}")

    _log.info("Download complete.")
    return filename, response.content


class FujiCommands(clap.Parser):
    """Represents the commands that are available to the user."""

    DEFAULT_SETUP_PATH = pathlib.Path.home().joinpath(".fuji")

    def __init__(self) -> None:
        super().__init__(
            help="A command-line tool for managing Minecraft servers.",
            epilog="Thank you for using Fuji!",
        )
        self._log = logging.getLogger(__name__)
        self._tmux = TmuxSession("fuji")
        self._fuji_path = pathlib.Path.home().joinpath(".fuji")

        project_root = pathlib.Path(__file__).parents[1]
        self._config_file = project_root.joinpath("config.json")

        self.config: dict[str, Any] = self.load_config()

    @property
    def fuji_path(self) -> pathlib.Path:
        """The path to the Fuji-related files."""
        return self._fuji_path

    @fuji_path.setter
    def fuji_path(self, path: pathlib.Path, /) -> None:
        self._fuji_path = path
        self.config["fuji_path"] = str(path)

    @property
    def config_file(self) -> pathlib.Path:
        """The path to the Fuji configuration file."""
        return self._config_file

    def save_config(self, config: dict[str, Any]) -> None:
        """Save the Fuji configuration."""
        with open(self.config_file, "w") as f:
            json.dump(config, f, indent=4)

    def load_config(self) -> dict[str, Any]:
        """Load the Fuji configuration."""
        try:
            with open(self.config_file, "r") as f:
                return cast(dict[str, Any], json.load(f))
        except FileNotFoundError:
            default_config: dict[str, Any] = {
                "fuji_path": str(self.fuji_path),
            }
            self.save_config(default_config)
            return default_config

    @override
    def parse(
        self,
        argv: list[str] = sys.argv,
        /,
        *,
        help_fmt: clap.HelpFormatter = clap.HelpFormatter(),
    ) -> None:
        """Parse the command-line arguments."""
        super().parse(argv, help_fmt=help_fmt)
        self.save_config(self.config)

    @clap.command()
    def setup(self, directory: str = str(DEFAULT_SETUP_PATH), /) -> None:
        """Setup the main Fuji directory.

        Parameters
        ----------
        directory : str
            The path to the directory to store all of the Fuji-related files.
        """
        path = pathlib.Path(directory)
        if path != self.fuji_path:
            self.fuji_path = path

        self._log.info(f"Setting up Fuji at '{path}'.")

        if path.exists():
            self._log.warning(f"Path '{path}' already exists.")
            return

        directories = [
            # For routine backups of each world.
            "backups",
            # For the Fuji log files.
            "logs",
            # For Server JAR files.
            "jars",
            # For the playable Minecraft server worlds.
            "servers",
        ]

        for directory in directories:
            path.joinpath(directory).mkdir(parents=True, exist_ok=True)

        self._log.info("Setup complete.")

    @clap.group()
    def server(self) -> None:
        """A collection of server-related commands."""
        pass

    @server.command()
    def list(self) -> None:
        """List all of the Minecraft servers."""
        servers = list(self.fuji_path.joinpath("servers").iterdir())

        if not servers:
            print("No servers found.")
            return

        for index, server in enumerate(servers, start=1):
            print(f"{index}. {server.name}")

    @server.command()
    def new(
        self,
        server: str,
        /,
        accept_eula: Annotated[bool, Short("y")] = False,
        edit: Annotated[bool, Short("e")] = False,
        version: str | None = None,
        build: int | None = None,
    ) -> None:
        """Create a new Minecraft server.

        Parameters
        ----------
        server : str
            The name of the server to create.
        version : str, optional
            The version of Minecraft to use.
        build : int, optional
            The build number of PaperMC to use.
        accept_eula : bool, optional
            Whether or not to accept the EULA without prompting the user.
        edit : bool, optional
            Whether or not to open the server.properties file for editing.
        """
        self._log.info(f"Creating server '{server}'.")
        server_path = self.fuji_path.joinpath("servers", server)

        if server_path.exists():
            self._log.warning(f"Server '{server}' already exists.")
            return

        server_path.mkdir(parents=True)
        server_jar = self.fuji_path.joinpath("server.jar")
        name, data = get_paper_jar(server_jar, version=version, build=build)

        if server_jar.resolve().name != name:
            paper_jar = self.fuji_path.joinpath("jars", name)
            _ = paper_jar.write_bytes(data)

            self._log.info(f"Updating server.jar symlink to '{name}'.")

            if server_jar.exists():
                server_jar.unlink()

            server_jar.symlink_to(paper_jar)

        cmd = ["java", "-jar", server_jar.as_posix(), "nogui"]
        self._log.info(f"Running command: {' '.join(cmd)}")
        _ = subprocess.run(
            cmd,
            shell=False,
            cwd=server_path,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        if not accept_eula:
            response = input(
                "By continuing, you accept the Minecraft EULA:\n"
                "https://aka.ms/MinecraftEULA\n"
                "Do you accept? [y/N] "
            )

            if response.lower() not in ("y", "yes"):
                return

        eula = server_path.joinpath("eula.txt")
        _ = eula.write_text("eula=true")

        if edit:
            self._log.info(
                f"Opening server.properties for editing using {EDITOR}."
            )
            server_properties = server_path.joinpath("server.properties")
            _ = subprocess.run([EDITOR, server_properties.as_posix()])

        self._log.info(f"Server '{server}' is ready.")

    @server.command()
    def remove(
        self,
        server: str,
        /,
        *,
        assume_yes: Annotated[bool, Short("y")] = False,
    ) -> None:
        """Remove a Minecraft server.

        Parameters
        ----------
        server : str
            The name of the server to remove.
        assume_yes : bool, optional
            Whether or not to skip the confirmation prompt.
        """
        self._log.info(f"Removing server '{server}'.")
        server_path = self.fuji_path.joinpath("servers", server)

        if not server_path.exists():
            self._log.warning(f"Server '{server}' does not exist.")
            return

        if not assume_yes:
            response = input(
                f"Are you sure you want to remove '{server}'? [y/N] "
            )

            if response.lower() not in ("y", "yes"):
                return

        _ = subprocess.run(["rm", "-rf", server_path.as_posix()])

        self._log.info(f"Server '{server}' has been removed.")

    @server.command()
    def edit(self, server: str, /) -> None:
        """Edit the server.properties file.

        Parameters
        ----------
        server : str
            The name of the server to edit.
        """
        server_properties = self.fuji_path.joinpath(
            "servers", server, "server.properties"
        )
        _ = subprocess.run([EDITOR, server_properties.as_posix()])

    @server.command()
    def start(self, server: str, /) -> None:
        """Start a Minecraft server.

        Parameters
        ----------
        server : str
            The name of the server to start.
        """
        raise NotImplementedError

    @server.command()
    def stop(self, server: str, /) -> None:
        """Stop a Minecraft server.

        Parameters
        ----------
        server : str
            The name of the server to stop.
        """
        raise NotImplementedError

    @server.command()
    def status(self, server: str, /) -> None:
        """Get the status of the server.

        Parameters
        ----------
        server : str
            The name of the server to get the status of.
        """
        # TODO: This is a temporary implementation. I probably need to read
        # the server.properties to determine the address and port.
        if self.server_online("127.0.0.1", 25565):
            self._log.info("Server is online.")
        else:
            self._log.info("Server is offline.")

    def server_online(self, host: str, port: int) -> bool:
        """Check if the server is online."""
        address = host, port
        try:
            with socket.create_connection(address, timeout=1):
                return True
        except socket.error:
            return False
