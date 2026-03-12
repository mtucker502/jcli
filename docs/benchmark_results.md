# Token Efficiency Benchmark Results

Results from the [benchmark methodology](benchmark.md). Three approaches compared: jmcp (MCP), jcli (CLI, no skill), and jcli + Skill (CLI with SKILL.md).

## Results (Phase 1: Static Token Counting)

All results below are from Phase 1 — static token counting with tiktoken. Per-call request and response overhead is identical for CLI and Skill (both use Bash tool with raw stdout). The only Phase 1 difference is one-time schema overhead.

### Schema overhead (one-time)

| Component | MCP | CLI | Skill |
|-----------|-----|-----|-------|
| Tool definitions / context | 936 | 0 | 2,292 |

MCP pays 936 tokens upfront to register 7 tool definitions. CLI pays zero — the Bash tool is already available. Skill pays 2,292 tokens for SKILL.md — a richer context (command reference, examples, workflow patterns) that costs more than MCP's JSON Schema but aims to provide better LLM guidance.

### Per-operation overhead

Per-call overhead is identical for CLI and Skill — both use the Bash tool with raw stdout responses.

| Operation | MCP Req | CLI Req | MCP Resp | CLI Resp | Req Savings | Resp Savings | Total Savings |
|-----------|---------|---------|----------|----------|------------|--------------|---------------|
| List devices | 31 | 36 | 51 | 16 | -5 | 35 | 30 |
| Device facts | 39 | 39 | 525 | 420 | 0 | 105 | 105 |
| Execute command | 48 | 45 | 469 | 359 | 3 | 110 | 113 |
| Show config | 39 | 39 | 2705 | 2648 | 0 | 57 | 57 |
| Config diff | 39 | 39 | 210 | 138 | 0 | 72 | 72 |
| Load config | 67 | 46 | 115 | 39 | 21 | 76 | 97 |

**Request tokens** are roughly comparable between approaches. For simple operations with few or no parameters (list, facts, config, diff), MCP's compact `{"input": {}}` matches or beats the CLI's `{"command": "jcli ..."}` wrapper. CLI wins on operations with more parameters (execute command, load config) where positional args are shorter than JSON key-value pairs.

**Response tokens** are where CLI consistently wins. MCP wraps every response in a `tool_result` structure with `TextContent` type metadata and handler-specific annotations. CLI returns raw stdout text. Savings range from 35 tokens (list devices) to 110 tokens (execute command).

### Session simulations

| Session | MCP Total | CLI Total | Skill Total | CLI Savings | Skill Savings |
|---------|-----------|-----------|-------------|-------------|---------------|
| 4-op workflow | 4,843 | 3,602 | 5,894 | 1,241 (25.6%) | -1,051 (-21.7%) |
| 6-op workflow | 5,274 | 3,864 | 6,156 | 1,410 (26.7%) | -882 (-16.7%) |

CLI Total = per-call costs only (no schema overhead). Skill Total = CLI per-call costs + 2,292 tokens for SKILL.md.

In Phase 1, Skill is the most expensive approach due to SKILL.md's richer context (2,292 tokens vs MCP's 936). However, Phase 1 only measures static overhead — it cannot capture the skill's potential to reduce turn count variance, which Phase 2 measures.
## Results (Phase 2: Real-World Validation)

Phase 2 ran Claude Code (`claude -p`) with opus against a live vsrx1 device, comparing three approaches: jmcp via MCP, jcli via Bash (no skill), and jcli via Bash with the SKILL.md skill installed. Each scenario was run 20 times per approach (4-5 valid runs after filtering rate-limited/empty sessions). Token usage was extracted from raw JSONL session data via `CLAUDE_CONFIG_DIR` isolation.

### Detailed statistics (min / avg / max)

Each cell shows min / avg / max across all runs. Context = input + cache creation + cache read tokens.

