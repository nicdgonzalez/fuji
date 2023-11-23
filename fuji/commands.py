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
import random
import subprocess
import sys
import threading
import time
from typing import Annotated, Any

import clap
import requests
from clap.metadata import Conflicts, Short
from overrides import override

from .server import Server
from .tmux import TmuxSession

__all__ = ("FujiCommands",)

EDITOR = os.environ.get("EDITOR", "vim")
PAPERMC_API_VERSION = "v2"
DEFAULT_ROOT = pathlib.Path.home().joinpath(".fuji")

_log = logging.getLogger(__name__)
config_file = pathlib.Path(__file__).parents[1].joinpath("config.json")


class FujiCommands(clap.Parser):
    """Represents the Fuji command-line interface."""

    def __init__(self) -> None:
        super().__init__(
            help="A command-line tool for managing Minecraft servers.",
            epilog="Thank you for using Fuji!",
        )
        self.config = self._load_config()
        self._root = self.config.get("root", DEFAULT_ROOT)

    @property
    def root(self) -> pathlib.Path:
        """The base directory of all Fuji-related files."""
        return pathlib.Path(self._root)

    @root.setter
    def root(self, value: pathlib.Path) -> None:
        self.config["root"] = str(value)

    @property
    def all_servers(self) -> tuple[pathlib.Path, ...]:
        """Get all of the servers that Fuji is managing."""
        return tuple(self.root.joinpath("servers").iterdir())

    def _load_config(self) -> dict[str, Any]:
        """Read from the configuration file.

        Returns
        -------
        dict[str, Any]
            The contents of the configuration file.
        """
        default_data = {"root": str(DEFAULT_ROOT)}

        try:
            return json.loads(config_file.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            _log.warning("Failed to read configuration file.")
            self._save_config(default_data)
            return default_data

    def _save_config(self, data: dict[str, Any], /) -> None:
        """Write to the configuration file.

        Parameters
        ----------
        data : dict[str, Any]
            The data to write to the configuration file.
        """
        with config_file.open("w") as f:
            json.dump(data, f, indent=4)

    @override
    def parse(
        self,
        argv: list[str] = sys.argv,
        /,
        help_fmt: clap.HelpFormatter = clap.HelpFormatter(),
    ) -> None:
        """Parse command-line arguments.

        Parameters
        ----------
        argv : list[str], optional
            The command-line arguments to parse.
        help_fmt : clap.HelpFormatter, optional
            The help formatter to use.
        """
        super().parse(argv, help_fmt=help_fmt)
        self._save_config(self.config)

    def get_server(self, name: str, /) -> Server:
        """Convert a server name to a :class:`Server` object.

        Parameters
        ----------
        name : str
            The name of the server.

        Returns
        -------
        Server
            The server object.
        """
        return Server(ctx=self, name=name)

    # COMMANDS #

    @clap.command()
    def setup(self, directory: pathlib.Path = str(DEFAULT_ROOT), /) -> None:
        """Initialize Fuji for the first time.

        Parameters
        ----------
        directory : pathlib.Path, optional
            The directory to use as the root directory for Fuji.
        """
        path = pathlib.Path(directory)

        if path.exists():
            _log.warning(f"Directory '{path}' already exists.")
            return

        _log.info(f"Initializing Fuji in '{path}'...")

        directories = ("backups", "logs", "jars", "servers")
        for directory in directories:
            path.joinpath(directory).mkdir(parents=True, exist_ok=True)

        self.root = path.resolve()
        _log.info(f"Successfully initialized Fuji in '{path}'.")

    # @clap.group()
    # def server(self) -> None:
    #     """A collection of server-related commands."""
    #     pass

    @clap.command()
    def list(self) -> None:
        """Display all available servers."""
        if not self.all_servers:
            print("No servers found.")
            return

        for index, server in enumerate(self.all_servers, start=1):
            print(f"{index}. {server.name.upper()}")

    @clap.command()
    def create(
        self,
        name: str,
        /,
        *,
        accept_eula: Annotated[bool, Short("y")] = False,
        edit: Annotated[bool, Short("e")] = False,
        version: str | None = None,
        build: int | None = None,
    ) -> None:
        """Create a new Minecraft server.

        Parameters
        ----------
        name : str
            The name of the server.
        accept_eula : bool, optional
            Whether to accept the EULA without prompting the user.
        edit : bool, optional
            Open an editor to edit the server.properties file after it is
            generated.
        version : str, optional
            The version of Minecraft to use.
        build : int, optional
            The build number of PaperMC to use.
        """
        name = self.validate_server_name(name)
        server = self.get_server(name)

        if server.path.exists():
            raise ValueError(f"Server '{name}' already exists.")

        server.path.mkdir(parents=True)
        _log.info(f"Created directory '{server.path}'.")

        # TODO: This is a workaround. Maybe define a `Command.invoke` method
        # with a `parent` parameter for manually invoking commands?
        self.upgrade.parent = self
        self.upgrade(name, version=version, build=build)

        self.generate_eula(server, accept_eula=accept_eula)

        if edit:
            _log.info(f"Opening '{server.server_properties}' in '{EDITOR}'.")
            subprocess.run([EDITOR, server.server_properties.as_posix()])

        _log.info(f"Successfully created server '{name}'.")

    def validate_server_name(self, name: str, /) -> str:
        """Validate a server name.

        Parameters
        ----------
        name : str
            The name of the server.

        Returns
        -------
        str
            The validated server name.
        """
        if not name[0].isalpha():
            raise ValueError(f"'{name}' is not a valid server name.")

        return name.lower()

    def generate_eula(
        self, /, server: Server, accept_eula: bool = False
    ) -> None:
        """Generate the EULA for a server.

        Parameters
        ----------
        server : Server
            The server to generate the EULA for.
        accept_eula : bool, optional
            Whether to accept the EULA without prompting the user.
        """
        cmd = ["java", "-jar", server.server_jar.as_posix(), "--nogui"]
        subprocess.run(
            cmd,
            shell=False,
            cwd=server.path,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        if not accept_eula:
            response = input(
                "Please read the Minecraft EULA before continuing:\n"
                "https://aka.ms/MinecraftEULA\n"
                "Do you accept the Minecraft EULA? [y/N] "
            )

            if response.lower() not in ("y", "yes"):
                raise RuntimeError("You must accept the Minecraft EULA.")

            eula = server.path.joinpath("eula.txt")
            eula.write_text("eula=true")

    @clap.command()
    def delete(
        self, name: str, /, *, assume_yes: Annotated[bool, Short("y")] = False
    ) -> None:
        """Delete a Minecraft server.

        Parameters
        ----------
        name : str
            The name of the server to delete.
        assume_yes : bool, optional
            Whether to skip the confirmation prompt.
        """
        name = self.validate_server_name(name)
        server = self.get_server(name)
        _log.info(f"Deleting server '{name}' at '{server.path}'...")

        if not server.path.exists():
            raise ValueError(f"Server '{name}' does not exist.")

        if not assume_yes:
            response = input(
                f"Are you sure you want to delete '{name}'? [y/N] "
            )
            if response.lower() not in ("y", "yes"):
                return

        subprocess.run(["rm", "-rf", server.path.as_posix()])
        _log.info(f"Successfully deleted server '{name}'.")

    @clap.command()
    def edit(self, name: str, /) -> None:
        """Edit a server's server.properties file.

        Parameters
        ----------
        name : str
            The name of the server to edit.
        """
        name = self.validate_server_name(name)
        server = self.get_server(name)

        if not server.path.exists():
            raise ValueError(f"Server '{name}' does not exist.")

        _log.info(f"Opening '{server.server_properties}' in '{EDITOR}'.")
        subprocess.run([EDITOR, server.server_properties.as_posix()])

    @clap.command()
    def start(
        self,
        name: str,
        /,
        *,
        auto_reconnect: Annotated[bool, Short("r")] = False,
    ) -> None:
        """Start a Minecraft server.

        Parameters
        ----------
        name : str
            The name of the server to start.
        auto_reconnect : bool, optional
            Whether to automatically reconnect to the server if it crashes.
        """
        name = self.validate_server_name(name)
        server = self.get_server(name)

        if not server.path.exists():
            raise ValueError(f"Server '{name}' does not exist.")

        tmux_session = TmuxSession(f"fuji-{name}")
        if not tmux_session.exists():
            tmux_session.new()

        # Aikar's flags for optimizing the JVM: https://mcflags.emc.gs
        cmd = [
            "cd",
            server.path.resolve().as_posix(),
            "&&",
            "java",
            "-Xms5G",
            "-Xmx5G",
            "-XX:+UseG1GC",
            "-XX:+ParallelRefProcEnabled",
            "-XX:MaxGCPauseMillis=200",
            "-XX:+UnlockExperimentalVMOptions",
            "-XX:+DisableExplicitGC",
            "-XX:+AlwaysPreTouch",
            "-XX:G1NewSizePercent=30",
            "-XX:G1MaxNewSizePercent=40",
            "-XX:G1HeapRegionSize=8M",
            "-XX:G1ReservePercent=20",
            "-XX:G1HeapWastePercent=5",
            "-XX:G1MixedGCCountTarget=4",
            "-XX:InitiatingHeapOccupancyPercent=15",
            "-XX:G1MixedGCLiveThresholdPercent=90",
            "-XX:G1RSetUpdatingPauseTimePercent=5",
            "-XX:SurvivorRatio=32",
            "-XX:+PerfDisableSharedMem",
            "-XX:MaxTenuringThreshold=1",
            "-Dusing.aikars.flags=https://mcflags.emc.gs",
            "-Daikars.new.flags=true",
            "-jar",
            server.server_jar.resolve().as_posix(),
            "--nogui",
        ]

        def watch_server() -> None:
            while 1:
                retries = 20
                if not server.is_online() and not server.is_locked():
                    _log.info(
                        f"Server '{name}' is offline. Sending command "
                        "to start server..."
                    )
                    tmux_session.send_keys(" ".join(cmd))
                    server.lock.touch()
                    _log.info(f"Created lock file '{server.lock}'.")

                while not server.is_online() and retries > 0:
                    retries -= 1
                    seconds = 1.0 + (random.randint(10, 100) / 100)
                    time.sleep(seconds)

                _log.info(f"Server '{name}' is online.")
                os.remove(server.lock)
                _log.info(f"Removed lock file '{server.lock}'.")

                if not auto_reconnect:
                    break

        try:
            # TODO: Does this leave a zombie process if auto_reconnect is true?
            thread = threading.Thread(target=watch_server, daemon=False)
            thread.start()
        except KeyboardInterrupt:
            os.remove(server.lock)
            _log.info(f"Removed lock file '{server.lock}'.")

    @clap.command()
    def stop(self, name: str, /) -> None:
        """Stop a Minecraft server.

        Parameters
        ----------
        name : str
            The name of the server to stop.
        """
        name = self.validate_server_name(name)
        server = self.get_server(name)
        tmux_session = TmuxSession(f"fuji-{name}")

        if not server.path.exists():
            raise ValueError(f"Server '{name}' does not exist.")

        if not tmux_session.exists():
            raise RuntimeError(f"Server '{name}' is not running.")

        tmux_session.send_keys("stop")
        _log.info(f"Sent command to stop server '{name}'.")

        retries = 10
        while server.is_online() and retries > 0:
            retries -= 1
            time.sleep(1)

        _log.info(f"Server '{name}' is offline.")
        tmux_session.kill()
        _log.info(f"Killed tmux session '{tmux_session.name}'.")

    @clap.command()
    def status(self, name: str, /) -> None:
        """Display the status of a Minecraft server.

        Parameters
        ----------
        name : str
            The name of the server to check.
        """
        name = self.validate_server_name(name)
        server = self.get_server(name)

        if not server.path.exists():
            raise ValueError(f"Server '{name}' does not exist.")

        if server.is_online():
            print(f"Server '{name}' is online.")
        else:
            print(f"Server '{name}' is offline.")

    @clap.command()
    def migrate(self, name: str, directory: pathlib.Path, /) -> None:
        """Migrate a Minecraft server to a new directory.

        Parameters
        ----------
        name : str
            A name for the server being migrated.
        directory : pathlib.Path
            The directory to migrate the server from.
        """
        # Move via copy. This is to ensure that the original server is not
        # modified in any way.

        # Validate the *from* directory and ensure that it is a valid server.

        # Determine the server's name from the `server.properties` file.

        # Ensures that a proper PaperMC server is runnable by Fuji.
        # I think the only thing that needs to be done is to create a symlink
        # to the server JAR file in the server's directory (at least for now).
        raise NotImplementedError

    @clap.command()
    def install_plugin(
        self,
        name: str,
        filename: str,
        /,
        *,
        local: Annotated[str | None, Conflicts("url")] = None,
        url: Annotated[str | None, Conflicts("local")] = None,
    ) -> None:
        """Install a plugin to a Minecraft server.

        Parameters
        ----------
        name : str
            The name of the server to install the plugin to.
        filename : str
            The filename of the plugin to install.
        local : str, optional
            The path to the plugin to install on the local filesystem.
        url : str, optional
            The URL to download the plugin from.
        """
        name = self.validate_server_name(name)
        server = self.get_server(name)

        if not server.path.exists():
            raise ValueError(f"Server '{name}' does not exist.")

        plugin = server.path.joinpath("plugins", filename)

        if local is not None:
            local_plugin = pathlib.Path(local)
            if not local_plugin.exists():
                raise ValueError(f"Plugin '{plugin}' does not exist.")
            plugin_data = local_plugin.read_bytes()
        elif url is not None:
            if (response := requests.get(url)).status_code != 200:
                raise RuntimeError(
                    f"Failed to download plugin: {response.text}"
                )
            plugin = server.path.joinpath("plugins", filename)
            plugin_data = response.content
        else:
            raise ValueError("Either 'local' or 'url' must be specified.")

        _log.info(f"Writing bytes to '{plugin}'.")
        plugin.write_bytes(plugin_data)
        _log.info(f"Successfully installed plugin '{filename}'.")

    @clap.command()
    def upgrade(
        self,
        name: str,
        /,
        version: str | None = None,
        build: int | None = None,
    ) -> None:
        """Update a Minecraft server to a newer version of PaperMC.

        Parameters
        ----------
        name : str
            The name of the server to update.
        version : str, optional
            The version of PaperMC to update to.
        build : int, optional
            The build number of PaperMC to update to.
        """
        name = self.validate_server_name(name)
        server = self.get_server(name)

        if not server.path.exists():
            raise ValueError(f"Server '{name}' does not exist.")

        filename, data = self.get_paper_jar(version=version, build=build)
        if server.server_jar.resolve().name != filename:
            paper_jar = self.root.joinpath("jars", filename)
            _log.info(f"Writing bytes to '{paper_jar}'.")
            paper_jar.write_bytes(data)

            _log.info(f"Symlink '{server.server_jar}' -> '{paper_jar}'.")
            if server.server_jar.exists():
                server.server_jar.unlink()
            server.server_jar.symlink_to(paper_jar)

        _log.info(f"Successfully upgraded server '{name}'.")

    def get_paper_jar(
        self, version: str | None = None, build: int | None = None
    ) -> tuple[str, bytes]:
        """Get the PaperMC server JAR file for the specified version and build.

        Parameters
        ----------
        version : str, optional
            The version of PaperMC to download. If not specified, the latest
            version will be downloaded.
        build : int, optional
            The build number of PaperMC to download. If not specified, the
            latest build will be downloaded.

        Returns
        -------
        tuple[str, bytes]
            A tuple containing the filename of the downloaded JAR file and the
            contents of the JAR file.

        Raises
        ------
        RuntimeError
            If the server JAR file could not be downloaded.
        """
        url = f"https://papermc.io/api/{PAPERMC_API_VERSION}/projects/paper"

        if version is None:
            if (response := requests.get(url)).status_code != 200:
                raise RuntimeError(
                    f"Failed to get latest version of PaperMC: {response.text}"
                )
            version = response.json()["versions"][-1]

        url += f"/versions/{version}/builds"

        if (response := requests.get(url)).status_code != 200:
            raise RuntimeError(
                f"Failed to get latest build of PaperMC: {response.text}"
            )

        if build is None:
            data = response.json()["builds"][-1]
        else:
            temp = response.json()
            builds = temp["builds"]

            valid_build = False
            for b in builds:
                if b["build"] == build:
                    valid_build = True
                    data = b
                    break

            if not valid_build:
                raise RuntimeError(
                    f"Invalid build number '{build}' for version '{version}'."
                )

        build = build or data["build"]
        filename: str = data["downloads"]["application"]["name"]

        for f in self.root.joinpath("jars").iterdir():
            if f.name == filename:
                _log.info("PaperMC is already up-to-date.")
                return filename, f.read_bytes()

        url += f"/{build}/downloads/{filename}"

        _log.info(f"Downloading PaperMC {version} build {build}...")
        if (response := requests.get(url)).status_code != 200:
            raise RuntimeError(f"Failed to download PaperMC: {response.text}")

        _log.info("Download complete.")
        return filename, response.content
