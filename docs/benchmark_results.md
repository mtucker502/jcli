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

Phase 2 ran Claude Code (`claude -p`) with Haiku against a live vsrx1 device, comparing all three approaches: jmcp via MCP, jcli via Bash (no skill), and jcli via Bash with SKILL.md installed. Each scenario was run 5 times per approach (75 total invocations). Token usage was extracted from raw JSONL session data via `CLAUDE_CONFIG_DIR` isolation.

### Averaged results

Context tokens = input + cache creation + cache read (total tokens the API processed per session).

| Scenario | Approach | Avg Turns | Avg Context | Avg Output |
|----------|----------|-----------|-------------|------------|
| List routers (1 op) | MCP | 7 | 183,607 | 591 |
| | CLI | 5 | 121,218 | 367 |
| | Skill | 24 | 677,319 | 1,818 |
| Multi-op (3 ops) | MCP | 8 | 213,667 | 956 |
| | CLI | 11 | 291,515 | 1,190 |
| | Skill | 9 | 240,162 | 1,114 |
| Show services (1 op) | MCP | 12 | 295,395 | 1,278 |
| | CLI | 16 | 438,736 | 1,764 |
| | Skill | 25 | 719,575 | 2,502 |
| Show interfaces (1 op) | MCP | 13 | 334,172 | 1,284 |
| | CLI | 10 | 257,771 | 1,173 |
| | Skill | 7 | 186,776 | 1,119 |
| Full workflow (4 ops) | MCP | 15 | 375,341 | 1,642 |
| | CLI | 18 | 456,961 | 1,831 |
| | Skill | 20 | 567,279 | 2,188 |

### Context comparison

| Scenario | MCP Context | CLI Context | CLI vs MCP | Skill Context | Skill vs MCP |
|----------|-------------|-------------|------------|---------------|--------------|
| List routers (1 op) | 183,607 | 121,218 | **-34.0%** | 677,319 | **+268.9%** |
| Multi-op (3 ops) | 213,667 | 291,515 | **+36.4%** | 240,162 | **+12.4%** |
| Show services (1 op) | 295,395 | 438,736 | **+48.5%** | 719,575 | **+143.6%** |
| Show interfaces (1 op) | 334,172 | 257,771 | **-22.9%** | 186,776 | **-44.1%** |
| Full workflow (4 ops) | 375,341 | 456,961 | **+21.7%** | 567,279 | **+51.1%** |

### Per-run variance

The averages mask significant run-to-run variance. The ranges below show how much individual runs deviated.

| Scenario | Approach | Turn Range | Context Range |
|----------|----------|------------|---------------|
| List routers (1 op) | MCP | 4-12 | 92,864 - 283,504 |
| | CLI | 4-10 | 92,770 - 234,954 |
| | Skill | 4-46 | 93,528 - 1,329,190 |
| Multi-op (3 ops) | MCP | 5-18 | 120,732 - 443,000 |
| | CLI | 4-29 | 97,378 - 735,467 |
| | Skill | 6-24 | 144,154 - 588,866 |
| Show services (1 op) | MCP | 4-22 | 93,390 - 570,924 |
| | CLI | 10-34 | 239,694 - 960,881 |
| | Skill | 14-44 | 368,552 - 1,341,940 |
| Show interfaces (1 op) | MCP | 4-26 | 99,048 - 669,816 |
| | CLI | 6-16 | 140,672 - 383,877 |
| | Skill | 4-10 | 99,134 - 263,132 |
| Full workflow (4 ops) | MCP | 11-24 | 267,120 - 627,232 |
| | CLI | 12-24 | 292,942 - 599,781 |
| | Skill | 11-33 | 271,009 - 860,894 |

### Scenario winners

| Scenario | Lowest Turns | Lowest Context | Winner |
|----------|-------------|----------------|--------|
| List routers | CLI (5) | CLI (121K) | CLI |
| Multi-op | MCP (8) | MCP (214K) | MCP |
| Show services | MCP (12) | MCP (295K) | MCP |
| Show interfaces | Skill (7) | Skill (187K) | Skill |
| Full workflow | MCP (15) | MCP (375K) | MCP |

### Phase 2 analysis

**No single approach dominates.** MCP won 3 of 5 scenarios, CLI won 1, and Skill won 1. The results depend heavily on scenario characteristics.

