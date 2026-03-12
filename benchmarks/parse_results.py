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
    "multi_cmd",
    "config_section",
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
    "multi_cmd": "Multi-command (3 ops)",
    "config_section": "Targeted config (1 op)",
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

            # Filter out failed runs (0 context tokens = rate limited or empty)
            valid_results = [
                r for r in run_results if r.get("context_tokens", 0) > 0
            ]
            if valid_results:
                avg = {}
                mins = {}
                maxs = {}
                for key in valid_results[0]:
                    values = [r[key] for r in valid_results]
                    avg[key] = sum(values) // len(values)
                    mins[key] = min(values)
                    maxs[key] = max(values)
                data["scenarios"][scenario][approach] = {
                    "runs": valid_results,
                    "valid_runs": len(valid_results),
                    "total_runs": len(run_results),
                    "average": avg,
                    "min": mins,
                    "max": maxs,
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

    # Determine actual valid run counts
    valid_counts = set()
    for scenario in SCENARIOS:
        sdata = data["scenarios"].get(scenario, {})
        for approach in APPROACHES:
            adata = sdata.get(approach, {})
            vr = adata.get("valid_runs")
            if vr is not None:
                valid_counts.add(vr)

    if len(valid_counts) == 1:
        valid_str = f"{valid_counts.pop()} valid"
    elif valid_counts:
        valid_str = f"{min(valid_counts)}-{max(valid_counts)} valid"
    else:
        valid_str = str(runs)

    print("## Results (Phase 2: Real-World Validation)\n")
    print(
        f"Phase 2 ran Claude Code (`claude -p`) with {model} against a live "
        f"vsrx1 device, comparing three approaches: jmcp via MCP, jcli via Bash "
        f"(no skill), and jcli via Bash with the SKILL.md skill installed. "
        f"Each scenario was run {runs} times per approach "
        f"({valid_str} runs after filtering rate-limited/empty sessions). "
        f"Token usage was extracted from raw JSONL session data via "
        f"`CLAUDE_CONFIG_DIR` isolation.\n"
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

    # --- Detailed statistics table ---
    print("### Detailed statistics (min / avg / max)\n")
    print(
        "Each cell shows min / avg / max across all runs. "
        "Context = input + cache creation + cache read tokens.\n"
    )
    print(
        "| Scenario | Approach | Turns | Context | Output |"
    )
    print(
        "|----------|----------|-------|---------|--------|"
    )

    for scenario in SCENARIOS:
        sdata = data["scenarios"].get(scenario, {})
        name = SCENARIO_NAMES.get(scenario, scenario)
        for approach in active_approaches:
            adata = sdata.get(approach, {})
            avg = adata.get("average", {})
            mins = adata.get("min", {})
            maxs = adata.get("max", {})
            if not avg or avg.get("num_turns", 0) == 0:
                continue
            label = name if approach == active_approaches[0] else ""
            t_min = mins.get("num_turns", 0)
            t_avg = avg.get("num_turns", 0)
            t_max = maxs.get("num_turns", 0)
            c_min = mins.get("context_tokens", 0)
            c_avg = avg.get("context_tokens", 0)
            c_max = maxs.get("context_tokens", 0)
            o_min = mins.get("output_tokens", 0)
            o_avg = avg.get("output_tokens", 0)
            o_max = maxs.get("output_tokens", 0)
            print(
                f"| {label} | {APPROACH_NAMES[approach]} | "
                f"{t_min} / {t_avg} / {t_max} | "
                f"{c_min:,} / {c_avg:,} / {c_max:,} | "
                f"{o_min:,} / {o_avg:,} / {o_max:,} |"
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

    # --- Scenario winners table ---
    print("\n### Scenario winners\n")
    print("| Scenario | Lowest Avg Turns | Lowest Avg Context | Winner |")
    print("|----------|-----------------|-------------------|--------|")

    for scenario in SCENARIOS:
        sdata = data["scenarios"].get(scenario, {})
        name = SCENARIO_NAMES.get(scenario, scenario)
        best_turns_approach = None
        best_turns = float("inf")
        best_ctx_approach = None
        best_ctx = float("inf")
        for approach in active_approaches:
            avg = sdata.get(approach, {}).get("average", {})
            if not avg or avg.get("num_turns", 0) == 0:
                continue
            turns = avg.get("num_turns", 0)
            ctx = avg.get("context_tokens", 0)
            if turns < best_turns:
                best_turns = turns
                best_turns_approach = approach
            if ctx < best_ctx:
                best_ctx = ctx
                best_ctx_approach = approach
        turns_label = (
            f"{APPROACH_NAMES[best_turns_approach]} ({best_turns})"
            if best_turns_approach
            else "N/A"
        )
        ctx_label = (
            f"{APPROACH_NAMES[best_ctx_approach]} ({best_ctx:,})"
            if best_ctx_approach
            else "N/A"
        )
        # Winner is the approach with lowest context (primary cost driver)
        winner = APPROACH_NAMES.get(best_ctx_approach, "N/A")
        print(f"| {name} | {turns_label} | {ctx_label} | {winner} |")


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
