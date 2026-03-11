"""Tests for jcli.device.inventory.DeviceInventory."""

import json
import pytest
from jcli.device.inventory import DeviceInventory


class TestLoadFromFile:
    def test_load_devices(self, inventory_file, sample_devices):
        inv = DeviceInventory(inventory_file)
        inv.load()
        assert inv.devices == sample_devices
        assert len(inv.devices) == 3

    def test_load_missing_file_succeeds_with_empty(self, tmp_path):
        path = str(tmp_path / "nonexistent.json")
        inv = DeviceInventory(path)
        inv.load()
        assert inv.devices == {}

    def test_load_empty_inventory(self, empty_inventory_file):
        inv = DeviceInventory(empty_inventory_file)
        inv.load()
        assert inv.devices == {}


class TestListDevices:
    def test_list_devices(self, inventory_file):
        inv = DeviceInventory(inventory_file)
        inv.load()
        names = inv.list_devices()
        assert sorted(names) == ["router1", "router2", "router3"]

    def test_list_devices_empty(self, tmp_path):
        path = str(tmp_path / "missing.json")
        inv = DeviceInventory(path)
        inv.load()
        assert inv.list_devices() == []


class TestGetDevice:
    def test_get_device(self, inventory_file, sample_devices):
        inv = DeviceInventory(inventory_file)
        inv.load()
        device = inv.get_device("router1")
        assert device == sample_devices["router1"]
        assert device["ip"] == "10.0.1.1"

    def test_get_device_missing_raises(self, inventory_file):
        inv = DeviceInventory(inventory_file)
        inv.load()
        with pytest.raises(KeyError, match="Router 'nonexistent' not found"):
            inv.get_device("nonexistent")


class TestAddDeviceAndSave:
    def test_add_device_and_save(self, inventory_file):
        inv = DeviceInventory(inventory_file)
        inv.load()
        new_device = {
            "ip": "10.0.4.1",
            "port": 22,
            "username": "ops",
            "auth": {"type": "password", "password": "newpass"},
        }
        inv.add_device("router4", new_device)
        assert "router4" in inv.devices
        inv.save()

        # Reload from disk and verify persistence
        inv2 = DeviceInventory(inventory_file)
        inv2.load()
        assert "router4" in inv2.devices
        assert inv2.get_device("router4")["ip"] == "10.0.4.1"

    def test_add_device_with_invalid_config_raises(self, inventory_file):
        inv = DeviceInventory(inventory_file)
        inv.load()
        with pytest.raises(ValueError, match="missing required fields"):
            inv.add_device("bad", {"ip": "1.1.1.1"})


class TestListDevicesSanitized:
    def test_strips_password(self, inventory_file):
        inv = DeviceInventory(inventory_file)
        inv.load()
        sanitized = inv.list_devices_sanitized()
        # router1 uses password auth -- password should be stripped
        assert "password" not in sanitized["router1"]["auth"]
        # Original should still have it
        assert "password" in inv.devices["router1"]["auth"]

    def test_strips_private_key_path(self, inventory_file):
        inv = DeviceInventory(inventory_file)
        inv.load()
        sanitized = inv.list_devices_sanitized()
        assert "private_key_path" not in sanitized["router2"]["auth"]

    def test_strips_ssh_config(self, inventory_file):
        inv = DeviceInventory(inventory_file)
        inv.load()
        sanitized = inv.list_devices_sanitized()
        assert "ssh_config" not in sanitized["router3"]
        # Original still has it
        assert "ssh_config" in inv.devices["router3"]

    def test_preserves_non_sensitive_fields(self, inventory_file):
        inv = DeviceInventory(inventory_file)
        inv.load()
        sanitized = inv.list_devices_sanitized()
        assert sanitized["router1"]["ip"] == "10.0.1.1"
        assert sanitized["router1"]["username"] == "admin"
        assert sanitized["router1"]["port"] == 22


class TestReload:
    def test_reload_same_file(self, inventory_file, sample_devices):
        inv = DeviceInventory(inventory_file)
        inv.load()
        old_count = inv.reload()
        assert old_count == 3
        assert len(inv.devices) == 3

    def test_reload_with_new_path(self, inventory_file, tmp_path):
        inv = DeviceInventory(inventory_file)
        inv.load()
        assert len(inv.devices) == 3

        new_path = tmp_path / "new_devices.json"
        new_devices = {
            "only_one": {
                "ip": "10.0.99.1",
                "port": 22,
                "username": "test",
                "auth": {"type": "password", "password": "pw"},
            }
        }
        new_path.write_text(json.dumps(new_devices))
        old_count = inv.reload(str(new_path))
        assert old_count == 3
        assert len(inv.devices) == 1
        assert "only_one" in inv.devices


class TestRemoveDevice:
    def test_remove_device(self, inventory_file):
        inv = DeviceInventory(inventory_file)
        inv.load()
        inv.remove_device("router1")
        assert "router1" not in inv.devices
        assert len(inv.devices) == 2

    def test_remove_missing_device_raises(self, inventory_file):
        inv = DeviceInventory(inventory_file)
        inv.load()
        with pytest.raises(KeyError, match="Router 'nope' not found"):
            inv.remove_device("nope")
