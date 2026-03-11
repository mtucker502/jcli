"""Constructs realistic MCP vs CLI vs Skill payloads for token comparison.

Builds the exact text an LLM sees in its context window for each approach:
- MCP: tool schemas + tool_use request blocks + TextContent responses with annotations
- CLI: Bash tool_use request blocks + raw stdout text responses
- Skill: SKILL.md context + Bash tool_use request blocks + raw stdout text responses
"""

import json
from pathlib import Path

SAMPLE_DIR = Path(__file__).parent / "sample_data"
SKILL_PATH = Path(__file__).parent.parent / "skills" / "SKILL.md"

# --- MCP tool definitions (from jmcp.py lines 952-1038) ---

MCP_TOOLS = [
    {
        "name": "execute_junos_command",
        "description": "Execute a Junos command on the router",
        "inputSchema": {
            "type": "object",
            "properties": {
                "router_name": {
                    "type": "string",
                    "description": "The name of the router",
                },
                "command": {
                    "type": "string",
                    "description": "The command to execute on the router",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Command timeout in seconds",
                    "default": 360,
                },
            },
            "required": ["router_name", "command"],
        },
    },
    {
        "name": "get_junos_config",
        "description": "Get the configuration of the router",
        "inputSchema": {
            "type": "object",
            "properties": {
                "router_name": {
                    "type": "string",
                    "description": "The name of the router",
                }
            },
            "required": ["router_name"],
        },
    },
    {
        "name": "junos_config_diff",
        "description": "Get the configuration diff against a rollback version",
        "inputSchema": {
            "type": "object",
            "properties": {
                "router_name": {
                    "type": "string",
                    "description": "The name of the router",
                },
                "version": {
                    "type": "integer",
                    "description": "Rollback version to compare against (1-49)",
                    "default": 1,
                },
            },
            "required": ["router_name"],
        },
    },
    {
        "name": "gather_device_facts",
        "description": "Gather Junos device facts from the router",
        "inputSchema": {
            "type": "object",
            "properties": {
                "router_name": {
                    "type": "string",
                    "description": "The name of the router",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Connection timeout in seconds",
                    "default": 360,
                },
            },
            "required": ["router_name"],
        },
    },
    {
        "name": "get_router_list",
        "description": "Get list of available Junos routers",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "load_and_commit_config",
        "description": "Load and commit configuration on a Junos router",
        "inputSchema": {
            "type": "object",
            "properties": {
                "router_name": {
                    "type": "string",
                    "description": "The name of the router",
                },
                "config_text": {
                    "type": "string",
                    "description": "The configuration text to load",
                },
                "config_format": {
                    "type": "string",
                    "description": "Format: set, text, or xml",
                    "default": "set",
                },
                "commit_comment": {
                    "type": "string",
                    "description": "Commit comment",
                    "default": "Configuration loaded via MCP",
                },
            },
            "required": ["router_name", "config_text"],
        },
    },
    {
        "name": "add_device",
        "description": "Add a new Junos device with interactive elicitation for device details",
        "inputSchema": {
            "type": "object",
            "properties": {
                "device_name": {
                    "type": "string",
                    "description": "Device name/identifier",
                    "default": "",
                },
                "device_ip": {
                    "type": "string",
                    "description": "Device IP address",
                    "default": "",
                },
                "device_port": {
                    "type": "integer",
                    "description": "SSH port (default: 22)",
                    "default": 0,
                },
                "username": {
                    "type": "string",
                    "description": "Username for authentication",
                    "default": "",
                },
                "ssh_key_path": {
                    "type": "string",
                    "description": "Path to SSH private key file",
                    "default": "",
                },
            },
            "required": [],
        },
    },
]

# --- Operation definitions ---

