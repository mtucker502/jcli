#!/usr/bin/env bash
# Targeted benchmark: re-tests scenarios where CLI and Skill underperformed MCP.
# Uses the same sandbox isolation as real_world_test.sh but runs only 5 scenarios.
#
# Scenarios targeted (from baseline results):
#   1. list_routers     — Skill +19%, CLI +33% vs MCP
#   2. show_interfaces  — Skill +66%, CLI +69% vs MCP
#   3. bgp_peers        — Skill +102%, CLI +53% vs MCP
#   4. config_section   — Skill +96%, CLI +94% vs MCP
#   5. full_workflow    — Skill -18% (already winning, control test)

set -euo pipefail

unset CLAUDECODE 2>/dev/null || true

# --- Configuration ---
JMCP_PATH="${JMCP_PATH:-/Users/matucker/git/junos-mcp-server/jmcp.py}"
JMCP_PYTHON="${JMCP_PYTHON:-/Users/matucker/git/junos-mcp-server/.venv/bin/python}"
MODEL="${BENCHMARK_MODEL:-opus}"
RUNS="${BENCHMARK_RUNS:-5}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SKILL_SRC="$REPO_DIR/skills/SKILL.md"
JCLI_VENV="$REPO_DIR/.venv"
TIMESTAMP=$(date +%Y%m%dT%H%M%S)
RESULTS_DIR="$SCRIPT_DIR/results/targeted_${TIMESTAMP}"

mkdir -p "$RESULTS_DIR"
RESULTS_DIR_ABS="$(cd "$RESULTS_DIR" && pwd)"

# --- Create clean sandbox ---
SANDBOX_DIR=$(mktemp -d)
cp "$REPO_DIR/devices.json" "$SANDBOX_DIR/devices.json"

cleanup_sandbox() {
    rm -rf "$SANDBOX_DIR"
}
trap cleanup_sandbox EXIT

if [[ ! -x "$JCLI_VENV/bin/jcli" ]]; then
    echo "ERROR: jcli not found at $JCLI_VENV/bin/jcli"
    exit 1
fi

cat > "$RESULTS_DIR/meta.json" <<EOF
{
  "timestamp": "$TIMESTAMP",
  "model": "$MODEL",
  "runs_per_scenario": $RUNS,
  "type": "targeted",
  "sandbox": true
}
EOF

# --- Helper functions ---
REAL_CONFIG_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"

seed_config_dir() {
    local config_dir="$1"
    mkdir -p "$config_dir"
    if [[ -f "$REAL_CONFIG_DIR/.credentials.json" ]]; then
        cp "$REAL_CONFIG_DIR/.credentials.json" "$config_dir/.credentials.json"
    fi
}

seed_config_dir_with_skill() {
    local config_dir="$1"
    seed_config_dir "$config_dir"
    local skill_dest="$config_dir/skills/jcli"
    mkdir -p "$skill_dest"
    cp "$SKILL_SRC" "$skill_dest/SKILL.md"
}

run_in_sandbox() {
    local config_dir="$1"
    shift
    (
        cd "$SANDBOX_DIR"
        export PATH="$JCLI_VENV/bin:$PATH"
        export CLAUDE_CONFIG_DIR="$config_dir"
        "$@"
    )
}

run_mcp() {
    local name="$1" run="$2" prompt="$3"
    local config_dir="$RESULTS_DIR_ABS/${name}_mcp_run${run}"
    seed_config_dir "$config_dir"
    echo "  [MCP]   $name run $run/$RUNS"
    run_in_sandbox "$config_dir" \
        claude -p "$prompt" \
        --mcp-config "{\"mcpServers\":{\"jmcp\":{\"command\":\"$JMCP_PYTHON\",\"args\":[\"$JMCP_PATH\"]}}}" \
        --dangerously-skip-permissions --model "$MODEL" \
        > "$config_dir/output.txt" 2>&1 || true
}

