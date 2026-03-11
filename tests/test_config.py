"""Tests for jcli.device.config validation and connection param preparation."""

import pytest
from jcli.device.config import (
    validate_device_config,
    validate_all_devices,
    prepare_connection_params,
)


class TestValidateDeviceConfig:
    def test_valid_password_auth(self):
        config = {
            "ip": "10.0.1.1",
            "port": 22,
            "username": "admin",
            "auth": {"type": "password", "password": "secret"},
        }
        # Should not raise
        validate_device_config("r1", config)

    def test_valid_ssh_key_auth(self):
        config = {
            "ip": "10.0.1.1",
            "port": 22,
            "username": "admin",
            "auth": {"type": "ssh_key", "private_key_path": "/path/to/key"},
        }
        validate_device_config("r1", config)

    def test_valid_legacy_password_field(self):
        """Legacy format with top-level password field (no auth section)."""
        config = {
            "ip": "10.0.1.1",
            "port": 22,
            "username": "admin",
            "password": "legacy_pw",
        }
        validate_device_config("r1", config)

    def test_missing_required_fields(self):
        config = {"port": 22}
        with pytest.raises(ValueError, match="missing required fields.*ip.*username"):
            validate_device_config("r1", config)

    def test_missing_ip(self):
        config = {"port": 22, "username": "admin", "password": "pw"}
        with pytest.raises(ValueError, match="missing required fields.*ip"):
            validate_device_config("r1", config)

    def test_missing_auth_entirely(self):
        """No auth section and no legacy password field."""
        config = {"ip": "10.0.1.1", "port": 22, "username": "admin"}
        with pytest.raises(ValueError, match="missing authentication"):
            validate_device_config("r1", config)

    def test_auth_missing_type(self):
        config = {
            "ip": "10.0.1.1",
            "port": 22,
            "username": "admin",
            "auth": {"password": "pw"},
        }
        with pytest.raises(ValueError, match="missing 'type' field"):
            validate_device_config("r1", config)

    def test_password_auth_missing_password(self):
        config = {
            "ip": "10.0.1.1",
            "port": 22,
            "username": "admin",
            "auth": {"type": "password"},
        }
        with pytest.raises(ValueError, match="'password' field is missing"):
            validate_device_config("r1", config)

    def test_ssh_key_auth_missing_key_path(self):
        config = {
            "ip": "10.0.1.1",
            "port": 22,
            "username": "admin",
            "auth": {"type": "ssh_key"},
        }
        with pytest.raises(ValueError, match="'private_key_path' field is missing"):
            validate_device_config("r1", config)

    def test_unsupported_auth_type(self):
        config = {
            "ip": "10.0.1.1",
            "port": 22,
            "username": "admin",
            "auth": {"type": "kerberos"},
        }
        with pytest.raises(ValueError, match="unsupported auth type 'kerberos'"):
            validate_device_config("r1", config)

    def test_invalid_port_type_string(self):
        config = {
            "ip": "10.0.1.1",
            "port": "22",
            "username": "admin",
            "auth": {"type": "password", "password": "pw"},
        }
        with pytest.raises(ValueError, match="invalid 'port' value.*Expected integer.*str"):
            validate_device_config("r1", config)

    def test_invalid_port_type_none(self):
        config = {
            "ip": "10.0.1.1",
            "port": None,
            "username": "admin",
            "auth": {"type": "password", "password": "pw"},
        }
        with pytest.raises(ValueError, match="invalid 'port' value"):
            validate_device_config("r1", config)


class TestValidateAllDevices:
    def test_valid_multiple_devices(self, sample_devices):
        # Should not raise
        validate_all_devices(sample_devices)

    def test_empty_devices(self):
        # Should not raise, just warns
        validate_all_devices({})

    def test_one_bad_device_raises(self):
        devices = {
            "good": {
                "ip": "10.0.1.1",
                "port": 22,
                "username": "admin",
                "auth": {"type": "password", "password": "pw"},
            },
            "bad": {"ip": "10.0.2.1"},
        }
        with pytest.raises(ValueError, match="validation failed"):
            validate_all_devices(devices)


class TestPrepareConnectionParams:
    def test_password_auth(self):
        device = {
            "ip": "10.0.1.1",
            "port": 22,
            "username": "admin",
            "auth": {"type": "password", "password": "secret"},
        }
        params = prepare_connection_params(device, "r1")
        assert params["host"] == "10.0.1.1"
        assert params["port"] == 22
        assert params["user"] == "admin"
        assert params["password"] == "secret"
        assert params["gather_facts"] is False
        assert params["timeout"] == 360
        assert "ssh_private_key_file" not in params

    def test_ssh_key_auth(self):
        device = {
            "ip": "10.0.1.1",
            "port": 830,
            "username": "netops",
            "auth": {"type": "ssh_key", "private_key_path": "/keys/id_rsa"},
        }
        params = prepare_connection_params(device, "r1")
        assert params["ssh_private_key_file"] == "/keys/id_rsa"
        assert "password" not in params

    def test_legacy_password(self):
        device = {
            "ip": "10.0.1.1",
            "port": 22,
            "username": "admin",
            "password": "legacy",
        }
        params = prepare_connection_params(device, "r1")
        assert params["password"] == "legacy"

    def test_ssh_config_included(self):
        device = {
            "ip": "10.0.1.1",
            "port": 22,
            "username": "admin",
            "auth": {"type": "password", "password": "pw"},
            "ssh_config": "/home/user/.ssh/config",
        }
        params = prepare_connection_params(device, "r1")
        assert params["ssh_config"] == "/home/user/.ssh/config"

    def test_ssh_config_absent(self):
        device = {
            "ip": "10.0.1.1",
            "port": 22,
            "username": "admin",
            "auth": {"type": "password", "password": "pw"},
        }
        params = prepare_connection_params(device, "r1")
        assert "ssh_config" not in params

    def test_invalid_device_raises(self):
        with pytest.raises(ValueError):
            prepare_connection_params({"ip": "1.1.1.1"}, "bad")
