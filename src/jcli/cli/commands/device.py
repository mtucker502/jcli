"""Device management commands: list, facts, add, reload."""

import sys

import click

from jcli.output.formatter import (
    format_device_list,
    format_facts,
    output_error,
    click_echo,
)


@click.group()
def device():
    """Manage Junos device inventory."""
    pass


@device.command("list")
@click.pass_obj
def device_list(ctx):
    """List all configured routers."""
    try:
        routers = ctx.inventory.list_devices()
    except Exception as e:
        output_error(str(e), ctx.json_output)
        sys.exit(1)
    if not routers:
        output_error("No devices configured", ctx.json_output)
        sys.exit(1)
    click_echo(format_device_list(routers, ctx.json_output))


@device.command()
@click.argument("router")
@click.option("--timeout", "-t", type=int, default=None, help="Command timeout in seconds.")
@click.pass_obj
def facts(ctx, router, timeout):
    """Gather device facts from ROUTER."""
    from jcli.device.connection import JunosConnection

    timeout = timeout or ctx.timeout
    try:
        device_info = ctx.inventory.get_device(router)
    except KeyError as e:
        output_error(str(e), ctx.json_output)
        sys.exit(1)
    try:
        conn = JunosConnection(device_info, router, timeout)
        device_facts = conn.get_facts()
    except Exception as e:
        output_error(str(e), ctx.json_output)
        sys.exit(1)
    click_echo(format_facts(router, device_facts, ctx.json_output))


@device.command()
@click.argument("name")
@click.option("--ip", required=True, help="Device IP address.")
@click.option("--port", type=int, default=22, help="SSH port.")
@click.option("--user", required=True, help="Username.")
@click.option(
    "--auth-type", required=True, type=click.Choice(["password", "ssh_key", "ssh_agent"]),
    help="Authentication type.",
)
@click.option(
    "--password", default=None, hidden=True,
    help="Password (for password auth). Prefer interactive prompt.",
)
@click.option("--key-file", default=None, help="SSH private key path (for ssh_key auth).")
@click.option("--ssh-config", default=None, help="SSH config file path (for jumphost/proxy).")
@click.option("--test", "test_conn", is_flag=True, help="Test connectivity after adding.")
@click.pass_obj
def add(ctx, name, ip, port, user, auth_type, password, key_file, ssh_config, test_conn):
    """Add a new device to the inventory.

    Example: jcli device add lab1 --ip 10.0.1.1 --user admin --auth-type ssh_key --key-file ~/.ssh/id_rsa
    """
    if auth_type == "password" and not password:
        password = click.prompt("Password", hide_input=True)
    if auth_type == "ssh_key" and not key_file:
        output_error("--key-file required when --auth-type is ssh_key", ctx.json_output)
        sys.exit(1)

    device_config = {
        "ip": ip,
        "port": port,
        "username": user,
        "auth": {"type": auth_type},
    }

    if auth_type == "password":
        device_config["auth"]["password"] = password
    elif auth_type == "ssh_key":
        device_config["auth"]["private_key_path"] = key_file

    if ssh_config:
        device_config["ssh_config"] = ssh_config

    try:
        ctx.inventory.add_device(name, device_config)
        ctx.inventory.save()
    except (ValueError, OSError) as e:
        output_error(str(e), ctx.json_output)
        sys.exit(1)

    if test_conn:
        from jcli.device.connection import JunosConnection

        try:
            conn = JunosConnection(device_config, name, ctx.timeout)
            conn.get_facts()
            click_echo(f"Added '{name}' and connectivity verified")
        except Exception as e:
            click_echo(f"Added '{name}' but connectivity test failed: {e}")
            sys.exit(1)
    else:
        click_echo(f"Added '{name}'")


@device.command()
@click.argument("path", required=False, default=None)
@click.pass_obj
def reload(ctx, path):
    """Reload device inventory from file.

    Optionally specify a new file path, otherwise re-reads the current inventory file.
    """
    try:
        old_count = ctx.inventory.reload(path)
        new_count = len(ctx.inventory.devices)
        click_echo(f"Reloaded: {old_count} -> {new_count} device(s)")
    except Exception as e:
        output_error(str(e), ctx.json_output)
        sys.exit(1)
