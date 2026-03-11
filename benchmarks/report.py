#!/usr/bin/env python3
"""Generate a markdown summary table from token efficiency benchmarks.

Run: python -m benchmarks.report
"""

import sys
from pathlib import Path

# Allow running as script or module
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from benchmarks.payloads import (  # noqa: E402
    OPERATIONS,
    build_cli_request,
    build_cli_response,
    build_mcp_request,
    build_mcp_response,
    build_mcp_schemas,
    build_skill_schema,
)
from benchmarks.token_counter import count_tokens  # noqa: E402

# Friendly names for operations
OP_NAMES = {
    "list_routers": "List devices",
    "device_facts": "Device facts",
    "execute_command": "Execute command",
    "show_config": "Show config",
    "config_diff": "Config diff",
    "load_config": "Load config",
}


def generate_report():
    # Schema overhead
    mcp_schema_tokens = count_tokens(build_mcp_schemas())
    skill_schema_tokens = count_tokens(build_skill_schema())

    print("# Token Efficiency Benchmark: jmcp (MCP) vs jcli (CLI) vs jcli + Skill\n")
    print("**Tokenizer:** cl100k_base (approximation of Claude's tokenizer)\n")

    # Schema section
    print("## Schema Overhead (one-time)\n")
    print("| Component | MCP | CLI | Skill | MCP vs CLI | MCP vs Skill |")
    print("|-----------|-----|-----|-------|------------|--------------|")
    print(
        f"| Tool definitions | {mcp_schema_tokens} | 0 | {skill_schema_tokens} | "
        f"{mcp_schema_tokens} tokens | {mcp_schema_tokens - skill_schema_tokens} tokens |"
    )
    print()
    print(
        f"MCP pays {mcp_schema_tokens} tokens for 7 JSON Schema tool definitions. "
        f"CLI pays zero (Bash tool already exists). "
        f"Skill pays {skill_schema_tokens} tokens for SKILL.md context "
        f"(command reference loaded once per session)."
    )
    print()

    # Per-operation table
    print("## Per-Operation Overhead\n")
    print(
        "Per-call request and response tokens are identical for CLI and Skill "
        "(both use Bash tool with raw stdout). The skill only adds one-time "
        "schema overhead.\n"
    )
    print("| Operation | MCP Req | CLI Req | MCP Resp | CLI Resp | "
          "Req Savings | Resp Savings | Total Savings |")
    print("|-----------|---------|---------|----------|----------|"
          "------------|--------------|---------------|")

    total_mcp = 0
    total_cli = 0

    for op_key, op_name in OP_NAMES.items():
        mcp_req = count_tokens(build_mcp_request(op_key))
        cli_req = count_tokens(build_cli_request(op_key))
        mcp_resp = count_tokens(build_mcp_response(op_key))
        cli_resp = count_tokens(build_cli_response(op_key))

        req_save = mcp_req - cli_req
        resp_save = mcp_resp - cli_resp
        total_save = req_save + resp_save

        total_mcp += mcp_req + mcp_resp
        total_cli += cli_req + cli_resp

        print(f"| {op_name:<17s} | {mcp_req:>7d} | {cli_req:>7d} | {mcp_resp:>8d} | "
              f"{cli_resp:>8d} | {req_save:>10d} | {resp_save:>12d} | {total_save:>13d} |")

    print()

    # Session simulations
    print("## Session Simulations\n")

    sessions = {
        "4-op workflow": ["list_routers", "device_facts", "execute_command", "show_config"],
        "6-op workflow": list(OPERATIONS.keys()),
    }

    print("| Session | MCP Total | CLI Total | Skill Total | "
          "CLI Savings | Skill Savings |")
    print("|---------|-----------|-----------|-------------|"
          "------------|---------------|")

    for session_name, ops in sessions.items():
        mcp_session = mcp_schema_tokens + sum(
            count_tokens(build_mcp_request(op)) + count_tokens(build_mcp_response(op))
            for op in ops
        )
        cli_session = sum(
            count_tokens(build_cli_request(op)) + count_tokens(build_cli_response(op))
            for op in ops
        )
        skill_session = skill_schema_tokens + cli_session

        cli_savings = mcp_session - cli_session
        cli_pct = round((1 - cli_session / mcp_session) * 100, 1)
        skill_savings = mcp_session - skill_session
        skill_pct = round((1 - skill_session / mcp_session) * 100, 1)

        print(
            f"| {session_name:<15s} | {mcp_session:>9d} | {cli_session:>9d} | "
            f"{skill_session:>11d} | "
            f"{cli_savings:>5d} ({cli_pct}%) | "
            f"{skill_savings:>5d} ({skill_pct}%) |"
        )

    print()

    # Summary
    per_call_savings = total_mcp - total_cli
    per_call_pct = round((1 - total_cli / total_mcp) * 100, 1)
    print("## Summary\n")
    print(f"- **MCP schema overhead:** {mcp_schema_tokens} tokens (7 JSON Schema tool definitions)")
    print(f"- **Skill schema overhead:** {skill_schema_tokens} tokens (SKILL.md command reference)")
    print("- **CLI schema overhead:** 0 tokens (Bash tool already exists)")
    print(f"- **Per-call savings (all {len(OP_NAMES)} ops):** {per_call_savings} tokens "
          f"({per_call_pct}%) — identical for CLI and Skill")
    print(f"- **Total savings ({len(OP_NAMES)}-op session, CLI):** "
          f"{mcp_schema_tokens + per_call_savings} tokens")
    print(f"- **Total savings ({len(OP_NAMES)}-op session, Skill):** "
          f"{mcp_schema_tokens - skill_schema_tokens + per_call_savings} tokens")
    print()
    print("*Note: Token counts use cl100k_base encoding. Claude's actual tokenizer may differ ")
    print("slightly, but the directional comparison is valid.*")


if __name__ == "__main__":
    generate_report()
