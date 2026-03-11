"""CLI integration tests using Click's CliRunner.

Only tests commands that do NOT require device connectivity.
"""

import json
import pytest
from click.testing import CliRunner

from jcli.cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


class TestTopLevelCli:
    def test_help(self, runner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Junos" in result.output or "jcli" in result.output.lower()
        assert "device" in result.output
        assert "command" in result.output
        assert "config" in result.output

    def test_version(self, runner):
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "jcli" in result.output
        assert "0.1.0" in result.output


class TestDeviceList:
    def test_device_list(self, runner, inventory_file):
        result = runner.invoke(cli, ["-f", inventory_file, "device", "list"])
        assert result.exit_code == 0
        assert "router1" in result.output
        assert "router2" in result.output
        assert "router3" in result.output

    def test_device_list_json(self, runner, inventory_file):
        result = runner.invoke(cli, ["-j", "-f", inventory_file, "device", "list"])
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert "routers" in parsed
        assert "router1" in parsed["routers"]

    def test_device_list_no_inventory(self, runner, tmp_path):
        empty_inv = str(tmp_path / "empty.json")
        (tmp_path / "empty.json").write_text("{}")
        result = runner.invoke(cli, ["-f", empty_inv, "device", "list"])
        assert result.exit_code != 0

    def test_device_list_missing_file(self, runner, tmp_path):
        missing = str(tmp_path / "does_not_exist.json")
        result = runner.invoke(cli, ["-f", missing, "device", "list"])
        # Missing file means empty inventory -> "No devices configured" error
        assert result.exit_code != 0


class TestDeviceAdd:
    def test_add_password_device(self, runner, inventory_file):
        result = runner.invoke(
            cli,
            [
                "-f", inventory_file,
                "device", "add", "new_router",
                "--ip", "10.0.5.1",
                "--user", "admin",
                "--auth-type", "password",
                "--password", "mypassword",
            ],
        )
        assert result.exit_code == 0
        assert "Added" in result.output
        assert "new_router" in result.output

        # Verify it's in the inventory file
        with open(inventory_file) as f:
            devices = json.load(f)
        assert "new_router" in devices
        assert devices["new_router"]["ip"] == "10.0.5.1"
        assert devices["new_router"]["auth"]["type"] == "password"

    def test_add_ssh_key_device(self, runner, inventory_file):
        result = runner.invoke(
            cli,
            [
                "-f", inventory_file,
                "device", "add", "key_router",
                "--ip", "10.0.6.1",
                "--user", "netops",
                "--auth-type", "ssh_key",
                "--key-file", "/home/netops/.ssh/id_rsa",
            ],
        )
        assert result.exit_code == 0
        assert "Added" in result.output

        with open(inventory_file) as f:
            devices = json.load(f)
        assert "key_router" in devices
        assert devices["key_router"]["auth"]["type"] == "ssh_key"
        assert devices["key_router"]["auth"]["private_key_path"] == "/home/netops/.ssh/id_rsa"

    def test_add_with_ssh_config(self, runner, inventory_file):
        result = runner.invoke(
            cli,
            [
                "-f", inventory_file,
                "device", "add", "jump_router",
                "--ip", "10.0.7.1",
                "--user", "admin",
                "--auth-type", "password",
                "--password", "pw",
                "--ssh-config", "/home/admin/.ssh/config",
            ],
        )
        assert result.exit_code == 0
        with open(inventory_file) as f:
            devices = json.load(f)
        assert devices["jump_router"]["ssh_config"] == "/home/admin/.ssh/config"

    def test_add_password_auth_without_password_flag(self, runner, inventory_file):
        result = runner.invoke(
            cli,
            [
                "-f", inventory_file,
                "device", "add", "bad",
                "--ip", "10.0.8.1",
                "--user", "admin",
                "--auth-type", "password",
            ],
        )
        assert result.exit_code != 0

    def test_add_ssh_key_auth_without_key_file(self, runner, inventory_file):
        result = runner.invoke(
            cli,
            [
                "-f", inventory_file,
                "device", "add", "bad",
                "--ip", "10.0.9.1",
                "--user", "admin",
                "--auth-type", "ssh_key",
            ],
        )
        assert result.exit_code != 0

    def test_add_with_custom_port(self, runner, inventory_file):
        result = runner.invoke(
            cli,
            [
                "-f", inventory_file,
                "device", "add", "custom_port",
                "--ip", "10.0.10.1",
                "--port", "830",
                "--user", "admin",
                "--auth-type", "password",
                "--password", "pw",
            ],
        )
        assert result.exit_code == 0
        with open(inventory_file) as f:
            devices = json.load(f)
        assert devices["custom_port"]["port"] == 830


class TestDeviceReload:
    def test_reload_same_file(self, runner, inventory_file):
        result = runner.invoke(cli, ["-f", inventory_file, "device", "reload"])
        assert result.exit_code == 0
        assert "Reloaded" in result.output
        assert "3" in result.output

    def test_reload_with_new_path(self, runner, inventory_file, tmp_path):
        new_inv = tmp_path / "new.json"
        new_inv.write_text(json.dumps({
            "single": {
                "ip": "1.1.1.1",
                "port": 22,
                "username": "u",
                "auth": {"type": "password", "password": "p"},
            }
        }))
        result = runner.invoke(
            cli, ["-f", inventory_file, "device", "reload", str(new_inv)]
        )
        assert result.exit_code == 0
        assert "Reloaded" in result.output


class TestConfigTemplate:
    def test_template_render_only(self, runner, inventory_file, template_file, vars_file):
        """Render without --apply should just print the rendered output."""
        result = runner.invoke(
            cli,
            [
                "-f", inventory_file,
                "config", "template",
                "--template", template_file,
                "--vars", vars_file,
            ],
        )
        assert result.exit_code == 0
        assert "ge-0/0/0" in result.output
        assert "192.168.1.1/24" in result.output

    def test_template_missing_template_file(self, runner, inventory_file, vars_file, tmp_path):
        fake = str(tmp_path / "nope.j2")
        result = runner.invoke(
            cli,
            [
                "-f", inventory_file,
                "config", "template",
                "--template", fake,
                "--vars", vars_file,
            ],
        )
        assert result.exit_code != 0

    def test_template_missing_vars_file(self, runner, inventory_file, template_file, tmp_path):
        fake = str(tmp_path / "nope.yaml")
        result = runner.invoke(
            cli,
            [
                "-f", inventory_file,
                "config", "template",
                "--template", template_file,
                "--vars", fake,
            ],
        )
        assert result.exit_code != 0
