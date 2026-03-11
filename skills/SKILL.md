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

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (device not found, connection failed, validation error) |
| 2 | Blocked by safety blocklist |

For `command batch`: exit 0 even with partial failures — check per-device `status` in JSON output.

## Detailed Command Usage

### Device Inventory

**List devices:**
```bash
jcli device list
jcli --json device list    # {"routers": ["r1", "r2"]}
```

**Get device facts:**
```bash
jcli device facts lab1
jcli device facts lab1 --timeout 120
```

**Add a device (3 auth types):**
```bash
# Password auth
jcli device add lab1 --ip 10.0.1.1 --user admin --auth-type password --password s3cr3t

# SSH key auth
jcli device add lab2 --ip 10.0.1.2 --user admin --auth-type ssh_key --key-file ~/.ssh/id_rsa

# SSH agent auth
jcli device add lab3 --ip 10.0.1.3 --user admin --auth-type ssh_agent

# With custom port, SSH config (jumphost), and connectivity test
jcli device add lab4 --ip 10.0.1.4 --port 830 --user admin --auth-type ssh_key \
  --key-file ~/.ssh/id_rsa --ssh-config ~/.ssh/config --test
```

Required: `--ip`, `--user`, `--auth-type`. Conditional: `--password` (password auth), `--key-file` (ssh_key auth).

**Reload inventory:**
```bash
jcli device reload                    # re-read current file
jcli device reload /etc/jcli/new.json # switch inventory file
```

### Running Commands

**Single command:**
```bash
jcli command run lab1 "show interfaces terse"
jcli --json command run lab1 "show bgp summary"
# JSON: {"router": "lab1", "command": "...", "output": "...", "duration": 0.523}
```

**Batch (parallel across devices):**
```bash
jcli command batch "show version" r1 r2 r3
jcli command batch "show bgp summary" r1 r2 r3 --parallel 10
jcli --json command batch "show interfaces terse" r1 r2 r3
# JSON: {"results": [{"router": "r1", "status": "success", "output": "...", "duration": 0.5}, ...]}
```

Default parallelism: 5 workers. Override with `--parallel/-p`.

### Configuration Management

**Show full config (set format):**
```bash
jcli config show lab1
```

**Diff against rollback:**
```bash
jcli config diff lab1              # vs rollback 1 (previous commit)
jcli config diff lab1 --rollback 5 # vs rollback 5
```
Rollback range: 1–49.

**Load and commit config:**
```bash
# Inline set commands
jcli config load lab1 "set system host-name new-name"

# From stdin (multi-line)
cat changes.conf | jcli config load lab1 --stdin

# Heredoc
jcli config load lab1 --stdin <<'EOF'
set system host-name new-name
set system domain-name lab.local
EOF

# Different formats
jcli config load lab1 "system { host-name new; }" --format text
jcli config load lab1 "<configuration>...</configuration>" --format xml

# With commit comment
jcli config load lab1 "set system host-name new" --comment "Hostname change ticket-1234"
```

Format options: `set` (default), `text`, `xml`. The load operation is atomic: lock → load → diff → commit → unlock, with automatic rollback on error.

**Template rendering:**
```bash
# Render only (preview)
jcli config template -t bgp.j2 -V vars.yaml

# Render and apply to devices
jcli config template -t bgp.j2 -V vars.yaml --router r1 --router r2 --apply

# Dry-run (show what would be applied, no commit)
jcli config template -t bgp.j2 -V vars.yaml --router r1 --apply --dry-run

# With format and commit comment
jcli config template -t bgp.j2 -V vars.yaml -r r1 --apply --format text --comment "BGP rollout"
```

## Safety Blocklists

Two blocklist files prevent dangerous operations. Patterns are regex, one per line, `#` for comments.

| Blocklist | Env Var | Default | Protects |
|-----------|---------|---------|----------|
| `block.cmd` | `JCLI_BLOCK_CMD` | `./block.cmd` | `command run`, `command batch` |
| `block.cfg` | `JCLI_BLOCK_CFG` | `./block.cfg` | `config load`, `config template --apply` |

Blocked commands/configs exit with code 2. If the blocklist file is missing, no restrictions are applied.

Default command blocks: `request system reboot`, `halt`, `power-cycle`, `power-off`, `zeroize`.
Default config blocks: `set system root-authentication`, `set system login user * authentication`.

## devices.json Format

```json
{
  "router_name": {
    "ip": "10.0.1.1",
    "port": 22,
    "username": "admin",
    "auth": {
      "type": "password|ssh_key|ssh_agent",
      "password": "...",
      "private_key_path": "/path/to/key"
    },
    "ssh_config": "/optional/ssh/config"
  }
}
```

Auth type determines required fields: `password` needs `auth.password`, `ssh_key` needs `auth.private_key_path`, `ssh_agent` needs nothing extra. `ssh_config` is optional (for jumphosts).

## Workflow Patterns

### Investigate a device
```bash
jcli device facts lab1                           # what hardware/OS?
jcli command run lab1 "show system alarms"        # any alarms?
jcli command run lab1 "show interfaces terse"     # interface status
jcli config diff lab1                             # any uncommitted changes?
```

### Audit multiple devices
```bash
jcli --json command batch "show version" r1 r2 r3 r4  # parallel version check
jcli --json command batch "show system alarms" r1 r2 r3 r4
```

### Safe configuration change
```bash
# 1. Check current state
jcli config show lab1 | grep "host-name"

# 2. Load config (automatic lock/commit/unlock with rollback on error)
jcli config load lab1 "set system host-name new-name" --comment "rename per ticket-123"

# 3. Verify
jcli command run lab1 "show system information | match host-name"
```

### Template-driven rollout
```bash
# 1. Preview rendered config
jcli config template -t bgp.j2 -V site.yaml

# 2. Dry-run against target devices
jcli config template -t bgp.j2 -V site.yaml -r r1 -r r2 --apply --dry-run

# 3. Apply
jcli config template -t bgp.j2 -V site.yaml -r r1 -r r2 --apply --comment "BGP rollout"
```

## Tips

- Always use `--json` when you need to parse output programmatically
- Quote multi-word commands: `"show bgp summary"`, not `show bgp summary`
- `command batch` validates all routers exist before executing on any
- `config load` shows the diff on success — use it to verify what changed
- Template `--dry-run` is free (no device connection needed) — always preview first
- Blocklist exit code 2 is distinct from error code 1 — handle them separately
- Per-command `--timeout` overrides the global `--timeout`
