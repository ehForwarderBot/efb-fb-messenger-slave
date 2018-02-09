# coding=utf-8

from typing import TYPE_CHECKING, Dict, Any, Hashable, Tuple, Union, Iterable

if TYPE_CHECKING:
    from . import FBMessengerChannel


class ExperimentalFlagsManager:

    DEFAULT_VALUES = {
        'proxy_links_by_facebook': True,  # True then links are proxied by facebook
        'send_link_with_description': False,  # Send link messages with descriptions
        'show_pending_threads': False,  # Show threads pending approval in the thread list
        'show_archived_threads': False,  # Show archived threads in the thread list
    }

    def __init__(self, channel: 'FBMessengerChannel'):
        self.config: Dict[str, Any] = ExperimentalFlagsManager.DEFAULT_VALUES.copy()
        self.config.update(channel.config.get('flags', dict()))

    def __call__(self, flag_key: str) -> Any:
        if flag_key not in self.config:
            raise ValueError("%s is not a valid experimental flag" % flag_key)
        return self.config[flag_key]


def get_value(source: Union[dict, Iterable], path: Tuple[Hashable, ...], default=None) -> Any:
    """
    Get value from a path of keys
    Args:
        source: Data source
        path: Path to get value from
        default: Default value if the value is not found

    Returns:
        The value found or the default value.
    """

    data = source
    stack = path
    while stack:
        key = stack[0]
        stack = stack[1:]
        try:
            data = data.__getitem__(key)
        except (AttributeError, KeyError, IndexError, TypeError):
            return default
    return data
