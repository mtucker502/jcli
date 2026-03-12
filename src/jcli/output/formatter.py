"""Output formatting — plain text (default) and JSON modes."""

import json
import sys


def output(data, json_mode=False):
    """Write data to stdout. In JSON mode, serialize as JSON."""
    if json_mode:
        if isinstance(data, str):
            click_echo(data)
        else:
            click_echo(json.dumps(data, indent=2, default=_json_serializer))
    else:
        if isinstance(data, dict):
            for key, value in data.items():
                click_echo(f"{key}: {value}")
        elif isinstance(data, list):
            for item in data:
                click_echo(str(item))
        else:
            click_echo(str(data))


def output_error(message, json_mode=False):
    """Write error to stderr."""
    if json_mode:
        err = json.dumps({"error": message})
        sys.stderr.write(err + "\n")
    else:
        sys.stderr.write(f"Error: {message}\n")


def format_command_result(router, command, output_text, duration=None, json_mode=False):
    if json_mode:
        result = {"router": router, "command": command, "output": output_text}
        if duration is not None:
            result["duration"] = duration
        return json.dumps(result, indent=2)
    return output_text


def format_batch_results(results, json_mode=False):
    if json_mode:
        return json.dumps({"results": results}, indent=2, default=_json_serializer)
    lines = []
    for r in results:
        lines.append(f"=== {r['router']} ===")
        lines.append(r["output"])
        lines.append("")
    return "\n".join(lines)


def format_multi_results(router, results, json_mode=False):
    if json_mode:
        return json.dumps(
            {"router": router, "results": results},
            indent=2,
            default=_json_serializer,
        )
    lines = []
    for r in results:
        lines.append(f"=== {r['command']} ===")
        lines.append(r["output"])
        lines.append("")
    return "\n".join(lines)


def format_device_list(routers, json_mode=False):
    if json_mode:
        return json.dumps({"routers": routers}, indent=2)
    return "\n".join(routers)


def format_facts(router, facts, json_mode=False):
    if json_mode:
        return json.dumps(
            {"router": router, "facts": facts}, indent=2, default=_json_serializer
        )
    lines = []
    for key, value in facts.items():
        lines.append(f"{key}: {value}")
    return "\n".join(lines)


def click_echo(message):
    """Write to stdout via click if available, otherwise print."""
    try:
        import click

        click.echo(message)
    except ImportError:
        print(message)


def _json_serializer(obj):
    if hasattr(obj, "_asdict"):
        return obj._asdict()
    elif hasattr(obj, "__dict__"):
        return obj.__dict__
    else:
        return str(obj)
