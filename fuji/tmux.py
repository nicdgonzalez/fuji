import logging
import subprocess

_log = logging.getLogger(__name__)


class TmuxSession:
    def __init__(self, name: str) -> None:
        self.name = name

    def is_alive(self) -> bool:
        try:
            _ = subprocess.check_output(
                ["tmux", "has-session", "-t", self.name],
                shell=False,
                stderr=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError:
            return False

        return True

    def create(self) -> None:
        if self.is_alive():
            _log.warning(f"Session {self.name!r} already exists.")
            return

        _ = subprocess.run(
            ["tmux", "new-session", "-d", "-s", self.name],
            shell=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        _log.info(f"Created session: {self.name!r}")

    def destroy(self) -> None:
        if not self.is_alive():
            _log.warning(f"Session {self.name!r} does not exist.")
            return

        _ = subprocess.run(
            ["tmux", "kill-session", "-t", self.name],
            shell=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        _log.info(f"Killed session: {self.name!r}")

    def send_keys(self, command: str) -> None:
        if not self.is_alive():
            _log.warning(f"Session {self.name!r} does not exist.")
            return

        _ = subprocess.run(
            ["tmux", "send-keys", "-t", self.name, command],
            shell=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        _log.info(f"Sent keys to session {self.name!r}: {command!r}")
