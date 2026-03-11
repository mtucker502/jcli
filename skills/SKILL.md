# jcli — Junos Device Management CLI

Use this skill when managing Juniper Junos network devices: running operational commands, viewing/loading configuration, managing device inventory, or rendering config templates. jcli wraps PyEZ/NETCONF into simple shell commands.

## Quick Reference

```
jcli [--json] [--inventory PATH] [--timeout SECS] [--verbose] <group> <command>
```

| Command | Purpose | Example |
|---------|---------|---------|
| `jcli device list` | List inventory | `jcli device list` |
| `jcli device facts ROUTER` | Hardware/OS info | `jcli device facts lab1` |
| `jcli device add NAME` | Add device | `jcli device add lab1 --ip 10.0.1.1 --user admin --auth-type password --password s3cr3t` |
| `jcli device reload [PATH]` | Reload inventory | `jcli device reload` |
| `jcli command run ROUTER CMD` | Run one command | `jcli command run lab1 "show bgp summary"` |
| `jcli command batch CMD R1 R2…` | Parallel execution | `jcli command batch "show version" lab1 lab2 lab3` |
| `jcli config show ROUTER` | Full config (set fmt) | `jcli config show lab1` |
| `jcli config diff ROUTER` | Diff vs rollback | `jcli config diff lab1 --rollback 2` |
| `jcli config load ROUTER CFG` | Load & commit config | `jcli config load lab1 "set system host-name new"` |
| `jcli config template` | Render/apply Jinja2 | `jcli config template -t bgp.j2 -V vars.yaml` |

## Global Options (before command group)

| Flag | Env Var | Default | Effect |
|------|---------|---------|--------|
| `--json / -j` | — | off | JSON output for all commands |
| `--inventory / -f PATH` | `JCLI_INVENTORY` | `./devices.json` | Inventory file path |
| `--timeout / -t SECS` | `JCLI_TIMEOUT` | `360` | Default command timeout |
| `--verbose / -v` | — | off | Debug logging |

Global options go **before** the command group:
```bash
jcli --json --timeout 60 command run lab1 "show version"   # correct
jcli command run lab1 "show version" --json                 # WRONG
```

Exit codes: 0=success, 1=error, 2=blocked by safety. Batch exits 0 with partial failures (check per-device `status` in JSON output).

## Gotchas

- `config load`: use `--stdin` for multi-line config (heredoc or pipe). `--format` selects set (default) / text / xml.
- `config template`: requires `-t TEMPLATE` + `-V VARS`. Add `--router R` + `--apply` to push to devices. `--dry-run` previews without committing.
- `device add`: requires `--ip`, `--user`, `--auth-type` (password/ssh_key/ssh_agent). Conditional: `--password` or `--key-file`.
- `config diff`: `--rollback N` compares against rollback N (1-49, default 1).
- `command batch`: `--parallel N` sets worker count (default 5).
