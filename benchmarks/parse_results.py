#!/usr/bin/env python3
"""Parse Claude Code JSONL session files from isolated benchmark runs.

Each benchmark run stores Claude Code session data in an isolated
CLAUDE_CONFIG_DIR. This script finds the JSONL files within each run
directory, extracts token usage from assistant messages, and produces
an aggregated results.json summary.

Usage:
    python benchmarks/parse_results.py <results_dir> [--runs N] [--markdown]
"""

import json
import sys
from pathlib import Path

SCENARIOS = [
    "list_routers",
    "multi_3op",
    "show_services",
    "show_interfaces",
    "full_workflow",
    "bgp_peers",
    "config_audit",
]

APPROACHES = ["mcp", "cli", "skill"]

SCENARIO_NAMES = {
    "list_routers": "List routers (1 op)",
    "multi_3op": "Multi-op (3 ops)",
    "show_services": "Show services (1 op)",
    "show_interfaces": "Show interfaces (1 op)",
    "full_workflow": "Full workflow (4 ops)",
    "bgp_peers": "BGP peer filtering (1 op)",
    "config_audit": "Config audit (2 ops)",
}

APPROACH_NAMES = {
    "mcp": "MCP",
    "cli": "CLI",
    "skill": "Skill",
}


def parse_jsonl(config_dir: Path) -> dict:
    """Extract aggregated token usage from JSONL files in a CLAUDE_CONFIG_DIR.

    Walks projects/**/*.jsonl, reads each line as JSON, and sums token usage
    from assistant messages. Skips entries where type is "summary" or message
    is missing.
    """
    totals = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
    }
    num_turns = 0

    projects_dir = config_dir / "projects"
    if not projects_dir.exists():
        return {**totals, "num_turns": 0, "context_tokens": 0}

    for jsonl_path in sorted(projects_dir.rglob("*.jsonl")):
        with open(jsonl_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Skip summary entries and entries without a message
                if entry.get("type") == "summary":
                    continue
                if "message" not in entry:
                    continue

                message = entry["message"]
                if not isinstance(message, dict):
                    continue

                # Only count assistant messages (they carry usage data)
                if message.get("role") != "assistant":
                    continue

                usage = message.get("usage")
                if not usage:
                    continue

                totals["input_tokens"] += usage.get("input_tokens", 0)
                totals["output_tokens"] += usage.get("output_tokens", 0)
                totals["cache_creation_input_tokens"] += usage.get(
                    "cache_creation_input_tokens", 0
                )
                totals["cache_read_input_tokens"] += usage.get(
                    "cache_read_input_tokens", 0
                )
                num_turns += 1

    totals["num_turns"] = num_turns
    totals["context_tokens"] = (
        totals["input_tokens"]
        + totals["cache_creation_input_tokens"]
        + totals["cache_read_input_tokens"]
    )
    return totals


def aggregate(results_dir: Path, runs: int) -> dict:
    """Parse all runs in a results directory and build aggregated data."""
    data = {"scenarios": {}}

    for scenario in SCENARIOS:
        data["scenarios"][scenario] = {}
        for approach in APPROACHES:
            run_results = []
            for r in range(1, runs + 1):
                config_dir = results_dir / f"{scenario}_{approach}_run{r}"
                if config_dir.exists():
                    usage = parse_jsonl(config_dir)
                    run_results.append(usage)

            if run_results:
                avg = {}
                for key in run_results[0]:
                    values = [r[key] for r in run_results]
                    avg[key] = sum(values) // len(values)
                data["scenarios"][scenario][approach] = {
                    "runs": run_results,
                    "average": avg,
                }
            else:
                data["scenarios"][scenario][approach] = {
                    "runs": [],
                    "average": {
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "cache_creation_input_tokens": 0,
                        "cache_read_input_tokens": 0,
                        "num_turns": 0,
                        "context_tokens": 0,
                    },
                }

    return data


def print_table(data: dict):
    """Print comparison table from aggregated data."""
    print()
    print(
        f"{'Scenario':<18} {'App':>5} {'Turns':>5} "
        f"{'Context':>9} {'Output':>8} {'Input':>8} "
        f"{'CacheCreate':>12} {'CacheRead':>10}"
    )
    print(
        f"{'-' * 18} {'-----':>5} {'-----':>5} "
        f"{'---------':>9} {'--------':>8} {'--------':>8} "
        f"{'------------':>12} {'----------':>10}"
    )

    for scenario in SCENARIOS:
        sdata = data["scenarios"].get(scenario, {})
        for approach in APPROACHES:
            adata = sdata.get(approach, {})
            avg = adata.get("average", {})
            if not avg or avg.get("num_turns", 0) == 0:
                continue
            label = scenario if approach == APPROACHES[0] else ""
            print(
                f"{label:<18} {APPROACH_NAMES[approach]:>5} "
                f"{avg.get('num_turns', 0):>5} "
                f"{avg.get('context_tokens', 0):>9} "
                f"{avg.get('output_tokens', 0):>8} "
                f"{avg.get('input_tokens', 0):>8} "
                f"{avg.get('cache_creation_input_tokens', 0):>12} "
                f"{avg.get('cache_read_input_tokens', 0):>10}"
            )
        print()


def print_markdown(data: dict):
    """Print Phase 2 results as markdown tables for docs/benchmark_results.md."""
    model = data.get("model", "unknown")
    runs = data.get("runs_per_scenario", "?")

    print("## Results (Phase 2: Real-World Validation)\n")
    print(
        f"Phase 2 ran Claude Code (`claude -p`) with {model} against a live "
        f"vsrx1 device, comparing three approaches: jmcp via MCP, jcli via Bash "
        f"(no skill), and jcli via Bash with the SKILL.md skill installed. "
        f"Each scenario was run {runs} times per approach "
        f"to account for natural variance in model behavior. Token usage was "
        f"extracted from raw JSONL session data via `CLAUDE_CONFIG_DIR` "
        f"isolation.\n"
    )

    # Determine which approaches have data
    active_approaches = []
    for approach in APPROACHES:
        has_data = any(
            data["scenarios"].get(s, {}).get(approach, {})
            .get("average", {}).get("num_turns", 0) > 0
            for s in SCENARIOS
        )
        if has_data:
            active_approaches.append(approach)

    # --- Averaged results table ---
    print("### Averaged results\n")
    print(
        "The table shows total context tokens "
        "(input + cache creation + cache read), output tokens, "
        "and average API turns.\n"
    )
    print("| Scenario | Approach | Avg Turns | Avg Context | Avg Output |")
    print("|----------|----------|-----------|-------------|------------|")

    for scenario in SCENARIOS:
        sdata = data["scenarios"].get(scenario, {})
        name = SCENARIO_NAMES.get(scenario, scenario)
        for approach in active_approaches:
            avg = sdata.get(approach, {}).get("average", {})
            if not avg or avg.get("num_turns", 0) == 0:
                continue
            label = name if approach == active_approaches[0] else ""
            turns = avg.get("num_turns", 0)
            context = avg.get("context_tokens", 0)
            output = avg.get("output_tokens", 0)
            print(
                f"| {label} | {APPROACH_NAMES[approach]} | "
                f"{turns} | {context:,} | {output:,} |"
            )

    # --- Context comparison table ---
    print("\n### Context comparison\n")
    header = "| Scenario | MCP Context |"
    separator = "|----------|-------------|"
    for approach in active_approaches:
        if approach == "mcp":
            continue
        header += f" {APPROACH_NAMES[approach]} Context | {APPROACH_NAMES[approach]} vs MCP |"
        separator += "-------------|------------|"
    print(header)
    print(separator)

    for scenario in SCENARIOS:
        sdata = data["scenarios"].get(scenario, {})
        name = SCENARIO_NAMES.get(scenario, scenario)
        mcp_ctx = sdata.get("mcp", {}).get("average", {}).get("context_tokens", 0)
        row = f"| {name} | {mcp_ctx:,} |"
        for approach in active_approaches:
            if approach == "mcp":
                continue
            ctx = sdata.get(approach, {}).get("average", {}).get("context_tokens", 0)
            if mcp_ctx > 0 and ctx > 0:
                pct = (ctx / mcp_ctx - 1) * 100
                sign = "+" if pct >= 0 else ""
                delta = f"**{sign}{pct:.1f}%**"
            else:
                delta = "N/A"
            row += f" {ctx:,} | {delta} |"
        print(row)

    # --- Per-run variance table ---
    print("\n### Per-run variance\n")
    print(
        "The averages mask significant run-to-run variance. "
        "The table below shows the range of turns and context "
        "tokens across all runs per scenario.\n"
    )
    print("| Scenario | Approach | Turn Range | Context Range |")
    print("|----------|----------|------------|---------------|")

    for scenario in SCENARIOS:
        sdata = data["scenarios"].get(scenario, {})
        name = SCENARIO_NAMES.get(scenario, scenario)
        for approach in active_approaches:
            run_data = sdata.get(approach, {}).get("runs", [])
            if not run_data:
                continue
            turns = [r["num_turns"] for r in run_data]
            contexts = [r["context_tokens"] for r in run_data]
            label = name if approach == active_approaches[0] else ""
            print(
                f"| {label} | {APPROACH_NAMES[approach]} | "
                f"{min(turns)}-{max(turns)} | "
                f"{min(contexts):,} - {max(contexts):,} |"
            )


def main():
    if len(sys.argv) < 2:
        print(
            f"Usage: {sys.argv[0]} <results_dir> [--runs N] [--markdown]",
            file=sys.stderr,
        )
        sys.exit(1)

    results_dir = Path(sys.argv[1])
    runs = 5
    markdown = "--markdown" in sys.argv

    if "--runs" in sys.argv:
        idx = sys.argv.index("--runs")
        runs = int(sys.argv[idx + 1])

    data = aggregate(results_dir, runs)

    # Merge metadata from meta.json if present
    meta_path = results_dir / "meta.json"
    if meta_path.exists():
        with open(meta_path) as f:
            meta = json.load(f)
        data.update(meta)

    # Write results.json
    results_path = results_dir / "results.json"
    with open(results_path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

    print(f"Results written to: {results_path}")

    if markdown:
        print_markdown(data)
    else:
        print_table(data)


if __name__ == "__main__":
    main()
