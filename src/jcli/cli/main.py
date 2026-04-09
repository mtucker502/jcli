import logging
import os
import shutil
import sys
from pathlib import Path

import click

from jcli import __version__
from jcli.device.inventory import DeviceInventory


def _install_skill(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    # parents: main.py -> cli/ -> jcli/ -> src/ -> repo root
    src = Path(__file__).resolve().parents[3] / "skills" / "SKILL.md"
    if not src.exists():
        # Fall back to installed package data
        import importlib.resources

        ref = importlib.resources.files("jcli").joinpath("skills/SKILL.md")
        src = Path(str(ref))
    if not src.exists():
        click.echo("Error: skill file not found.", err=True)
        ctx.exit(1)
    dest_dir = Path.home() / ".claude" / "skills" / "jcli"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / "SKILL.md"
    shutil.copy2(src, dest)
    click.echo(f"Installed jcli skill to {dest}")
    ctx.exit(0)


def _uninstall_skill(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    skill_dir = Path.home() / ".claude" / "skills" / "jcli"
    if not skill_dir.exists():
        click.echo("jcli skill is not installed.", err=True)
        ctx.exit(1)
    shutil.rmtree(skill_dir)
    click.echo(f"Uninstalled jcli skill from {skill_dir}")
    ctx.exit(0)


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
    default=None,
    help="Path to devices.json inventory file. Defaults to ./devices.json or ~/.config/jcli/devices.json.",
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
@click.option(
    "--install-skill",
    is_flag=True,
    is_eager=True,
    expose_value=False,
    callback=_install_skill,
    help="Install the jcli Claude Code skill to ~/.claude/skills/.",
)
@click.option(
    "--uninstall-skill",
    is_flag=True,
    is_eager=True,
    expose_value=False,
    callback=_uninstall_skill,
    help="Uninstall the jcli Claude Code skill from ~/.claude/skills/.",
)
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
