"""Configuration management: show, diff, load, template."""

import sys

import click

from jcli.output.formatter import output_error, click_echo


@click.group()
def config():
    """View and manage device configuration."""
    pass


@config.command()
@click.argument("router")
@click.argument("section", required=False, default=None)
@click.pass_obj
def show(ctx, router, section):
    """Show running configuration of ROUTER in set format.

    Optionally filter to a SECTION (e.g. "system services", "protocols bgp").
    """
    from jcli.device.connection import JunosConnection

    try:
        device_info = ctx.inventory.get_device(router)
    except KeyError as e:
        output_error(str(e), ctx.json_output)
        sys.exit(1)
    try:
        conn = JunosConnection(device_info, router, ctx.timeout)
        result = conn.get_config(section=section)
    except Exception as e:
        output_error(str(e), ctx.json_output)
        sys.exit(1)
    click_echo(result)


@config.command()
@click.argument("router")
@click.option(
    "--rollback", "-r", type=int, default=1,
    help="Rollback version to compare against (1-49).",
)
@click.pass_obj
def diff(ctx, router, rollback):
    """Show configuration diff against a rollback version on ROUTER."""
    from jcli.device.connection import JunosConnection

    if not 1 <= rollback <= 49:
        output_error("Rollback version must be between 1 and 49", ctx.json_output)
        sys.exit(1)
    try:
        device_info = ctx.inventory.get_device(router)
    except KeyError as e:
        output_error(str(e), ctx.json_output)
        sys.exit(1)
    try:
        conn = JunosConnection(device_info, router, ctx.timeout)
        result = conn.get_config_diff(rollback)
    except Exception as e:
        output_error(str(e), ctx.json_output)
        sys.exit(1)
    click_echo(result)


@config.command()
@click.argument("router")
@click.argument("config_text", required=False, default=None)
@click.option(
    "--format", "-F", "config_format", type=click.Choice(["set", "text", "xml"]),
    default="set", help="Configuration format.",
)
@click.option("--comment", "-c", default="Configuration loaded via jcli", help="Commit comment.")
@click.option("--stdin", "use_stdin", is_flag=True, help="Read config from stdin.")
@click.pass_obj
def load(ctx, router, config_text, config_format, comment, use_stdin):
    """Load configuration onto ROUTER and commit.

    Example: jcli config load vsrx1 "set system host-name new-name"
    """
    from jcli.device.config_ops import load_and_commit
    from jcli.safety.blocklist import check_config_blocklist

    if use_stdin:
        config_text = click.get_text_stream("stdin").read()
    elif config_text is None:
        output_error("Provide config text as argument or use --stdin", ctx.json_output)
        sys.exit(1)

    if not config_text.strip():
        output_error("Config text is empty", ctx.json_output)
        sys.exit(1)

    is_blocked, blocked_msg = check_config_blocklist(config_text)
    if is_blocked:
        output_error(blocked_msg, ctx.json_output)
        sys.exit(2)

    try:
        device_info = ctx.inventory.get_device(router)
    except KeyError as e:
        output_error(str(e), ctx.json_output)
        sys.exit(1)

    try:
        result = load_and_commit(
            device_info, router, config_text,
            config_format=config_format,
            commit_comment=comment,
            timeout=ctx.timeout,
        )
    except Exception as e:
        output_error(str(e), ctx.json_output)
        sys.exit(1)

    click_echo(result)


@config.command()
@click.option("--template", "-t", "template_path", required=True, help="Path to Jinja2 template file.")
@click.option("--vars", "-V", "vars_path", required=True, help="Path to YAML variables file.")
@click.option("--router", "-r", "routers", multiple=True, help="Target router(s). Repeatable.")
@click.option("--apply", "apply_config", is_flag=True, help="Apply rendered config to routers.")
@click.option("--dry-run", is_flag=True, help="Show diff without committing.")
@click.option("--comment", "-c", default="Configuration applied via jcli template", help="Commit comment.")
@click.option(
    "--format", "-F", "config_format", type=click.Choice(["set", "text", "xml"]),
    default="set", help="Configuration format.",
)
@click.pass_obj
def template(ctx, template_path, vars_path, routers, apply_config, dry_run, comment, config_format):
    """Render a Jinja2 template with YAML variables, optionally apply to routers.

    Example: jcli config template -t bgp.j2 -V site.yaml --router r1 --apply
    """
    from jcli.template.renderer import render_template
    from jcli.safety.blocklist import check_config_blocklist

    try:
        rendered = render_template(template_path, vars_path)
    except (FileNotFoundError, ValueError) as e:
        output_error(str(e), ctx.json_output)
        sys.exit(1)

    if not apply_config:
        click_echo(rendered)
        return

    if not routers:
        output_error("Provide --router when using --apply", ctx.json_output)
        sys.exit(1)

    is_blocked, blocked_msg = check_config_blocklist(rendered)
    if is_blocked:
        output_error(blocked_msg, ctx.json_output)
        sys.exit(2)

    from jcli.device.config_ops import load_and_commit

    for router in routers:
        try:
            device_info = ctx.inventory.get_device(router)
        except KeyError as e:
            output_error(str(e), ctx.json_output)
            continue

        if dry_run:
            click_echo(f"=== {router} (dry-run) ===")
            click_echo(rendered)
            click_echo("")
            continue

        try:
            result = load_and_commit(
                device_info, router, rendered,
                config_format=config_format,
                commit_comment=comment,
                timeout=ctx.timeout,
            )
            click_echo(f"=== {router} ===")
            click_echo(result)
            click_echo("")
        except Exception as e:
            output_error(f"{router}: {e}", ctx.json_output)
