# Token Efficiency Benchmark: jmcp vs jcli vs jcli + Skill

jcli was built to replace jmcp (MCP server) for Junos device management, with the explicit goal of reducing token consumption when driven by an LLM. The jcli skill (SKILL.md) gives the LLM knowledge of available commands without requiring MCP's structured tool interface. This benchmark quantifies where savings come from and how the three approaches compare.

## Background

When an LLM uses MCP tools, its context window accumulates three types of overhead:

1. **Schema overhead** — MCP tool definitions (names, descriptions, JSON Schema for parameters) are injected into the context once per session.
2. **Request overhead** — Each tool call is a `tool_use` content block with structured JSON input.
3. **Response overhead** — Each result is wrapped in a `tool_result` block containing `TextContent` objects with type metadata and annotations (router names, timing data, format info).

When the same LLM uses jcli via the Bash tool, it sees only a short command string and raw text output. The Bash tool schema is already present in the context — jcli adds nothing.

When the LLM has the jcli skill installed, it gains a command reference (SKILL.md) in its context — a one-time cost similar to MCP's schema overhead, but containing human-readable documentation rather than JSON Schema. Per-call request and response overhead is identical to CLI.

### Three approaches compared

| Aspect | MCP (jmcp) | CLI (jcli) | Skill (jcli + SKILL.md) |
|--------|-----------|------------|-------------------------|
| Schema overhead | 7 JSON Schema tool definitions | None (Bash tool already exists) | SKILL.md command reference |
| Request format | `tool_use` block with JSON args | `tool_use` Bash block with command string | Same as CLI |
| Response format | `tool_result` with `TextContent`, `type`, `annotations` | Raw stdout text | Same as CLI |
| LLM guidance | Structured tool schemas constrain behavior | None — LLM must know or discover commands | SKILL.md provides command knowledge |

## Methodology

### Phase 1: Static token counting

The benchmark constructs the exact payloads an LLM would see for each approach and counts tokens using tiktoken's `cl100k_base` encoding. This is an approximation of Claude's tokenizer — exact counts may differ slightly, but the directional comparison is valid.

**What gets measured:**

| Component | MCP (jmcp) | CLI (jcli) | Skill (jcli + SKILL.md) |
|-----------|-----------|------------|-------------------------|
| Schema | 7 tool definitions with JSON Schema | Nothing (Bash tool already exists) | SKILL.md content |
| Request | `tool_use` block with JSON args | `tool_use` Bash block with command string | Same as CLI |
| Response | `tool_result` with `TextContent`, `type`, `annotations` | Raw stdout text | Same as CLI |

**MCP tool schemas** are taken directly from jmcp.py (the `list_tools` handler). All 7 tools are serialized as JSON:

- `execute_junos_command`
- `get_junos_config`
- `junos_config_diff`
- `gather_device_facts`
- `get_router_list`
- `load_and_commit_config`
- `add_device`

**MCP response annotations** are faithfully reproduced from each jmcp handler:

| Tool | Annotations |
|------|------------|
| `execute_junos_command` | `router_name`, `command`, `metadata.execution_duration`, `metadata.start_time`, `metadata.end_time` |
| `get_junos_config` | `router_name` |
| `junos_config_diff` | `router_name`, `config_diff_version` |
| `gather_device_facts` | `router_name` |
| `get_router_list` | none |
| `load_and_commit_config` | `router_name`, `config_text`, `config_format`, `commit_comment` |

**Skill schema** is the SKILL.md file content — a markdown document with command reference, examples, and workflow patterns. This is loaded into the LLM's context once per session, analogous to MCP's tool definitions but in human-readable format.

**Sample data** represents realistic Junos device output:

- Router list: 5 devices
- Device facts: ~30-field PyEZ facts dict (hostname, model, serial, version, RE status, etc.)
- BGP summary: 20-line peer table with 4 peers across 2 groups
- Configuration: 120-line `set`-format config covering interfaces, BGP, OSPF, firewall filters, security zones, NAT, SNMP
- Config diff: 16-line rollback diff with additions, deletions, and modifications
- Load result: 4-line commit confirmation with ID and timestamp

### Six operations benchmarked (Phase 1)

| # | jmcp tool | jcli command |
|---|-----------|-------------|
| 1 | `get_router_list` | `jcli device list` |
| 2 | `gather_device_facts` | `jcli device facts vsrx1` |
| 3 | `execute_junos_command` | `jcli command run vsrx1 "show bgp summary"` |
| 4 | `get_junos_config` | `jcli config show vsrx1` |
| 5 | `junos_config_diff` | `jcli config diff vsrx1` |
| 6 | `load_and_commit_config` | `jcli config load vsrx1 "set system host-name new"` |

Phase 1 intentionally uses only operations where all three approaches return **identical output**. This isolates the structural overhead (schema, annotations, wrapping) from LLM behavioral differences, keeping the comparison apples-to-apples.

Per-call request and response overhead is identical for CLI and Skill — both use the Bash tool with raw stdout. The only Phase 1 difference between CLI and Skill is the one-time schema overhead (0 vs SKILL.md tokens).

Operations where CLI could filter output — e.g., piping `show interfaces` through `grep` for drop counters, or running `show configuration system services` instead of fetching the full config — are excluded from Phase 1 because they depend on the LLM choosing to compose commands differently. Hard-coding an optimal CLI pipeline while giving MCP no equivalent opportunity would bias the results. These scenarios are tested in Phase 2, where the LLM makes its own decisions for all three approaches.

### Phase 2: Real-world validation

