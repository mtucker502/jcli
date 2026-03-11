"""Device configuration validation and connection parameter utilities.

Ported from jmcp utils/config.py to maintain devices.json compatibility.
"""

import logging

log = logging.getLogger(__name__)


def validate_device_config(device_name: str, device_config: dict) -> None:
    required_fields = ["ip", "port", "username"]
    missing_fields = [f for f in required_fields if f not in device_config]

    if missing_fields:
        raise ValueError(
            f"Device '{device_name}' missing required fields: {', '.join(missing_fields)}. "
            f"Expected format: {{'ip': 'x.x.x.x', 'port': 22, 'username': 'user', 'auth': {{...}}}}"
        )

    if "auth" in device_config:
        auth_config = device_config["auth"]
        if "type" not in auth_config:
            raise ValueError(
                f"Device '{device_name}' has 'auth' section but missing 'type' field. "
                f"Expected 'type' to be either 'password' or 'ssh_key'"
            )

        if auth_config["type"] == "password":
            if "password" not in auth_config:
                raise ValueError(
                    f"Device '{device_name}' auth type is 'password' but 'password' field is missing"
                )
        elif auth_config["type"] == "ssh_key":
            if "private_key_path" not in auth_config:
                raise ValueError(
                    f"Device '{device_name}' auth type is 'ssh_key' "
                    f"but 'private_key_path' field is missing"
                )
        elif auth_config["type"] == "ssh_agent":
            pass  # No additional fields needed — uses SSH agent
        else:
            raise ValueError(
                f"Device '{device_name}' has unsupported auth type '{auth_config['type']}'. "
                f"Supported types are: 'password', 'ssh_key', 'ssh_agent'"
            )
    elif "password" not in device_config:
        raise ValueError(
            f"Device '{device_name}' missing authentication configuration. "
            f"Either provide 'auth' section or 'password' field (deprecated)"
        )

    if not isinstance(device_config.get("port"), int):
        raise ValueError(
            f"Device '{device_name}' has invalid 'port' value. "
            f"Expected integer, got {type(device_config.get('port')).__name__}"
        )

    log.debug(f"Device '{device_name}' configuration validated successfully")


def validate_all_devices(devices: dict) -> None:
    if not devices:
        log.warning("No devices configured")
        return

    errors = []
    for device_name, device_config in devices.items():
        try:
            validate_device_config(device_name, device_config)
        except ValueError as e:
            errors.append(str(e))

    if errors:
        error_msg = "Device configuration validation failed:\n" + "\n".join(
            f"  - {e}" for e in errors
        )
        raise ValueError(error_msg)

    log.info(f"All {len(devices)} device(s) validated successfully")


def prepare_connection_params(device_info: dict, router_name: str) -> dict:
    validate_device_config(router_name, device_info)

    connect_params = {
        "host": device_info["ip"],
        "port": device_info["port"],
        "user": device_info["username"],
        "gather_facts": False,
        "timeout": 360,
    }

    if "ssh_config" in device_info:
        connect_params["ssh_config"] = device_info["ssh_config"]

    if "auth" in device_info:
        auth_config = device_info["auth"]
        if auth_config["type"] == "password":
            connect_params["password"] = auth_config["password"]
        elif auth_config["type"] == "ssh_key":
            connect_params["ssh_private_key_file"] = auth_config["private_key_path"]
        elif auth_config["type"] == "ssh_agent":
            pass  # PyEZ picks up SSH agent automatically
        else:
            raise ValueError(f"Unsupported auth type '{auth_config['type']}' for {router_name}")
    elif "password" in device_info:
        connect_params["password"] = device_info["password"]
    else:
        raise ValueError(f"No valid authentication method found for {router_name}")

    return connect_params
