# jcli

CLI tool for Juniper Junos device management via NETCONF/PyEZ.

## Table of Contents

- [jcli](#jcli)
  - [Table of Contents](#table-of-contents)
  - [Install](#install)
  - [Device Inventory](#device-inventory)
  - [Commands](#commands)
    - [Device Management](#device-management)
    - [Command Execution](#command-execution)
    - [Configuration](#configuration)
  - [Safety Blocklists](#safety-blocklists)
  - [Environment Variables](#environment-variables)

## Install

```
pip install .
```

Or run directly:

```
uv run jcli --help
```

## Device Inventory

Devices are stored in `devices.json` (or set via `--inventory` / `JCLI_INVENTORY`).

```
jcli device add r1 --ip 10.0.1.1 --user admin --auth-type ssh_key --key-file ~/.ssh/id_rsa
jcli device add r2 --ip 10.0.1.2 --user admin --auth-type password --password secret
jcli device add r3 --ip 10.0.1.3 --user root --auth-type ssh_agent
```

Auth types: `password`, `ssh_key`, `ssh_agent`.

## Commands

All commands support `--json` for structured output: `jcli --json <command>`.

### Device Management

```
jcli device list                        # list all routers
jcli device facts r1                    # gather device facts
jcli device add r1 --ip ... --user ...  # add device to inventory
jcli device reload                      # re-read devices.json
```

### Command Execution

```
jcli command run r1 "show bgp summary"                  # single device
jcli command batch "show interfaces terse" r1 r2 r3     # parallel execution
```

### Configuration

```
jcli config show r1                                             # full config (set format)
jcli config diff r1 --rollback 3                                # diff against rollback
jcli config load r1 "set system host-name new-name"             # load and commit
echo "set ..." | jcli config load r1 --stdin                    # load from stdin
jcli config template -t bgp.j2 -V site.yaml                    # render template
jcli config template -t bgp.j2 -V site.yaml -r r1 --apply      # render and apply
```

## Safety Blocklists

Operational commands and configuration changes are checked against blocklist files before execution.

Create `block.cmd` to block operational commands (one pattern per line):

```
request system reboot
request system halt
request system zeroize
```

Create `block.cfg` to block configuration patterns:

```
set system root-authentication
set system login user ([^ ]+) authentication
```

Patterns support regex. Lines starting with `#` are comments.

Example files are provided in `examples/`. Copy them to your working directory and edit as needed:

```
cp examples/block.cmd examples/block.cfg .
```

Or specify paths via `JCLI_BLOCK_CMD` and `JCLI_BLOCK_CFG` environment variables. If no blocklist file is found, no restrictions are applied.

## Environment Variables

| Variable         | Purpose                   | Default          |
| ---------------- | ------------------------- | ---------------- |
| `JCLI_INVENTORY` | Path to devices.json      | `./devices.json` |
| `JCLI_TIMEOUT`   | Command timeout (seconds) | `360`            |
| `JCLI_BLOCK_CMD` | Path to command blocklist | `./block.cmd`    |
| `JCLI_BLOCK_CFG` | Path to config blocklist  | `./block.cfg`    |
