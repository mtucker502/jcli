#!/usr/bin/env bash
# Phase 2: Real-world token usage comparison using Claude Code.
#
# Runs identical tasks via three approaches:
#   1. MCP (jmcp) — Claude uses MCP tools for Junos device management
#   2. CLI (jcli, no skill) — Claude uses jcli commands via Bash
#   3. Skill (jcli + SKILL.md) — Claude uses jcli via Bash with skill context
#
# Each scenario runs N times per approach. Results are averaged to
# account for natural variance in model behavior (output length,
# turn count, tool selection).
#
# Token usage is measured by isolating each run's CLAUDE_CONFIG_DIR
# to a local directory, then parsing the raw JSONL session files
# to extract per-message token counts.
#
# Skill isolation: Each run uses an isolated CLAUDE_CONFIG_DIR. CLI
# runs have no skill installed. Skill runs have SKILL.md copied into
# the isolated config dir. This prevents cross-contamination.
#
# Prerequisites:
#   - claude CLI installed and configured
#   - jmcp.py accessible (adjust JMCP_PATH below)
#   - jcli installed (pip install -e .)
#   - devices.json in working directory
#   - Python 3 available
#
# Usage: bash benchmarks/real_world_test.sh

set -euo pipefail

# Allow running from within a Claude Code session
unset CLAUDECODE 2>/dev/null || true

# --- Configuration ---
JMCP_PATH="${JMCP_PATH:-/Users/matucker/git/junos-mcp-server/jmcp.py}"
JMCP_PYTHON="${JMCP_PYTHON:-/Users/matucker/git/junos-mcp-server/.venv/bin/python}"
MODEL="${BENCHMARK_MODEL:-opus}"
RUNS="${BENCHMARK_RUNS:-5}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SKILL_SRC="$REPO_DIR/skills/SKILL.md"
TIMESTAMP=$(date +%Y%m%dT%H%M%S)
RESULTS_DIR="$SCRIPT_DIR/results/${TIMESTAMP}"

mkdir -p "$RESULTS_DIR"
RESULTS_DIR_ABS="$(cd "$RESULTS_DIR" && pwd)"

# Save run metadata
cat > "$RESULTS_DIR/meta.json" <<EOF
{
  "timestamp": "$TIMESTAMP",
  "model": "$MODEL",
  "runs_per_scenario": $RUNS
}
EOF

# --- Helper functions ---

# Resolve the real config dir so we can copy credentials into isolated dirs
REAL_CONFIG_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"

seed_config_dir() {
    local config_dir="$1"
    mkdir -p "$config_dir"
    # Copy credentials so the isolated instance can authenticate
    if [[ -f "$REAL_CONFIG_DIR/.credentials.json" ]]; then
        cp "$REAL_CONFIG_DIR/.credentials.json" "$config_dir/.credentials.json"
    fi
}

seed_config_dir_with_skill() {
    local config_dir="$1"
    seed_config_dir "$config_dir"
    # Install the jcli skill into the isolated config dir
    local skill_dest="$config_dir/skills/jcli"
    mkdir -p "$skill_dest"
    cp "$SKILL_SRC" "$skill_dest/SKILL.md"
}

run_mcp() {
    local name="$1"
    local run="$2"
    local prompt="$3"
    local config_dir="$RESULTS_DIR_ABS/${name}_mcp_run${run}"
    seed_config_dir "$config_dir"

    echo "  [MCP]   $name run $run/$RUNS"
    CLAUDE_CONFIG_DIR="$config_dir" claude -p "$prompt" \
        --mcp-config "{\"mcpServers\":{\"jmcp\":{\"command\":\"$JMCP_PYTHON\",\"args\":[\"$JMCP_PATH\"]}}}" \
        --dangerously-skip-permissions \
        --model "$MODEL" \
        > "$config_dir/output.txt" 2>&1 || true
}

run_cli() {
    local name="$1"
    local run="$2"
    local prompt="$3"
    local config_dir="$RESULTS_DIR_ABS/${name}_cli_run${run}"
    seed_config_dir "$config_dir"

    echo "  [CLI]   $name run $run/$RUNS"
    CLAUDE_CONFIG_DIR="$config_dir" claude -p "$prompt" \
        --dangerously-skip-permissions \
        --model "$MODEL" \
        > "$config_dir/output.txt" 2>&1 || true
}

run_skill() {
    local name="$1"
    local run="$2"
    local prompt="$3"
    local config_dir="$RESULTS_DIR_ABS/${name}_skill_run${run}"
    seed_config_dir_with_skill "$config_dir"

    echo "  [Skill] $name run $run/$RUNS"
    CLAUDE_CONFIG_DIR="$config_dir" claude -p "$prompt" \
        --dangerously-skip-permissions \
        --model "$MODEL" \
        > "$config_dir/output.txt" 2>&1 || true
}

# --- Scenarios ---

echo "============================================="
echo "  Token Efficiency: Real-World Comparison"
echo "  Model: $MODEL"
echo "  Runs per scenario: $RUNS"
echo "  Results: $RESULTS_DIR/"
echo "  Approaches: MCP, CLI (no skill), Skill"
echo "============================================="
echo ""

# Verify skill file exists
if [[ ! -f "$SKILL_SRC" ]]; then
    echo "ERROR: Skill file not found at $SKILL_SRC"
    exit 1
fi

