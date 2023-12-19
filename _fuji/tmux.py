"""
tmux
====

This module provides a simple wrapper around the `tmux` command-line utility.

"""
from __future__ import annotations

import logging
import subprocess
from typing import Any


class TmuxSession:
    """Represents a tmux session.

    Parameters
    ----------
    name : str
        The name of the tmux session.
    """

    def __init__(self, name: str, *args: Any, **kwargs: Any) -> None:
        self.name = name
        self._log = logging.getLogger(__name__)

    def exists(self) -> bool:
        """Check that the session is valid."""
        try:
            _ = subprocess.check_output(
                ["tmux", "has-session", "-t", self.name],
                shell=False,
                stderr=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError:
            return False
        else:
            return True

    def new(self) -> None:
        """Create a new tmux session."""
        if self.exists():
            self._log.warning(f"Session '{self.name}' already exists.")
            return

        _ = subprocess.run(
            ["tmux", "new-session", "-d", "-s", self.name],
            shell=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._log.info(f"Created new session: '{self.name}'")

    def kill(self) -> None:
        """Kill the tmux session."""
        if not self.exists():
            self._log.warning(f"Session '{self.name}' does not exist.")
            return

        _ = subprocess.run(
            ["tmux", "kill-session", "-t", self.name],
            shell=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._log.info(f"Killed session: '{self.name}'")

    def send_keys(
        self, command: str, enter: bool = True, **params: Any
    ) -> None:
        """Send a command to the tmux session."""
        if not self.exists():
            self._log.warning(f"Session '{self.name}' does not exist.")
            return

        params.setdefault("shell", False)
        cmd = [
            "tmux",
            "send-keys",
            "-t",
            self.name,
            command,
            "Enter" if enter else "",
        ]
        _ = subprocess.run(cmd, **params)
        self._log.info(f"Sent command to session '{self.name}': '{command}'")