run_cli() {
    local name="$1" run="$2" prompt="$3"
    local config_dir="$RESULTS_DIR_ABS/${name}_cli_run${run}"
    seed_config_dir "$config_dir"
    echo "  [CLI]   $name run $run/$RUNS"
    run_in_sandbox "$config_dir" \
        claude -p "$prompt" \
        --dangerously-skip-permissions --model "$MODEL" \
        > "$config_dir/output.txt" 2>&1 || true
}

run_skill() {
    local name="$1" run="$2" prompt="$3"
    local config_dir="$RESULTS_DIR_ABS/${name}_skill_run${run}"
    seed_config_dir_with_skill "$config_dir"
    echo "  [Skill] $name run $run/$RUNS"
    run_in_sandbox "$config_dir" \
        claude -p "$prompt" \
        --dangerously-skip-permissions --model "$MODEL" \
        > "$config_dir/output.txt" 2>&1 || true
}

# --- Run ---
echo "============================================="
echo "  Targeted Benchmark (sandbox isolation)"
echo "  Model: $MODEL | Runs: $RUNS"
echo "  Sandbox: $SANDBOX_DIR"
echo "  Results: $RESULTS_DIR/"
echo "============================================="
echo ""

if [[ ! -f "$SKILL_SRC" ]]; then
    echo "ERROR: Skill file not found at $SKILL_SRC"
    exit 1
fi

for i in $(seq 1 "$RUNS"); do
    echo "=== Run $i/$RUNS ==="

    echo "--- list_routers ---"
    run_mcp "list_routers" "$i" "List the available Junos routers"
    run_cli "list_routers" "$i" "List the available Junos routers"
    run_skill "list_routers" "$i" "List the available Junos routers"

    echo "--- show_interfaces ---"
    run_mcp "show_interfaces" "$i" \
        "Run 'show interfaces' on vsrx1 and tell me which interfaces have drop counters"
    run_cli "show_interfaces" "$i" \
        "Run 'show interfaces' on vsrx1 and tell me which interfaces have drop counters"
    run_skill "show_interfaces" "$i" \
        "Run 'show interfaces' on vsrx1 and tell me which interfaces have drop counters"

    echo "--- bgp_peers ---"
    run_mcp "bgp_peers" "$i" \
        "Show BGP peers on vsrx1 and identify any not in Established state"
    run_cli "bgp_peers" "$i" \
        "Show BGP peers on vsrx1 and identify any not in Established state"
    run_skill "bgp_peers" "$i" \
        "Show BGP peers on vsrx1 and identify any not in Established state"

    echo "--- config_section ---"
    run_mcp "config_section" "$i" \
        "Show me the system services configuration on vsrx1 in set format"
    run_cli "config_section" "$i" \
        "Show me the system services configuration on vsrx1 in set format"
    run_skill "config_section" "$i" \
        "Show me the system services configuration on vsrx1 in set format"

    echo "--- full_workflow (control) ---"
    run_mcp "full_workflow" "$i" \
        "Complete workflow: 1) List routers 2) Get facts for vsrx1 3) Run 'show bgp summary' on vsrx1 4) Show the full config of vsrx1"
    run_cli "full_workflow" "$i" \
        "Complete workflow: 1) List routers 2) Get facts for vsrx1 3) Run 'show bgp summary' on vsrx1 4) Show the full config of vsrx1"
    run_skill "full_workflow" "$i" \
        "Complete workflow: 1) List routers 2) Get facts for vsrx1 3) Run 'show bgp summary' on vsrx1 4) Show the full config of vsrx1"

    echo ""
done

echo "============================================="
echo "  Parsing results..."
echo "============================================="

python3 "$SCRIPT_DIR/parse_results.py" "$RESULTS_DIR_ABS" --runs "$RUNS"
echo ""
python3 "$SCRIPT_DIR/parse_results.py" "$RESULTS_DIR_ABS" --runs "$RUNS" --markdown

echo ""
echo "Done. Results: $RESULTS_DIR/"
