from __future__ import annotations

import logging
import os
import pathlib
import socket
import subprocess
from typing import TYPE_CHECKING

import requests

from .server_properties import (
    ServerProperties,
    deserialize_server_properties,
    serialize_server_properties,
)

if TYPE_CHECKING:
    from builtins import tuple as Tuple
    from typing import Optional

_log = logging.getLogger(__name__)


class MinecraftServer:
    """Represents a Minecraft server in Fuji's 'servers' directory.

    Parameters
    ----------
    path : :class:`str`
        The path to the server's directory.
    """

    def __init__(self, path: str) -> None:
        self._path = path

    @property
    def path(self) -> pathlib.Path:
        """The path to the server's directory."""
        return pathlib.Path(self._path).expanduser()

    @property
    def name(self) -> str:
        """The name of the server."""
        return self.path.name

    @property
    def exists(self) -> bool:
        """Whether or not the server exists."""
        return self.path.exists()

    @property
    def properties(self) -> ServerProperties:
        """The contents of the server.properties file."""
        with open(self.path / "server.properties") as file:
            return deserialize_server_properties(file.read())

    @properties.setter
    def properties(self, properties: ServerProperties) -> None:
        with open(self.path / "server.properties", "w") as file:
            file.write(serialize_server_properties(properties))

    @property
    def server_jar(self) -> pathlib.Path:
        """The path to the server's JAR file."""
        return self.path.joinpath("server.jar")

    @property
    def lock_file(self) -> pathlib.Path:
        """The path to the server's lock file."""
        return self.path.joinpath(".lock")

    def is_locked(self) -> bool:
        """Whether or not the server is locked."""
        return self.lock_file.exists()

    def lock(self) -> None:
        """Lock the server."""
        self.lock_file.touch(exist_ok=True)

    def unlock(self) -> None:
        """Unlock the server."""
        if self.is_locked:
            os.remove(self.lock_file)

    @property
    def server_ip(self) -> str:
        """The server's IP address."""
        return self.properties.get("server-ip", "127.0.0.1")

    @property
    def server_port(self) -> int:
        """The server's port."""
        return self.properties.get("server-port", 25565)

    def status(self) -> bool:
        """Whether the server is currently running.

        The server is considered active if a connection can be made to it.
        (The connection is immediately closed after being opened.)

        Returns
        -------
        :class:`bool`
            ``True`` if the server is running, ``False`` otherwise.
        """
        address = (self.server_ip, self.server_port)

        try:
            with socket.create_connection(address, timeout=1.0):
                return True
        except OSError:
            return False

    def create(
        self,
        *,
        accept_eula: bool = False,
        version: Optional[str] = None,
        build: Optional[int] = None,
    ) -> None:
        """Make the server directory and generate the server.properties file.

        Parameters
        ----------
        accept_eula : :class:`bool`
            Whether to accept the EULA without prompting the user.

        Other Parameters
        ----------------
        version : :class:`str`, optional
            The version of Minecraft the server will run.
        build : :class:`int`, optional
            A specific build of the server to install. Must be a valid build
            for the specified version.
        """
        if self.exists:
            raise FileExistsError(f"Server {self.name!r} already exists.")

        self.path.mkdir(parents=True)
        _log.info(f"Created directory at {self.path}")

        self.update(version=version, build=build)
        self._generate_server_properties(accept_eula=accept_eula)
        _log.info(f"Succesfully created server {self.name!r}.")

    def update(
        self, *, version: Optional[str] = None, build: Optional[int] = None
    ) -> None:
        """Update the JAR file to the specified version and build, if possible.

        This method will download the `server.jar` file from PaperMC's API.
        The server will *not* stop or restart automatically.

        Parameters
        ----------
        version : :class:`str`, optional
            The version of the server to install.
        build : :class:`int`, optional
            The build of the server to install.
        """
        if not self.exists:
            raise FileNotFoundError(f"Server {self.name!r} does not exist.")

        name, content = self._download_server_jar(version, build)

        if name == self.server_jar.resolve().name:
            return

        fuji_dir = self.path.parents[1]
        paper_jar = fuji_dir.joinpath("jars", name)
        _log.info(f"Writing bytes to {paper_jar}...")
        paper_jar.write_bytes(content)

        _log.info(f"Creating symlink {self.server_jar} -> {paper_jar}")

        if self.server_jar.exists():
            self.server_jar.unlink()

        self.server_jar.symlink_to(paper_jar)
        _log.info(f"Successfully updated server {self.name!r}.")

    def _download_server_jar(
        self, version: Optional[str] = None, build: Optional[int] = None
    ) -> Tuple[str, bytes]:
        """Download the server JAR file from PaperMC's API.

        Parameters
        ----------
        version : :class:`str`, optional
            The version of the server to install.
        build : :class:`int`, optional
            The build of the server to install.

        Returns
        -------
        :class:`tuple`
            A tuple containing the name of the JAR file and its contents.
        """
        url = "https://papermc.io/api/v2/projects/paper"

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

        if build is not None:
            tmp = response.json()

            for b in tmp["builds"]:
                if b["build"] == build:
                    data = b
                    break
            else:
                raise RuntimeError(
                    f"Version {version} does not have build {build}"
                )
        else:
            data = response.json()["builds"][-1]

        build = build or data["build"]
        name = data["downloads"]["application"]["name"]
        jars = self.path.parents[1].joinpath("jars")

        for file in jars.iterdir():
            if name == file.name:
                _log.info("PaperMC is already up-to-date. Skipping download.")
                return name, file.read_bytes()

        url += f"/{build}/downloads/{name}"
        _log.info(f"Downloading PaperMC {version} build {build}...")

        if (response := requests.get(url)).status_code != 200:
            raise RuntimeError(f"Failed to download PaperMC: {response.text}")

        _log.info("Download complete.")
        return name, response.content

    def _generate_server_properties(
        self, /, *, accept_eula: bool = False
    ) -> None:
        """Runs the server to generate the server.properties file and EULA.

        This method is used by :meth:`create`. It is not necessarily meant to
        be called directly unless you know what you're doing.

        Parameters
        ----------
        accept_eula : :class:`bool`
            Whether to accept the EULA without prompting the user.
        """
        server_properties = self.path.joinpath("server.properties")

        if server_properties.exists():
            _log.warning(
                f"Server {self.name!r} already has a server.properties file."
            )
        else:
            cmd = ["java", "-jar", self.server_jar, "--nogui"]
            _log.info(f"Running command: {' '.join(cmd)!r}")
            subprocess.run(
                cmd,
                shell=False,
                cwd=self.path,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        eula = self.path.joinpath("eula.txt")

        if "eula=true" in eula.read_text().lower():
            _log.warning(
                f"Server {self.name!r} has already accepted the EULA."
            )
            return

        if not accept_eula:
            response = input(
                "Please read the Minecraft EULA before continuing:\n"
                "https://aka.ms/MinecraftEULA\n"
                "Do you accept the Minecraft EULA? [y/N] "
            )

            if response.lower() not in ("y", "yes"):
                raise RuntimeError("You must accept the Minecraft EULA.")

        eula.write_text("eula=true")

    def delete(self, *, skip_prompt: bool = False) -> None:
        """Delete the server directory.

        Parameters
        ----------
        skip_prompt : :class:`bool`
            Whether to skip the confirmation prompt.
        """
        if not self.exists:
            raise FileNotFoundError(f"Server {self.name!r} does not exist.")

        if not skip_prompt:
            response = input(
                f"Are you sure you want to delete {self.name!r}? [y/N] "
            )

            if response.lower() not in ("y", "yes"):
                return

        self.path.rmdir()
        _log.info(f"Successfully deleted server {self.name!r}.")

    def start(self) -> None:
        """Start the server."""
        raise NotImplementedError

    def stop(self) -> None:
        """Stop the server."""
        raise NotImplementedError

    def add_plugin(
        self,
        file_name: str,
        *,
        local_path: Optional[str] = None,
        url: Optional[str] = None,
    ) -> None:
        """Install or update a plugin in the server's "plugins" directory.

        Notes
        -----
        If the plugin already exists, it will be overwritten (updated).
        Either ``local_path`` or ``url`` must be specified. If both are
        specified, ``local_path`` will be searched first, then ``url``.

        Parameters
        ----------
        file_name : :class:`str`
            The name of the plugin's JAR file.
        local_path : :class:`str`, optional
            The path to the plugin's JAR file on the local filesystem.
        url : :class:`str`, optional
            The URL to the plugin's JAR file.
        """
        if not self.path.exists():
            raise FileNotFoundError(f"Server {self.name!r} does not exist.")

        if local_path is None and url is None:
            raise RuntimeError("Either local_path or url must be specified.")

        plugin = self.path.joinpath("plugins", file_name)
        plugin_data = None

        if local_path is not None:
            file = pathlib.Path(local_path).expanduser()

            if not file.exists():
                raise FileNotFoundError(f"File {file} does not exist.")

            if not file.is_file():
                raise RuntimeError(f"{file} is not a file.")

            if not file.suffix == ".jar":
                raise RuntimeError(f"{file} is not a JAR file.")

            try:
                plugin_data = file.read_bytes()
            except Exception as exc:
                _log.error(f"Failed to read {file}: {exc}")

        if url is not None and plugin_data is None:
            response = requests.get(url)

            if response.status_code != 200:
                raise RuntimeError(
                    f"Failed to download plugin: {response.text}"
                )

            try:
                plugin_data = response.content
            except Exception as exc:
                _log.error(f"Failed to download plugin: {exc}")

        if plugin_data is None:
            raise RuntimeError(f"Failed to get plugin data for {file_name!r}.")

        _log.info(f"Writing bytes to {plugin}...")
        plugin.write_bytes(plugin_data)
        _log.info(f"Successfully installed plugin {file_name!r}.")

    def remove_plugin(self, file_name: str) -> None:
        """Remove a plugin from the server's "plugins" directory.

        Parameters
        ----------
        file_name : :class:`str`
            The name of the plugin's JAR file.
        """
        if not self.path.exists():
            raise FileNotFoundError(f"Server {self.name!r} does not exist.")

        plugin = self.path.joinpath("plugins", file_name)

        if not plugin.exists():
            raise FileNotFoundError(f"Plugin {file_name!r} does not exist.")

        plugin.unlink()
        _log.info(f"Successfully deleted plugin {file_name!r}.")
