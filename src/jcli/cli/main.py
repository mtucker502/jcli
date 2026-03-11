import logging
import os
import sys

import click

from jcli import __version__
from jcli.device.inventory import DeviceInventory


class CliContext:
    def __init__(self, json_output=False, verbose=False, inventory_path=None, timeout=360):
        self.json_output = json_output
        self.verbose = verbose
        self.timeout = timeout
        self._inventory_path = inventory_path
        self._inventory = None

    @property
    def inventory(self):
        if self._inventory is None:
            self._inventory = DeviceInventory(self._inventory_path)
            self._inventory.load()
        return self._inventory


@click.group()
@click.option("--json", "-j", "json_output", is_flag=True, help="Output in JSON format.")
@click.option(
    "--inventory",
    "-f",
    "inventory_path",
    envvar="JCLI_INVENTORY",
    default="devices.json",
    help="Path to devices.json inventory file.",
)
@click.option(
    "--timeout",
    "-t",
    type=int,
    envvar="JCLI_TIMEOUT",
    default=360,
    help="Default command timeout in seconds.",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging.")
@click.version_option(version=__version__, prog_name="jcli")
@click.pass_context
def cli(ctx, json_output, inventory_path, timeout, verbose):
    """CLI tool for Juniper Junos device management."""
    ctx.ensure_object(dict)
    ctx.obj = CliContext(
        json_output=json_output,
        verbose=verbose,
        inventory_path=inventory_path,
        timeout=timeout,
    )
    if verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")
    else:
        logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")


# Import and register subcommand groups
from jcli.cli.commands.device import device  # noqa: E402
from jcli.cli.commands.command import command  # noqa: E402
from jcli.cli.commands.config import config  # noqa: E402

cli.add_command(device)
cli.add_command(command)
cli.add_command(config)
