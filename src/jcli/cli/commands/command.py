"""Command execution: run, batch."""

import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import click

from jcli.output.formatter import (
    format_command_result,
    format_batch_results,
    format_multi_results,
    output_error,
    click_echo,
)


@click.group()
def command():
    """Execute Junos CLI commands on devices."""
    pass


@command.command()
@click.argument("router")
@click.argument("cmd")
@click.option("--timeout", "-t", type=int, default=None, help="Command timeout in seconds.")
@click.pass_obj
def run(ctx, router, cmd, timeout):
    """Execute a Junos CLI command on ROUTER.

    Example: jcli command run vsrx1 "show bgp summary"
    """
    from jcli.device.connection import JunosConnection
    from jcli.safety.blocklist import check_command_blocklist

    is_blocked, blocked_msg = check_command_blocklist(cmd)
    if is_blocked:
        output_error(blocked_msg, ctx.json_output)
        sys.exit(2)

    timeout = timeout or ctx.timeout
    try:
        device_info = ctx.inventory.get_device(router)
    except KeyError as e:
        output_error(str(e), ctx.json_output)
        sys.exit(1)
    start = time.time()
    try:
        conn = JunosConnection(device_info, router, timeout)
        result = conn.run_command(cmd)
    except Exception as e:
        output_error(str(e), ctx.json_output)
        sys.exit(1)
    duration = round(time.time() - start, 3)
    click_echo(format_command_result(router, cmd, result, duration, ctx.json_output))


@command.command()
@click.argument("router")
@click.argument("cmds", nargs=-1, required=True)
@click.option("--timeout", "-t", type=int, default=None, help="Command timeout in seconds.")
@click.option("--stop-on-error", is_flag=True, help="Stop on first command failure.")
@click.pass_obj
def multi(ctx, router, cmds, timeout, stop_on_error):
    """Run multiple commands on ROUTER in a single connection.

    Example: jcli command multi vsrx1 "show version" "show bgp summary" "show interfaces terse"
    """
    from jcli.device.connection import JunosConnection
    from jcli.safety.blocklist import check_command_blocklist

    # Pre-check all commands against blocklist before executing any
    for cmd in cmds:
        is_blocked, blocked_msg = check_command_blocklist(cmd)
        if is_blocked:
            output_error(blocked_msg, ctx.json_output)
            sys.exit(2)

    timeout = timeout or ctx.timeout
    try:
        device_info = ctx.inventory.get_device(router)
    except KeyError as e:
        output_error(str(e), ctx.json_output)
        sys.exit(1)

    try:
        conn = JunosConnection(device_info, router, timeout)
        results = conn.run_commands(list(cmds), stop_on_error=stop_on_error)
    except Exception as e:
        output_error(str(e), ctx.json_output)
        sys.exit(1)

    click_echo(format_multi_results(router, results, ctx.json_output))


@command.command()
@click.argument("cmd")
@click.argument("routers", nargs=-1, required=True)
@click.option("--timeout", "-t", type=int, default=None, help="Command timeout in seconds.")
@click.option("--parallel", "-p", type=int, default=5, help="Max concurrent connections.")
@click.pass_obj
def batch(ctx, cmd, routers, timeout, parallel):
    """Execute a command on multiple routers in parallel.

    Example: jcli command batch "show version" r1 r2 r3
    """
    from jcli.device.connection import JunosConnection
    from jcli.safety.blocklist import check_command_blocklist

    timeout = timeout or ctx.timeout

    is_blocked, blocked_msg = check_command_blocklist(cmd)
    if is_blocked:
        output_error(blocked_msg, ctx.json_output)
        sys.exit(2)

    # Validate all routers exist before executing
    device_infos = {}
    for router in routers:
        try:
            device_infos[router] = ctx.inventory.get_device(router)
        except KeyError as e:
            output_error(str(e), ctx.json_output)
            sys.exit(1)

    def execute_on_router(router_name):
        start = time.time()
        try:
            conn = JunosConnection(device_infos[router_name], router_name, timeout)
            output = conn.run_command(cmd)
            status = "success"
        except Exception as e:
            output = str(e)
            status = "failed"
        duration = round(time.time() - start, 3)
        return {
            "router": router_name,
            "status": status,
            "output": output,
            "duration": duration,
        }

    results = []
    with ThreadPoolExecutor(max_workers=parallel) as pool:
        futures = {pool.submit(execute_on_router, r): r for r in routers}
        for future in as_completed(futures):
            results.append(future.result())

    # Maintain original router order
    order = {r: i for i, r in enumerate(routers)}
    results.sort(key=lambda r: order[r["router"]])

    click_echo(format_batch_results(results, ctx.json_output))
