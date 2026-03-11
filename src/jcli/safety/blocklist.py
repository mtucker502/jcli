"""Command and config blocklist safety checking."""
import logging
import os
import re
from pathlib import Path

log = logging.getLogger(__name__)


def check_command_blocklist(command: str, block_file: str | None = None) -> tuple[bool, str | None]:
    """Check if command matches any blocked pattern. Returns (is_blocked, message)."""
    if not command:
        return False, None

    block_file = block_file or os.environ.get("JCLI_BLOCK_CMD", "block.cmd")
    block_file_path = Path(block_file)

    if not block_file_path.is_absolute() and not block_file_path.exists():
        # Try relative to package directory
        block_file_path = Path(__file__).resolve().parent.parent.parent.parent / block_file

    if not block_file_path.exists():
        # No blocklist file = no restrictions (different from jmcp which blocks everything)
        log.debug(f"Blocklist file '{block_file_path}' not found, skipping check")
        return False, None

    try:
        with open(block_file_path, "r", encoding="utf-8") as f:
            blocked_patterns = [
                line.strip() for line in f if line.strip() and not line.strip().startswith("#")
            ]
    except OSError as e:
        return True, f"Unable to read blocklist file '{block_file_path}': {e}"

    normalized_command = " ".join(command.split())

    for pattern in blocked_patterns:
        try:
            if re.match(pattern, normalized_command):
                return True, (
                    f"Blocked: command '{normalized_command}' matches pattern '{pattern}'"
                )
        except re.error as e:
            return True, f"Invalid regex in '{block_file_path}': '{pattern}' ({e})"

    return False, None


def check_config_blocklist(config_text: str, block_file: str | None = None) -> tuple[bool, str | None]:
    """Check if config text matches any blocked pattern. Returns (is_blocked, message)."""
    if not config_text:
        return False, None

    block_file = block_file or os.environ.get("JCLI_BLOCK_CFG", "block.cfg")
    block_file_path = Path(block_file)

    if not block_file_path.is_absolute() and not block_file_path.exists():
        block_file_path = Path(__file__).resolve().parent.parent.parent.parent / block_file

    if not block_file_path.exists():
        log.debug(f"Blocklist file '{block_file_path}' not found, skipping check")
        return False, None

    try:
        with open(block_file_path, "r", encoding="utf-8") as f:
            blocked_patterns = [
                line.strip() for line in f if line.strip() and not line.strip().startswith("#")
            ]
    except OSError as e:
        return True, f"Unable to read blocklist file '{block_file_path}': {e}"

    config_lines = [" ".join(line.split()) for line in config_text.splitlines() if line.strip()]

    for pattern in blocked_patterns:
        pattern_tokens = _split_pattern_tokens(pattern)

        for config_line in config_lines:
            config_tokens = config_line.split()

            if len(config_tokens) < len(pattern_tokens):
                continue

            token_match = True
            for config_token, pattern_token in zip(config_tokens, pattern_tokens):
                try:
                    if not re.fullmatch(pattern_token, config_token):
                        token_match = False
                        break
                except re.error as e:
                    return True, f"Invalid regex in '{block_file_path}': '{pattern_token}' ({e})"

            if token_match:
                return True, (
                    f"Blocked: config line '{config_line}' matches pattern '{pattern}'"
                )

    return False, None


def _split_pattern_tokens(pattern_line: str) -> list[str]:
    """Split pattern into tokens, preserving spaces inside regex char classes like [^ ]+."""
    tokens: list[str] = []
    current: list[str] = []
    in_char_class = False
    escaped = False

    for ch in pattern_line:
        if escaped:
            current.append(ch)
            escaped = False
            continue

        if ch == "\\":
            current.append(ch)
            escaped = True
            continue

        if ch == "[":
            in_char_class = True
            current.append(ch)
            continue

        if ch == "]" and in_char_class:
            in_char_class = False
            current.append(ch)
            continue

        if ch.isspace() and not in_char_class:
            if current:
                tokens.append("".join(current))
                current = []
            continue

        current.append(ch)

    if current:
        tokens.append("".join(current))

    return tokens