**MCP excels at multi-step structured tasks.** For multi-op (3 tasks), show services, and the full workflow, MCP's typed tool schemas guided the model to complete work in fewer turns. MCP averaged 8-15 turns across these scenarios vs 11-18 for CLI and 9-25 for Skill.

**CLI wins when exact commands are specified.** For list routers — the simplest task where the prompt included the exact command — CLI completed in 5 turns (vs MCP's 7, Skill's 24). When the model knows exactly what to do, the lack of schema overhead and direct Bash execution is most efficient.

**Skill won the composability scenario.** For show interfaces (finding drop counters), Skill averaged just 7 turns and 187K context — the lowest of all approaches. The SKILL.md command reference helped the model compose a targeted `jcli command run` + `grep` pipeline efficiently, beating both MCP (13 turns) and CLI (10 turns).

**Skill had the highest variance overall.** Skill turn ranges were the widest in 3 of 5 scenarios (list routers: 4-46, show services: 14-44, full workflow: 11-33). The SKILL.md context sometimes caused the model to over-explore rather than execute directly, contradicting the hypothesis that richer context would reduce variance.

**The system prompt still dominates context cost.** Each API turn includes ~25K tokens of Claude Code system prompt (mostly via cache). This makes turn count the primary cost driver — a single extra turn costs more than MCP's entire 936-token schema overhead.

**All approaches have significant outliers.** MCP had an 18-turn run in multi-op and a 26-turn run in show interfaces. CLI had a 29-turn outlier in multi-op and a 34-turn outlier in show services. Skill had a 46-turn outlier in list routers and a 44-turn outlier in show services. The variance suggests that 5 runs is insufficient for high-confidence averages, but the directional trends are informative.

## Summary

### Phase 1 (static token analysis)

- **936 tokens** of MCP schema overhead eliminated per session (MCP tool definitions)
- **SKILL.md** adds a one-time context cost of 2,292 tokens (more than MCP's 936-token schema)
- **474 tokens** saved across all 6 operations from leaner responses (10.9% per-call reduction) — identical for CLI and Skill
- **1,410 tokens** total savings in a 6-operation session for CLI (26.7% reduction)
- Response wrapping and annotations account for the majority of per-call savings
- Request overhead is roughly equivalent — positional CLI args vs structured JSON is a wash for simple operations
- Phase 1 deliberately excludes composability scenarios (output filtering, targeted commands) — these depend on LLM behavior and are measured in Phase 2

### Phase 2 (real-world validation, three-way comparison)

- **MCP won 3 of 5 scenarios** (multi-op, show services, full workflow) — structured tool schemas guide multi-step tasks most efficiently
- **CLI won 1 scenario** (list routers) — direct Bash execution with exact commands is fastest for simple tasks
- **Skill won 1 scenario** (show interfaces) — SKILL.md helped compose targeted command pipelines for the composability test
- **Skill had the highest variance** in 3 of 5 scenarios, contradicting the hypothesis that richer context would reduce turn count variance
- The dominant cost factor remains **number of API turns**, not per-token overhead
- Each extra turn adds ~25K+ tokens of context (Claude Code's system prompt), making turn consistency the primary cost driver
- All approaches showed significant run-to-run variance — 5 runs is directionally informative but not statistically robust

### Combined takeaway

Phase 1 and Phase 2 measure different things and reach different conclusions:

1. **Per-token overhead** (Phase 1): CLI is cheapest (zero schema, lean responses), MCP is middle (936-token schema, wrapped responses), Skill is most expensive (2,292-token SKILL.md). CLI saves 1,410 tokens in a 6-operation session (26.7% reduction vs MCP).

2. **Real-world efficiency** (Phase 2): MCP is most efficient for structured multi-step tasks (3 of 5 scenarios). CLI wins for simple direct-command tasks. Skill's advantage is limited to composability scenarios where its command reference helps the model construct targeted pipelines.

3. **Skill hypothesis result**: The skill did not achieve the predicted combination of CLI efficiency and MCP consistency. Instead, it introduced the highest turn variance of all three approaches in most scenarios. The one exception — show interfaces — demonstrates that skills can help with command composition, but this benefit was scenario-specific rather than general.

4. **Turn count is everything.** Phase 1's 474-token per-session savings are negligible compared to the ~25K-token cost of each additional API turn. The approach that minimizes turns wins, regardless of per-token overhead.

The optimal choice depends on the task type: MCP for structured multi-step workflows, CLI for simple direct operations, and potentially Skill for composability-heavy scenarios where the LLM needs to discover and chain commands.
