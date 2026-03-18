"""Device inventory management — loads/saves the devices.json file."""

import copy
import json
import logging
import os
from pathlib import Path

from jcli.device.config import validate_all_devices, validate_device_config

log = logging.getLogger(__name__)


class DeviceInventory:
    def __init__(self, path: str | None = None):
        self.path = Path(path) if path else Path("devices.json")
        self.devices: dict[str, dict] = {}

    def load(self) -> None:
        if not self.path.exists():
            log.warning(f"Inventory file '{self.path}' not found")
            self.devices = {}
            return

        with open(self.path) as f:
            self.devices = json.load(f)

        validate_all_devices(self.devices)
        log.info(f"Loaded {len(self.devices)} device(s) from '{self.path}'")

    def save(self) -> None:
        with open(self.path, "w") as f:
            json.dump(self.devices, f, indent=4)
        os.chmod(self.path, 0o600)
        log.info(f"Saved {len(self.devices)} device(s) to '{self.path}'")

    def reload(self, path: str | None = None) -> int:
        if path:
            self.path = Path(path)
        old_count = len(self.devices)
        self.load()
        return old_count

    def list_devices(self) -> list[str]:
        return list(self.devices.keys())

    def get_device(self, name: str) -> dict:
        if name not in self.devices:
            raise KeyError(f"Router '{name}' not found in device inventory")
        return self.devices[name]

    def get_device_sanitized(self, name: str) -> dict:
        device = copy.deepcopy(self.get_device(name))
        if "auth" in device:
            device["auth"].pop("password", None)
            device["auth"].pop("private_key_path", None)
        device.pop("password", None)
        device.pop("ssh_config", None)
        return device

    def list_devices_sanitized(self) -> dict:
        result = {}
        for name in self.devices:
            result[name] = self.get_device_sanitized(name)
        return result

    def add_device(self, name: str, config: dict) -> None:
        validate_device_config(name, config)
        self.devices[name] = config
        log.info(f"Added device '{name}'")

    def remove_device(self, name: str) -> None:
        if name not in self.devices:
            raise KeyError(f"Router '{name}' not found in device inventory")
        del self.devices[name]
        log.info(f"Removed device '{name}'")
