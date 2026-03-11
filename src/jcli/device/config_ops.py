"""Configuration operations -- load and commit with safety."""
import logging

from jnpr.junos import Device
from jnpr.junos.exception import CommitError, ConfigLoadError, ConnectError, LockError
from jnpr.junos.utils.config import Config

from jcli.device.config import prepare_connection_params

log = logging.getLogger(__name__)


def load_and_commit(
    device_info: dict,
    router_name: str,
    config_text: str,
    config_format: str = "set",
    commit_comment: str = "Configuration loaded via jcli",
    timeout: int = 360,
) -> str:
    """Load configuration and commit with safety (lock/check/rollback pattern).

    Returns result message string.
    Raises ConnectionError on connection failure, ValueError on config errors.
    """
    connect_params = prepare_connection_params(device_info, router_name)

    try:
        with Device(**connect_params) as dev:
            dev.timeout = timeout
            config_util = Config(dev)

            try:
                config_util.lock()
            except LockError as e:
                raise ValueError(f"Failed to lock configuration: {e}") from e

            try:
                config_util.load(config_text, format=config_format)

                diff = config_util.diff()
                if not diff:
                    config_util.unlock()
                    return "No configuration changes detected"

                config_util.commit(comment=commit_comment, timeout=timeout)
                config_util.unlock()
                return f"Configuration committed on {router_name}. Changes:\n{diff}"

            except (ConfigLoadError, CommitError) as e:
                try:
                    config_util.rollback()
                    config_util.unlock()
                except Exception:
                    pass
                raise ValueError(f"Failed to load/commit configuration: {e}") from e
            except Exception as e:
                try:
                    config_util.rollback()
                    config_util.unlock()
                except Exception:
                    pass
                raise

    except ConnectError as ce:
        raise ConnectionError(f"Connection error to {router_name}: {ce}") from ce