| Scenario | Approach | Turns | Context | Output |
|----------|----------|-------|---------|--------|
| List routers (1 op) | MCP | 5 / 5 / 6 | 44,591 / 52,550 / 64,481 | 322 / 377 / 451 |
|  | CLI | 5 / 5 / 5 | 62,595 / 62,600 / 62,624 | 291 / 335 / 356 |
|  | Skill | 5 / 5 / 5 | 56,682 / 58,579 / 66,143 | 285 / 314 / 363 |
| Multi-op (3 ops) | MCP | 6 / 7 / 8 | 44,045 / 92,452 / 104,560 | 541 / 631 / 659 |
|  | CLI | 7 / 7 / 7 | 98,788 / 98,832 / 98,854 | 429 / 589 / 646 |
|  | Skill | 7 / 7 / 8 | 98,879 / 101,155 / 104,583 | 577 / 622 / 685 |
| Show services (1 op) | MCP | 4 / 5 / 8 | 45,492 / 69,722 / 102,947 | 452 / 543 / 620 |
|  | CLI | 4 / 5 / 6 | 45,522 / 69,984 / 80,497 | 443 / 590 / 652 |
|  | Skill | 5 / 5 / 7 | 66,301 / 73,742 / 103,262 | 353 / 497 / 651 |
| Show interfaces (1 op) | MCP | 3 / 5 / 6 | 28,011 / 57,168 / 68,504 | 473 / 652 / 716 |
|  | CLI | 5 / 6 / 8 | 68,545 / 98,661 / 125,870 | 646 / 834 / 1,025 |
|  | Skill | 5 / 5 / 6 | 70,005 / 74,282 / 90,782 | 581 / 667 / 839 |
| Full workflow (4 ops) | MCP | 9 / 11 / 14 | 123,906 / 136,809 / 156,347 | 844 / 1,167 / 1,520 |
|  | CLI | 9 / 9 / 10 | 123,911 / 138,727 / 143,774 | 1,080 / 1,121 / 1,178 |
|  | Skill | 9 / 9 / 9 | 123,954 / 124,024 / 124,050 | 628 / 993 / 1,158 |
| BGP peer filtering (1 op) | MCP | 4 / 5 / 7 | 30,816 / 69,553 / 98,158 | 518 / 730 / 861 |
|  | CLI | 5 / 6 / 8 | 64,671 / 96,947 / 120,151 | 597 / 746 / 1,024 |
|  | Skill | 5 / 7 / 9 | 64,099 / 113,635 / 140,806 | 668 / 821 / 992 |
| Config audit (2 ops) | MCP | 11 / 13 / 19 | 129,138 / 214,087 / 327,803 | 848 / 1,369 / 1,925 |
|  | CLI | 10 / 11 / 12 | 150,534 / 176,634 / 192,836 | 916 / 1,110 / 1,330 |
|  | Skill | 9 / 11 / 14 | 132,321 / 174,417 / 226,056 | 773 / 895 / 1,164 |
| Multi-command (3 ops) | MCP | 7 / 7 / 9 | 99,105 / 108,124 / 131,915 | 741 / 826 / 882 |
|  | CLI | 7 / 7 / 10 | 108,382 / 122,127 / 163,037 | 635 / 715 / 849 |
|  | Skill | 7 / 7 / 7 | 90,422 / 98,564 / 101,279 | 537 / 682 / 772 |
| Targeted config (1 op) | MCP | 3 / 3 / 5 | 25,176 / 33,703 / 53,699 | 295 / 413 / 529 |
|  | CLI | 4 / 5 / 7 | 45,511 / 67,533 / 98,546 | 435 / 673 / 938 |
|  | Skill | 4 / 5 / 6 | 45,613 / 65,183 / 82,430 | 467 / 594 / 733 |

### Context comparison

| Scenario | MCP Context | CLI Context | CLI vs MCP | Skill Context | Skill vs MCP |
|----------|-------------|-------------|------------|-------------|------------|
| List routers (1 op) | 52,550 | 62,600 | **+19.1%** | 58,579 | **+11.5%** |
| Multi-op (3 ops) | 92,452 | 98,832 | **+6.9%** | 101,155 | **+9.4%** |
| Show services (1 op) | 69,722 | 69,984 | **+0.4%** | 73,742 | **+5.8%** |
| Show interfaces (1 op) | 57,168 | 98,661 | **+72.6%** | 74,282 | **+29.9%** |
| Full workflow (4 ops) | 136,809 | 138,727 | **+1.4%** | 124,024 | **-9.3%** |
| BGP peer filtering (1 op) | 69,553 | 96,947 | **+39.4%** | 113,635 | **+63.4%** |
| Config audit (2 ops) | 214,087 | 176,634 | **-17.5%** | 174,417 | **-18.5%** |
| Multi-command (3 ops) | 108,124 | 122,127 | **+13.0%** | 98,564 | **-8.8%** |
| Targeted config (1 op) | 33,703 | 67,533 | **+100.4%** | 65,183 | **+93.4%** |

### Scenario winners

| Scenario | Lowest Avg Turns | Lowest Avg Context | Winner |
|----------|-----------------|-------------------|--------|
| List routers (1 op) | MCP (5) | MCP (52,550) | MCP |
| Multi-op (3 ops) | MCP (7) | MCP (92,452) | MCP |
| Show services (1 op) | MCP (5) | MCP (69,722) | MCP |
| Show interfaces (1 op) | MCP (5) | MCP (57,168) | MCP |
| Full workflow (4 ops) | CLI (9) | Skill (124,024) | Skill |
| BGP peer filtering (1 op) | MCP (5) | MCP (69,553) | MCP |
| Config audit (2 ops) | CLI (11) | Skill (174,417) | Skill |
| Multi-command (3 ops) | MCP (7) | Skill (98,564) | Skill |
| Targeted config (1 op) | MCP (3) | MCP (33,703) | MCP |
