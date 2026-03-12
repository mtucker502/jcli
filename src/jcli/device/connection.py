"""PyEZ connection wrapper for Junos devices."""

import json
import logging
import time

from jnpr.junos import Device
from jnpr.junos.exception import ConnectError

from jcli.device.config import prepare_connection_params

log = logging.getLogger(__name__)


class JunosConnection:
    def __init__(self, device_info: dict, router_name: str, timeout: int = 360):
        self.device_info = device_info
        self.router_name = router_name
        self.timeout = timeout
        self._device = None

    def _connect(self):
        connect_params = prepare_connection_params(self.device_info, self.router_name)
        self._device = Device(**connect_params)
        self._device.open()
        self._device.timeout = self.timeout
        return self._device

    def run_command(self, command: str) -> str:
        """Execute a CLI command and return output string."""
        try:
            with Device(**prepare_connection_params(self.device_info, self.router_name)) as dev:
                dev.timeout = self.timeout
                return dev.cli(command, warning=False)
        except ConnectError as ce:
            raise ConnectionError(f"Connection error to {self.router_name}: {ce}") from ce

    def run_commands(self, commands: list[str], stop_on_error: bool = False) -> list[dict]:
        """Execute multiple CLI commands on one connection.

        Returns list of dicts with command, output, status, and duration.
        """
        results = []
        try:
            with Device(**prepare_connection_params(self.device_info, self.router_name)) as dev:
                dev.timeout = self.timeout
                for cmd in commands:
                    start = time.time()
                    try:
                        output = dev.cli(cmd, warning=False)
                        results.append({
                            "command": cmd,
                            "output": output,
                            "status": "success",
                            "duration": round(time.time() - start, 3),
                        })
                    except Exception as e:
                        results.append({
                            "command": cmd,
                            "output": str(e),
                            "status": "failed",
                            "duration": round(time.time() - start, 3),
                        })
                        if stop_on_error:
                            break
        except ConnectError as ce:
            raise ConnectionError(f"Connection error to {self.router_name}: {ce}") from ce
        return results

    def get_config(self, section: str | None = None) -> str:
        """Get config in set format, optionally filtered to a section."""
        if section:
            cmd = (
                f"show configuration {section}"
                " | display inheritance no-comments | display set | no-more"
            )
            return self.run_command(cmd)
        return self.run_command(
            "show configuration | display inheritance no-comments | display set | no-more"
        )

    def get_config_diff(self, rollback_version: int = 1) -> str:
        """Get config diff against rollback version."""
        return self.run_command(
            f"show configuration | compare rollback {rollback_version}"
        )

    def get_facts(self) -> dict:
        """Gather device facts."""
        try:
            connect_params = prepare_connection_params(self.device_info, self.router_name)
            connect_params["timeout"] = self.timeout
            with Device(**connect_params) as dev:
                return dict(dev.facts)
        except ConnectError as ce:
            raise ConnectionError(f"Connection error to {self.router_name}: {ce}") from ce
