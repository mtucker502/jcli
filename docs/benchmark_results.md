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

Phase 2 ran Claude Code (`claude -p`) with opus against a live vsrx1 device, comparing three approaches: jmcp via MCP, jcli via Bash (no skill), and jcli via Bash with the SKILL.md skill installed. Each scenario was run 3 times per approach (3 valid runs after filtering rate-limited/empty sessions). Token usage was extracted from raw JSONL session data via `CLAUDE_CONFIG_DIR` isolation.

### Detailed statistics (min / avg / max)

Each cell shows min / avg / max across all runs. Context = input + cache creation + cache read tokens.

| Scenario | Approach | Turns | Context | Output |
|----------|----------|-------|---------|--------|
| List routers (1 op) | MCP | 6 / 6 / 7 | 59,363 / 84,226 / 96,664 | 339 / 384 / 414 |
|  | CLI | 6 / 7 / 9 | 78,279 / 96,080 / 131,664 | 296 / 456 / 673 |
|  | Skill | 5 / 5 / 5 | 52,722 / 52,724 / 52,725 | 335 / 338 / 341 |
| Multi-op (3 ops) | MCP | 14 / 20 / 30 | 281,810 / 491,297 / 859,379 | 1,051 / 1,499 / 2,291 |
|  | CLI | 16 / 17 / 18 | 249,098 / 293,380 / 326,405 | 1,211 / 1,384 / 1,592 |
|  | Skill | 11 / 11 / 12 | 163,740 / 177,236 / 201,835 | 589 / 821 / 1,082 |
| Show services (1 op) | MCP | 10 / 10 / 12 | 112,185 / 128,632 / 146,523 | 795 / 942 / 1,150 |
|  | CLI | 11 / 11 / 12 | 166,570 / 176,484 / 187,696 | 933 / 1,181 / 1,322 |
|  | Skill | 5 / 5 / 5 | 51,623 / 51,623 / 51,623 | 544 / 551 / 559 |
| Show interfaces (1 op) | MCP | 10 / 10 / 12 | 122,882 / 141,610 / 156,472 | 758 / 940 / 1,151 |
|  | CLI | 10 / 11 / 13 | 152,075 / 178,289 / 229,333 | 841 / 944 / 1,042 |
|  | Skill | 6 / 6 / 7 | 73,796 / 78,826 / 88,850 | 608 / 719 / 832 |
| Full workflow (4 ops) | MCP | 18 / 26 / 37 | 223,740 / 529,241 / 899,832 | 1,646 / 2,610 / 3,383 |
|  | CLI | 15 / 15 / 16 | 238,926 / 254,029 / 268,041 | 1,466 / 1,593 / 1,737 |
|  | Skill | 12 / 12 / 12 | 184,293 / 184,326 / 184,347 | 1,303 / 1,313 / 1,332 |
| BGP peer filtering (1 op) | MCP | 13 / 14 / 15 | 142,499 / 207,735 / 242,395 | 981 / 1,230 / 1,420 |
|  | CLI | 9 / 11 / 13 | 132,290 / 175,034 / 206,112 | 925 / 1,192 / 1,450 |
|  | Skill | 5 / 5 / 6 | 51,783 / 62,435 / 68,607 | 572 / 719 / 798 |
| Config audit (2 ops) | MCP | 19 / 21 / 24 | 263,590 / 315,951 / 413,536 | 1,765 / 1,907 / 2,121 |
|  | CLI | 15 / 16 / 17 | 239,507 / 265,401 / 280,384 | 1,232 / 1,406 / 1,585 |
|  | Skill | 8 / 9 / 12 | 98,838 / 141,831 / 190,949 | 658 / 789 / 976 |
| Multi-command (3 ops) | MCP | 7 / 13 / 18 | 99,715 / 211,277 / 279,495 | 692 / 1,418 / 1,785 |
|  | CLI | 14 / 15 / 16 | 209,665 / 227,409 / 259,732 | 1,221 / 1,256 / 1,288 |
|  | Skill | 5 / 5 / 5 | 55,024 / 55,024 / 55,024 | 566 / 654 / 709 |
| Targeted config (1 op) | MCP | 9 / 10 / 11 | 105,827 / 126,667 / 137,117 | 970 / 1,051 / 1,096 |
|  | CLI | 11 / 11 / 13 | 154,416 / 167,323 / 193,108 | 961 / 1,051 / 1,098 |
|  | Skill | 5 / 5 / 5 | 51,726 / 51,726 / 51,726 | 491 / 520 / 575 |

### Context comparison

| Scenario | MCP Context | CLI Context | CLI vs MCP | Skill Context | Skill vs MCP |
|----------|-------------|-------------|------------|-------------|------------|
| List routers (1 op) | 84,226 | 96,080 | **+14.1%** | 52,724 | **-37.4%** |
| Multi-op (3 ops) | 491,297 | 293,380 | **-40.3%** | 177,236 | **-63.9%** |
| Show services (1 op) | 128,632 | 176,484 | **+37.2%** | 51,623 | **-59.9%** |
| Show interfaces (1 op) | 141,610 | 178,289 | **+25.9%** | 78,826 | **-44.3%** |
| Full workflow (4 ops) | 529,241 | 254,029 | **-52.0%** | 184,326 | **-65.2%** |
| BGP peer filtering (1 op) | 207,735 | 175,034 | **-15.7%** | 62,435 | **-69.9%** |
| Config audit (2 ops) | 315,951 | 265,401 | **-16.0%** | 141,831 | **-55.1%** |
| Multi-command (3 ops) | 211,277 | 227,409 | **+7.6%** | 55,024 | **-74.0%** |
| Targeted config (1 op) | 126,667 | 167,323 | **+32.1%** | 51,726 | **-59.2%** |

### Scenario winners

| Scenario | Lowest Avg Turns | Lowest Avg Context | Winner |
|----------|-----------------|-------------------|--------|
| List routers (1 op) | Skill (5) | Skill (52,724) | Skill |
| Multi-op (3 ops) | Skill (11) | Skill (177,236) | Skill |
| Show services (1 op) | Skill (5) | Skill (51,623) | Skill |
| Show interfaces (1 op) | Skill (6) | Skill (78,826) | Skill |
| Full workflow (4 ops) | Skill (12) | Skill (184,326) | Skill |
| BGP peer filtering (1 op) | Skill (5) | Skill (62,435) | Skill |
| Config audit (2 ops) | Skill (9) | Skill (141,831) | Skill |
| Multi-command (3 ops) | Skill (5) | Skill (55,024) | Skill |
| Targeted config (1 op) | Skill (5) | Skill (51,726) | Skill |

**Score: Skill 9, CLI 0, MCP 0.**

Skill won every scenario, with context savings of 37–74% vs MCP. The dominant factor is turn count — Skill completed single-op tasks in 5 turns while MCP required 6–14 and CLI required 7–16. SKILL.md eliminates command discovery overhead entirely, letting the model execute the right command on the first attempt. Skill also showed dramatically lower variance (e.g., list routers context range of 52,722–52,725 vs MCP's 59,363–96,664).