for i in $(seq 1 "$RUNS"); do
    echo "=== Run $i/$RUNS ==="

    echo "--- Scenario 1: List routers ---"
    run_mcp "list_routers" "$i" "List the available Junos routers"
    run_cli "list_routers" "$i" "List the available Junos routers"
    run_skill "list_routers" "$i" "List the available Junos routers"

    echo "--- Scenario 2: Multi-operation (3 tasks) ---"
    run_mcp "multi_3op" "$i" \
        "Do these three things: 1) List all routers 2) Get facts for vsrx1 3) Run 'show version' on vsrx1"
    run_cli "multi_3op" "$i" \
        "Do these three things: 1) List all routers 2) Get facts for vsrx1 3) Run 'show version' on vsrx1"
    run_skill "multi_3op" "$i" \
        "Do these three things: 1) List all routers 2) Get facts for vsrx1 3) Run 'show version' on vsrx1"

    echo "--- Scenario 3: Show system services config ---"
    run_mcp "show_services" "$i" \
        "Show me the system services configuration on vsrx1"
    run_cli "show_services" "$i" \
        "Show me the system services configuration on vsrx1"
    run_skill "show_services" "$i" \
        "Show me the system services configuration on vsrx1"

    echo "--- Scenario 4: Show interface drop counters ---"
    run_mcp "show_interfaces" "$i" \
        "Run 'show interfaces' on vsrx1 and tell me which interfaces have drop counters"
    run_cli "show_interfaces" "$i" \
        "Run 'show interfaces' on vsrx1 and tell me which interfaces have drop counters"
    run_skill "show_interfaces" "$i" \
        "Run 'show interfaces' on vsrx1 and tell me which interfaces have drop counters"

    echo "--- Scenario 5: Full workflow (4 tasks) ---"
    run_mcp "full_workflow" "$i" \
        "Complete workflow: 1) List routers 2) Get facts for vsrx1 3) Run 'show bgp summary' on vsrx1 4) Show the full config of vsrx1"
    run_cli "full_workflow" "$i" \
        "Complete workflow: 1) List routers 2) Get facts for vsrx1 3) Run 'show bgp summary' on vsrx1 4) Show the full config of vsrx1"
    run_skill "full_workflow" "$i" \
        "Complete workflow: 1) List routers 2) Get facts for vsrx1 3) Run 'show bgp summary' on vsrx1 4) Show the full config of vsrx1"

    echo "--- Scenario 6: BGP peer filtering ---"
    run_mcp "bgp_peers" "$i" \
        "Show BGP peers on vsrx1 and identify any not in Established state"
    run_cli "bgp_peers" "$i" \
        "Show BGP peers on vsrx1 and identify any not in Established state"
    run_skill "bgp_peers" "$i" \
        "Show BGP peers on vsrx1 and identify any not in Established state"

    echo "--- Scenario 8: Multi-command ---"
    run_mcp "multi_cmd" "$i" \
        "Run 'show version', 'show bgp summary', and 'show interfaces terse' on vsrx1"
    run_cli "multi_cmd" "$i" \
        "Run 'show version', 'show bgp summary', and 'show interfaces terse' on vsrx1"
    run_skill "multi_cmd" "$i" \
        "Run 'show version', 'show bgp summary', and 'show interfaces terse' on vsrx1"

    echo "--- Scenario 9: Targeted config ---"
    run_mcp "config_section" "$i" \
        "Show me the system services configuration on vsrx1 in set format"
    run_cli "config_section" "$i" \
        "Show me the system services configuration on vsrx1 in set format"
    run_skill "config_section" "$i" \
        "Show me the system services configuration on vsrx1 in set format"

    echo "--- Scenario 7: Multi-section config audit ---"
    run_mcp "config_audit" "$i" \
        "Show just the firewall filter rules and SNMP community configuration on vsrx1"
    run_cli "config_audit" "$i" \
        "Show just the firewall filter rules and SNMP community configuration on vsrx1"
    run_skill "config_audit" "$i" \
        "Show just the firewall filter rules and SNMP community configuration on vsrx1"

    echo ""
done

# --- Parse JSONL and aggregate results ---
echo "============================================="
echo "  Parsing JSONL session data..."
echo "============================================="

python3 "$SCRIPT_DIR/parse_results.py" "$RESULTS_DIR_ABS" --runs "$RUNS"

# --- Generate markdown results ---
BENCHMARK_RESULTS="$REPO_DIR/docs/benchmark_results.md"
echo ""
echo "============================================="
echo "  Generating markdown results..."
echo "============================================="

# Preserve Phase 1 content from existing results file
PHASE1_END_MARKER="## Results (Phase 2: Real-World Validation)"
if [[ -f "$BENCHMARK_RESULTS" ]]; then
    # Extract everything before Phase 2
    PHASE1_CONTENT=$(sed -n "1,/^${PHASE1_END_MARKER}/{ /^${PHASE1_END_MARKER}/!p; }" "$BENCHMARK_RESULTS")
else
    PHASE1_CONTENT="# Token Efficiency Benchmark Results

Results from the [benchmark methodology](benchmark.md). Three approaches compared: jmcp (MCP), jcli (CLI, no skill), and jcli + Skill (CLI with SKILL.md).

"
fi

# Write Phase 1 + new Phase 2
{
    echo "$PHASE1_CONTENT"
    python3 "$SCRIPT_DIR/parse_results.py" "$RESULTS_DIR_ABS" --runs "$RUNS" --markdown 2>/dev/null | grep -v "^Results written to:"
} > "$BENCHMARK_RESULTS"

echo "Markdown results written to: $BENCHMARK_RESULTS"

echo ""
echo "Raw JSONL data preserved in: $RESULTS_DIR/"
echo "Point ccusage at any run dir via CLAUDE_CONFIG_DIR for cross-validation."
echo "Done."