A shell script (`benchmarks/real_world_test.sh`) runs Claude Code (`claude -p`) with equivalent prompts under three configurations — jmcp via MCP, jcli via Bash (no skill), and jcli via Bash with SKILL.md installed — and captures actual token usage. This validates Phase 1 predictions and tests scenarios that Phase 1 cannot: composability, output filtering, and LLM decision-making.

**Sandbox isolation:** Each run executes in a clean temporary directory containing only `devices.json` — no source code, no CLAUDE.md, no `.git` directory. This prevents the model from reading jcli internals to discover commands, which would give CLI and Skill an artificial advantage not present in real deployments. jcli is made available via PATH (the venv's bin directory is prepended), so the model can run `jcli` as a normal command.

This sandbox reflects the realistic deployment scenario: a user has `jcli` installed system-wide and manages routers from an arbitrary working directory, not from inside the jcli source repository.

**Skill isolation:** Each run uses an isolated `CLAUDE_CONFIG_DIR`. CLI runs have no skill installed. Skill runs have SKILL.md copied into the isolated config dir's `skills/jcli/` directory. This prevents cross-contamination between approaches.

**Prompt design:** All three approaches use identical natural-language prompts. MCP discovers actions from tool schemas, Skill from SKILL.md context, and CLI must figure it out from available tools. This keeps the comparison fair — any behavioral differences come from the approach, not the prompt.

**Phase 2 scenarios include the Phase 1 operations plus composability tests:**

| Scenario | Prompt (identical for all 3 approaches) |
|----------|------------------------------------------|
| List routers | "List the available Junos routers" |
| Multi-op (3 tasks) | "Do these three things: 1) List all routers 2) Get facts for vsrx1 3) Run 'show version' on vsrx1" |
| Show system services | "Show me the system services configuration on vsrx1" |
| Interface drop counters | "Run 'show interfaces' on vsrx1 and tell me which interfaces have drop counters" |
| Full workflow (4 tasks) | "Complete workflow: 1) List routers 2) Get facts for vsrx1 3) Run 'show bgp summary' on vsrx1 4) Show the full config of vsrx1" |
| BGP peer filtering | "Show BGP peers on vsrx1 and identify any not in Established state" |
| Config audit (2 sections) | "Show just the firewall filter rules and SNMP community configuration on vsrx1" |
| Multi-command (3 ops) | "Run 'show version', 'show bgp summary', and 'show interfaces terse' on vsrx1" |
| Targeted config | "Show me the system services configuration on vsrx1 in set format" |

These prompts describe intent without prescribing commands (for MCP and Skill), letting the LLM decide how to get the data. The skill hypothesis is that SKILL.md provides enough guidance for the LLM to use jcli commands correctly with natural-language prompts — combining CLI's per-token efficiency with MCP's behavioral consistency.

## Results

See [benchmark_results.md](benchmark_results.md) for Phase 1, Phase 2, and summary results.

## Running the benchmarks

### Phase 1 (static, no API key needed)

```bash
pip install -e ".[dev]"
pytest benchmarks/test_token_efficiency.py -v
python benchmarks/report.py
```

### Phase 2 (requires Claude Code + live devices)

**Prerequisites:**
- `claude` CLI installed and authenticated
- jmcp.py accessible (default: `/Users/matucker/git/junos-mcp-server/jmcp.py`)
- A Python environment with jmcp's dependencies (junos-eznc, mcp[cli], etc.)
- jcli installed (`pip install -e .`)
- `devices.json` in the working directory with reachable devices

**Setup:** The jmcp venv must match the current platform. If running on a different platform than where jmcp was originally set up (e.g., Linux VM vs macOS host), create a platform-compatible venv:

```bash
cd /path/to/junos-mcp-server
python3 -m venv .venv-$(uname -s | tr A-Z a-z)
.venv-$(uname -s | tr A-Z a-z)/bin/pip install junos-eznc "mcp[cli]" jxmlease lxml ncclient paramiko psutil pydantic pydantic-settings pyserial uvicorn starlette
```

Then point `JMCP_PYTHON` at the new venv's python binary.

**Run:**

```bash
JMCP_PYTHON=/path/to/junos-mcp-server/.venv-linux/bin/python bash benchmarks/real_world_test.sh
```

**Environment variables:**

- `JMCP_PATH` — path to jmcp.py (default: `/Users/matucker/git/junos-mcp-server/jmcp.py`)
- `JMCP_PYTHON` — python binary with jmcp dependencies (default: jmcp's `.venv/bin/python`)
- `BENCHMARK_MODEL` — model to use (default: `opus`)
- `BENCHMARK_RUNS` — number of runs per scenario (default: `5`)

## Caveats

- Phase 1 token counts use OpenAI's `cl100k_base` encoding as an approximation. Claude uses a different tokenizer, so absolute counts will differ. The relative comparison remains valid.
- Phase 1 measures only tool interaction overhead. It does not account for system prompts, model reasoning tokens, or retry behavior.
- Phase 2 results include natural variance from model behavior — output token counts and turn counts differ between runs for identical prompts. Multiple runs per scenario reduce noise, but some variance remains.
- The skill's SKILL.md context cost is paid once per session. In shorter sessions (1-2 operations), the skill overhead may exceed MCP's schema overhead. In longer sessions, the per-call savings accumulate.
- Real-world savings depend on the ratio of tool overhead to system prompt size. Claude Code's large system prompt (~25k tokens) dilutes the percentage impact of schema savings. In lighter-weight agent frameworks with smaller system prompts, the Phase 1 percentages would be more representative.
- Working directory matters significantly. Early Phase 2 runs inside the jcli source repo showed MCP winning most scenarios, because the model could read source code and CLAUDE.md to discover commands. Sandbox runs (clean directory with only `devices.json`) show the opposite result — Skill wins decisively. The sandbox reflects the realistic deployment scenario.
