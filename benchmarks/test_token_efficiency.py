"""Phase 1: Static token efficiency benchmark — MCP vs CLI vs Skill.

Measures token overhead in three categories:
1. Schema overhead (one-time cost of MCP tool definitions / SKILL.md)
2. Per-call overhead (request + response for each operation)
3. Session cost (end-to-end multi-operation workflow)

Three approaches compared:
- MCP (jmcp): 7 tool definitions + structured tool_use/tool_result
- CLI (jcli): Bash tool only, no schema overhead
- Skill (jcli + SKILL.md): SKILL.md loaded into context + Bash tool
"""

import pytest

from benchmarks.payloads import (
    OPERATIONS,
    build_cli_request,
    build_cli_response,
    build_mcp_request,
    build_mcp_response,
    build_mcp_schemas,
    build_skill_request,
    build_skill_response,
    build_skill_schema,
)
from benchmarks.token_counter import count_tokens

# Store results for report generation
_results = {}


def _store(category, key, mcp_tokens, cli_tokens, skill_tokens=None):
    """Store benchmark result for later report generation."""
    entry = {
        "mcp": mcp_tokens,
        "cli": cli_tokens,
        "savings": mcp_tokens - cli_tokens,
        "pct": round((1 - cli_tokens / mcp_tokens) * 100, 1) if mcp_tokens > 0 else 0,
    }
    if skill_tokens is not None:
        entry["skill"] = skill_tokens
    _results.setdefault(category, {})[key] = entry


class TestSchemaOverhead:
    """One-time cost: MCP tool definitions vs SKILL.md vs zero for CLI."""

    def test_mcp_schema_cost(self):
        schema_text = build_mcp_schemas()
        mcp_tokens = count_tokens(schema_text)
        cli_tokens = 0  # CLI adds no schema overhead (Bash tool already exists)
        skill_text = build_skill_schema()
        skill_tokens = count_tokens(skill_text)

        _store("schema", "tool_definitions", mcp_tokens, cli_tokens, skill_tokens)

        assert mcp_tokens > 0, "MCP schemas should have nonzero token cost"
        assert mcp_tokens > 500, f"Expected substantial schema overhead, got {mcp_tokens}"
        assert skill_tokens > 0, "Skill schema should have nonzero token cost"
        print(f"\nSchema overhead: MCP={mcp_tokens}, CLI=0, Skill={skill_tokens}")


class TestPerCallOverhead:
    """Per-operation comparison of request + response tokens."""

    @pytest.mark.parametrize("operation", list(OPERATIONS.keys()))
    def test_request_tokens(self, operation):
        """Record per-request token counts.

        Note: For simple operations with few parameters, MCP requests can be
        comparable or even smaller than CLI (e.g. {"input": {}} vs
        {"command": "jcli device list"}). Skill requests are identical to CLI.
        """
        mcp_req = build_mcp_request(operation)
        cli_req = build_cli_request(operation)
        skill_req = build_skill_request(operation)

        mcp_tokens = count_tokens(mcp_req)
        cli_tokens = count_tokens(cli_req)
        skill_tokens = count_tokens(skill_req)

        _store("request", operation, mcp_tokens, cli_tokens, skill_tokens)

        assert cli_tokens == skill_tokens, "Skill requests should be identical to CLI"
        print(f"\n{operation} request: MCP={mcp_tokens}, CLI={cli_tokens}, "
              f"Skill={skill_tokens}")

    @pytest.mark.parametrize("operation", list(OPERATIONS.keys()))
    def test_response_tokens(self, operation):
        mcp_resp = build_mcp_response(operation)
        cli_resp = build_cli_response(operation)
        skill_resp = build_skill_response(operation)

        mcp_tokens = count_tokens(mcp_resp)
        cli_tokens = count_tokens(cli_resp)
        skill_tokens = count_tokens(skill_resp)

        _store("response", operation, mcp_tokens, cli_tokens, skill_tokens)

        assert cli_tokens < mcp_tokens, (
            f"CLI response should use fewer tokens than MCP for {operation}: "
            f"CLI={cli_tokens}, MCP={mcp_tokens}"
        )
        assert cli_tokens == skill_tokens, "Skill responses should be identical to CLI"
        print(f"\n{operation} response: MCP={mcp_tokens}, CLI={cli_tokens}, "
              f"Skill={skill_tokens}")

    @pytest.mark.parametrize("operation", list(OPERATIONS.keys()))
    def test_roundtrip_tokens(self, operation):
        """Combined request + response overhead per operation."""
        mcp_total = count_tokens(build_mcp_request(operation)) + count_tokens(
            build_mcp_response(operation)
        )
        cli_total = count_tokens(build_cli_request(operation)) + count_tokens(
            build_cli_response(operation)
        )
        skill_total = count_tokens(build_skill_request(operation)) + count_tokens(
            build_skill_response(operation)
        )

        _store("roundtrip", operation, mcp_total, cli_total, skill_total)

        assert cli_total < mcp_total, (
            f"CLI roundtrip should use fewer tokens than MCP for {operation}: "
            f"CLI={cli_total}, MCP={mcp_total}"
        )
        assert cli_total == skill_total, "Skill roundtrip should equal CLI"


class TestSessionCost:
    """End-to-end: simulate multi-operation sessions across all three approaches."""

    def test_four_operation_session(self):
        """Workflow: list routers -> get facts -> run command -> show config."""
        session_ops = ["list_routers", "device_facts", "execute_command", "show_config"]

        # MCP session includes schema overhead (one-time) + per-call costs
        mcp_schema = count_tokens(build_mcp_schemas())
        mcp_calls = sum(
            count_tokens(build_mcp_request(op)) + count_tokens(build_mcp_response(op))
            for op in session_ops
        )
        mcp_total = mcp_schema + mcp_calls

        # CLI session: just the per-call costs (no schema overhead)
        cli_total = sum(
            count_tokens(build_cli_request(op)) + count_tokens(build_cli_response(op))
            for op in session_ops
        )

        # Skill session: SKILL.md overhead (one-time) + per-call costs (same as CLI)
        skill_schema = count_tokens(build_skill_schema())
        skill_total = skill_schema + cli_total

        _store("session", "4-op workflow", mcp_total, cli_total, skill_total)

        savings = mcp_total - cli_total
        pct = round((1 - cli_total / mcp_total) * 100, 1)

        assert cli_total < mcp_total, (
            f"CLI session should use fewer tokens: CLI={cli_total}, MCP={mcp_total}"
        )
        print(f"\n4-op session: MCP={mcp_total}, CLI={cli_total}, "
              f"Skill={skill_total}, savings(cli)={savings} ({pct}%)")

    def test_all_operation_session(self):
        """All operations in a single session."""
        all_ops = list(OPERATIONS.keys())

        mcp_schema = count_tokens(build_mcp_schemas())
        mcp_calls = sum(
            count_tokens(build_mcp_request(op)) + count_tokens(build_mcp_response(op))
            for op in all_ops
        )
        mcp_total = mcp_schema + mcp_calls

        cli_total = sum(
            count_tokens(build_cli_request(op)) + count_tokens(build_cli_response(op))
            for op in all_ops
        )

        skill_schema = count_tokens(build_skill_schema())
        skill_total = skill_schema + cli_total

        _store("session", f"{len(all_ops)}-op workflow", mcp_total, cli_total, skill_total)

        assert cli_total < mcp_total
        print(f"\n{len(all_ops)}-op session: MCP={mcp_total}, CLI={cli_total}, "
              f"Skill={skill_total}")


def get_results():
    """Return collected benchmark results (used by report.py)."""
    return _results
