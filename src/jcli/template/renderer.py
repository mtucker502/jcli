"""Jinja2 template rendering with YAML variables."""
import logging
from pathlib import Path

import yaml
from jinja2 import TemplateError
from jinja2.sandbox import SandboxedEnvironment

log = logging.getLogger(__name__)

ALLOWED_TEMPLATE_EXTENSIONS = {".j2", ".jinja", ".jinja2", ".txt", ".conf", ".cfg", ".set"}
ALLOWED_VARS_EXTENSIONS = {".yaml", ".yml", ".json"}


def _validate_file_path(file_path: Path, allowed_extensions: set[str], label: str) -> Path:
    """Validate and resolve a file path for safe reading.

    Resolves the path to eliminate traversal (e.g. '../../../etc/passwd'),
    verifies it is a regular file with an expected extension.

    Raises:
        FileNotFoundError: If the file doesn't exist
        ValueError: If the path is not a regular file or has a disallowed extension
    """
    resolved = file_path.resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"{label} not found: {file_path}")
    if not resolved.is_file():
        raise ValueError(f"{label} is not a regular file: {file_path}")
    if resolved.suffix.lower() not in allowed_extensions:
        raise ValueError(
            f"{label} has unsupported extension '{resolved.suffix}'"
            f" (allowed: {', '.join(sorted(allowed_extensions))})"
        )
    return resolved


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
    template_file = _validate_file_path(
        Path(template_path), ALLOWED_TEMPLATE_EXTENSIONS, "Template file"
    )
    vars_file = _validate_file_path(
        Path(vars_path), ALLOWED_VARS_EXTENSIONS, "Variables file"
    )

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
        env = SandboxedEnvironment(trim_blocks=True, lstrip_blocks=True, autoescape=False)
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
        env = SandboxedEnvironment(trim_blocks=True, lstrip_blocks=True, autoescape=False)
        template = env.from_string(template_content)
        return template.render(variables)
    except TemplateError as e:
        raise ValueError(f"Error rendering template: {e}") from e
