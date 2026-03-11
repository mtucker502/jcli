"""Tests for jcli.safety.blocklist command and config checking."""

import pytest
from jcli.safety.blocklist import (
    check_command_blocklist,
    check_config_blocklist,
    _split_pattern_tokens,
)


class TestCheckCommandBlocklist:
    def test_blocked_reboot(self, block_cmd_file):
        blocked, msg = check_command_blocklist("request system reboot", block_cmd_file)
        assert blocked is True
        assert "Blocked" in msg

    def test_blocked_halt(self, block_cmd_file):
        blocked, msg = check_command_blocklist("request system halt", block_cmd_file)
        assert blocked is True

    def test_blocked_zeroize(self, block_cmd_file):
        blocked, msg = check_command_blocklist("request system zeroize", block_cmd_file)
        assert blocked is True

    def test_blocked_regex_pattern(self, block_cmd_file):
        """The block file contains 'show .*secret.*' which should match regex."""
        blocked, msg = check_command_blocklist("show secret-keys detail", block_cmd_file)
        assert blocked is True
        assert "secret" in msg

    def test_allowed_show_version(self, block_cmd_file):
        blocked, msg = check_command_blocklist("show version", block_cmd_file)
        assert blocked is False
        assert msg is None

    def test_allowed_show_bgp(self, block_cmd_file):
        blocked, msg = check_command_blocklist("show bgp summary", block_cmd_file)
        assert blocked is False
        assert msg is None

    def test_empty_command_not_blocked(self, block_cmd_file):
        blocked, msg = check_command_blocklist("", block_cmd_file)
        assert blocked is False

    def test_missing_blocklist_file_not_blocked(self, tmp_path):
        fake = str(tmp_path / "nonexistent_block.cmd")
        blocked, msg = check_command_blocklist("request system reboot", fake)
        assert blocked is False
        assert msg is None

    def test_whitespace_normalization(self, block_cmd_file):
        """Extra whitespace in command should be normalized before matching."""
        blocked, msg = check_command_blocklist(
            "request   system   reboot", block_cmd_file
        )
        assert blocked is True


class TestCheckConfigBlocklist:
    def test_blocked_root_auth(self, block_cfg_file):
        config = "set system root-authentication encrypted-password $6$abc"
        blocked, msg = check_config_blocklist(config, block_cfg_file)
        assert blocked is True
        assert "root-authentication" in msg

    def test_blocked_user_auth_pattern(self, block_cfg_file):
        config = "set system login user admin authentication plain-text-password"
        blocked, msg = check_config_blocklist(config, block_cfg_file)
        assert blocked is True

    def test_blocked_delete_system(self, block_cfg_file):
        config = "delete system services"
        blocked, msg = check_config_blocklist(config, block_cfg_file)
        assert blocked is True

    def test_allowed_interface_config(self, block_cfg_file):
        config = "set interfaces ge-0/0/0 unit 0 family inet address 10.0.0.1/30"
        blocked, msg = check_config_blocklist(config, block_cfg_file)
        assert blocked is False
        assert msg is None

    def test_allowed_hostname_config(self, block_cfg_file):
        config = "set system host-name lab-router"
        blocked, msg = check_config_blocklist(config, block_cfg_file)
        assert blocked is False

    def test_empty_config_not_blocked(self, block_cfg_file):
        blocked, msg = check_config_blocklist("", block_cfg_file)
        assert blocked is False

    def test_multiline_config_one_blocked(self, block_cfg_file):
        config = (
            "set interfaces ge-0/0/0 description uplink\n"
            "set system root-authentication encrypted-password $6$bad\n"
            "set protocols bgp group peers type external\n"
        )
        blocked, msg = check_config_blocklist(config, block_cfg_file)
        assert blocked is True
        assert "root-authentication" in msg

    def test_missing_blocklist_file_not_blocked(self, tmp_path):
        fake = str(tmp_path / "nonexistent_block.cfg")
        blocked, msg = check_config_blocklist(
            "set system root-authentication bad", fake
        )
        assert blocked is False
        assert msg is None


class TestSplitPatternTokens:
    def test_simple_tokens(self):
        tokens = _split_pattern_tokens("set system root-authentication")
        assert tokens == ["set", "system", "root-authentication"]

    def test_regex_with_char_class(self):
        """Spaces inside character classes should not split the token."""
        tokens = _split_pattern_tokens("set system login user ([^ ]+) authentication")
        assert tokens == ["set", "system", "login", "user", "([^ ]+)", "authentication"]

    def test_empty_pattern(self):
        assert _split_pattern_tokens("") == []

    def test_single_token(self):
        assert _split_pattern_tokens("delete") == ["delete"]
