"""Shared fixtures for jcli test suite."""

import json
import pytest
from pathlib import Path


@pytest.fixture
def sample_devices():
    """Sample devices dict with password and ssh_key auth types."""
    return {
        "router1": {
            "ip": "10.0.1.1",
            "port": 22,
            "username": "admin",
            "auth": {
                "type": "password",
                "password": "secret123",
            },
        },
        "router2": {
            "ip": "10.0.2.1",
            "port": 830,
            "username": "netops",
            "auth": {
                "type": "ssh_key",
                "private_key_path": "/home/user/.ssh/id_rsa",
            },
        },
        "router3": {
            "ip": "10.0.3.1",
            "port": 22,
            "username": "admin",
            "auth": {
                "type": "password",
                "password": "pass3",
            },
            "ssh_config": "/home/user/.ssh/config",
        },
    }


@pytest.fixture
def inventory_file(tmp_path, sample_devices):
    """Write sample devices to a temp JSON file and return its path."""
    path = tmp_path / "devices.json"
    path.write_text(json.dumps(sample_devices, indent=4))
    return str(path)


@pytest.fixture
def empty_inventory_file(tmp_path):
    """Write an empty devices dict to a temp JSON file."""
    path = tmp_path / "devices.json"
    path.write_text(json.dumps({}, indent=4))
    return str(path)


@pytest.fixture
def block_cmd_file(tmp_path):
    """Create a temp command blocklist file."""
    content = """\
# Blocked operational commands
request system reboot
request system halt
request system zeroize
show .*secret.*
"""
    path = tmp_path / "block.cmd"
    path.write_text(content)
    return str(path)


@pytest.fixture
def block_cfg_file(tmp_path):
    """Create a temp config blocklist file."""
    content = """\
# Blocked configuration patterns
set system root-authentication
set system login user ([^ ]+) authentication
delete system
"""
    path = tmp_path / "block.cfg"
    path.write_text(content)
    return str(path)


@pytest.fixture
def template_file(tmp_path):
    """Create a temp Jinja2 template file."""
    content = """\
set interfaces {{ interface }} unit 0 family inet address {{ ip_address }}
set interfaces {{ interface }} description "{{ description }}"
"""
    path = tmp_path / "template.j2"
    path.write_text(content)
    return str(path)


@pytest.fixture
def vars_file(tmp_path):
    """Create a temp YAML variables file."""
    content = """\
interface: ge-0/0/0
ip_address: 192.168.1.1/24
description: Uplink to core
"""
    path = tmp_path / "vars.yaml"
    path.write_text(content)
    return str(path)
