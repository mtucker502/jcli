"""Jinja2 template rendering with YAML variables."""
import logging
from pathlib import Path

import yaml
from jinja2 import Environment, TemplateError

log = logging.getLogger(__name__)


def render_template(template_path: str, vars_path: str) -> str:
    """Render a Jinja2 template file with YAML variables.

    Args:
        template_path: Path to Jinja2 template file
        vars_path: Path to YAML variables file

    Returns:
        Rendered configuration string

    Raises:
        FileNotFoundError: If template or vars file doesn't exist
        ValueError: If YAML parsing or template rendering fails
    """
    template_file = Path(template_path)
    vars_file = Path(vars_path)

    if not template_file.exists():
        raise FileNotFoundError(f"Template file not found: {template_path}")
    if not vars_file.exists():
        raise FileNotFoundError(f"Variables file not found: {vars_path}")

    # Load variables
    try:
        with open(vars_file) as f:
            variables = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing YAML variables: {e}") from e

    if not variables:
        raise ValueError("Variables file is empty or invalid")

    # Load and render template
    try:
        template_content = template_file.read_text()
        env = Environment(trim_blocks=True, lstrip_blocks=True, autoescape=False)
        template = env.from_string(template_content)
        return template.render(variables)
    except TemplateError as e:
        raise ValueError(f"Error rendering template: {e}") from e


def render_template_string(template_content: str, vars_content: str) -> str:
    """Render a Jinja2 template string with YAML variables string.

    Args:
        template_content: Jinja2 template as string
        vars_content: YAML variables as string

    Returns:
        Rendered configuration string
    """
    try:
        variables = yaml.safe_load(vars_content)
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing YAML variables: {e}") from e

    if not variables:
        raise ValueError("Variables content is empty or invalid")

    try:
        env = Environment(trim_blocks=True, lstrip_blocks=True, autoescape=False)
        template = env.from_string(template_content)
        return template.render(variables)
    except TemplateError as e:
        raise ValueError(f"Error rendering template: {e}") from e