OPERATIONS = {
    "list_routers": {
        "mcp_tool": "get_router_list",
        "mcp_input": {},
        "cli_command": "jcli device list",
        "sample_file": "router_list.txt",
        "mcp_annotations": None,
    },
    "device_facts": {
        "mcp_tool": "gather_device_facts",
        "mcp_input": {"router_name": "vsrx1"},
        "cli_command": "jcli device facts vsrx1",
        "sample_file": "device_facts.json",
        "mcp_annotations": {"router_name": "vsrx1"},
    },
    "execute_command": {
        "mcp_tool": "execute_junos_command",
        "mcp_input": {"router_name": "vsrx1", "command": "show bgp summary"},
        "cli_command": 'jcli command run vsrx1 "show bgp summary"',
        "sample_file": "show_bgp_summary.txt",
        "mcp_annotations": {
            "router_name": "vsrx1",
            "command": "show bgp summary",
            "metadata": {
                "execution_duration": "1.234s",
                "start_time": "2026-03-11T14:20:00Z",
                "end_time": "2026-03-11T14:20:01Z",
            },
        },
    },
    "show_config": {
        "mcp_tool": "get_junos_config",
        "mcp_input": {"router_name": "vsrx1"},
        "cli_command": "jcli config show vsrx1",
        "sample_file": "show_config.txt",
        "mcp_annotations": {"router_name": "vsrx1"},
    },
    "config_diff": {
        "mcp_tool": "junos_config_diff",
        "mcp_input": {"router_name": "vsrx1"},
        "cli_command": "jcli config diff vsrx1",
        "sample_file": "config_diff.txt",
        "mcp_annotations": {"router_name": "vsrx1", "config_diff_version": 1},
    },
    "load_config": {
        "mcp_tool": "load_and_commit_config",
        "mcp_input": {
            "router_name": "vsrx1",
            "config_text": "set system host-name new",
            "config_format": "set",
            "commit_comment": "Configuration loaded via MCP",
        },
        "cli_command": 'jcli config load vsrx1 "set system host-name new"',
        "sample_file": "load_result.txt",
        "mcp_annotations": {
            "router_name": "vsrx1",
            "config_text": "set system host-name new",
            "config_format": "set",
            "commit_comment": "Configuration loaded via MCP",
        },
    },
}


def _load_sample(filename: str) -> str:
    """Load sample data file contents."""
    return (SAMPLE_DIR / filename).read_text()


def build_mcp_schemas() -> str:
    """Serialize all 7 MCP tool definitions as JSON.

    This is what gets injected into the LLM's context when MCP tools are registered.
    """
    return json.dumps(MCP_TOOLS, indent=2)


def build_mcp_request(operation: str) -> str:
    """Build the tool_use content block for an MCP tool call."""
    op = OPERATIONS[operation]
    block = {
        "type": "tool_use",
        "id": "toolu_benchmark_mcp",
        "name": op["mcp_tool"],
        "input": op["mcp_input"],
    }
    return json.dumps(block)


def build_cli_request(operation: str) -> str:
    """Build the Bash tool_use content block for a CLI command."""
    op = OPERATIONS[operation]
    block = {
        "type": "tool_use",
        "id": "toolu_benchmark_cli",
        "name": "Bash",
        "input": {"command": op["cli_command"]},
    }
    return json.dumps(block)


def build_mcp_response(operation: str) -> str:
    """Build the MCP tool result with TextContent wrapping and annotations.

    Faithfully reproduces the annotation structure from each jmcp handler.
    """
    op = OPERATIONS[operation]
    raw_output = _load_sample(op["sample_file"])

    content_block = {"type": "text", "text": raw_output}
    if op["mcp_annotations"] is not None:
        content_block["annotations"] = op["mcp_annotations"]

    result = {
        "type": "tool_result",
        "tool_use_id": "toolu_benchmark_mcp",
        "content": [content_block],
    }
    return json.dumps(result)


def build_cli_response(operation: str) -> str:
    """Build the CLI response — just the raw stdout text."""
    op = OPERATIONS[operation]
    return _load_sample(op["sample_file"])


def build_skill_schema() -> str:
    """Return the SKILL.md content — loaded into context once per session.

    This is the skill's equivalent of MCP tool definitions: a one-time
    context cost that gives the LLM knowledge of available commands.
    """
    return SKILL_PATH.read_text()


def build_skill_request(operation: str) -> str:
    """Build the Bash tool_use content block for a skill-assisted CLI command.

    Identical to build_cli_request — the skill changes what the LLM knows,
    not how it invokes commands.
    """
    return build_cli_request(operation)


def build_skill_response(operation: str) -> str:
    """Build the skill response — identical to CLI (raw stdout text).

    The skill doesn't change response format, only LLM decision-making.
    """
    return build_cli_response(operation)
