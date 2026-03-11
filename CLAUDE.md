# jcli

CLI tool for Junos device management via NETCONF/PyEZ. Replaces jmcp MCP server with shell commands for token efficiency.

## Stack

- Python 3.12, Click CLI, Hatchling build, src layout
- PyEZ (junos-eznc) for NETCONF over SSH
- Jinja2 + PyYAML for template rendering
- venv at `.venv/`, install: `pip install -e ".[dev]"`
- Run tests: `.venv/bin/pytest tests/ -v`
- Lint: `.venv/bin/ruff check src/ tests/`

## Structure

```
src/jcli/cli/main.py          # Click group, global options (--json, --inventory, --timeout)
src/jcli/cli/commands/         # device.py, command.py, config.py
src/jcli/device/inventory.py   # DeviceInventory (loads devices.json)
src/jcli/device/config.py      # validate + prepare_connection_params (ported from jmcp)
src/jcli/device/config_ops.py  # load_and_commit (lock/check/rollback safety)
src/jcli/device/connection.py  # JunosConnection wrapper around PyEZ
src/jcli/safety/blocklist.py   # command/config blocklist checking
src/jcli/template/renderer.py  # Jinja2 + YAML rendering
src/jcli/output/formatter.py   # plain text (default) and JSON output
examples/                      # block.cmd, block.cfg examples
skills/SKILL.md               # Claude Code skill (install via jcli --install-skill)
```

## Patterns

- `@click.pass_obj` passes `CliContext` (json_output, inventory, timeout)
- Lazy-import `JunosConnection` inside command functions (avoids PyEZ import at CLI load)
- Errors to stderr via `output_error()`, data to stdout
- Exit codes: 0=success, 1=error, 2=blocked by safety
- Auth types: `password`, `ssh_key`, `ssh_agent`
- devices.json format is shared with jmcp (interoperable)

## Commands (10 total)

```
jcli device list|facts|add|reload
jcli command run|batch
jcli config show|diff|load|template
```
