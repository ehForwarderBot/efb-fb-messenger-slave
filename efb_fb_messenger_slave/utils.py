# coding=utf-8
import collections
import logging
from collections import deque
from logging import LogRecord
from typing import TYPE_CHECKING, Dict, Any, Hashable, Union, Sequence

if TYPE_CHECKING:
    from . import FBMessengerChannel

ThreadID = Union[str, int]


class ExperimentalFlagsManager:

    DEFAULT_VALUES = {
        'proxy_links_by_facebook': False,  # True then links with Facebook redirection
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


def get_value(source: Union[Dict, Sequence],
              path: Sequence[Hashable],
              default: Any = None) -> Any:
    """
    Get value from a path of keys

    Args:
        source: Data source
        path: Path to get value from
        default: Default value if the value is not found

    Returns:
        The value found or the default value.
    """

    data: Any = source
    stack = deque(path)
    while stack:
        key = stack.popleft()
        try:
            data = data.__getitem__(key)
        except (AttributeError, KeyError, IndexError, TypeError):
            return default
    return data


class PahoMQTTPingFilter(logging.Filter):

    blacklist = {"Sending PINGREQ", "Received PINGRESP"}

    def filter(self, record: LogRecord) -> int:
        if record.msg in self.blacklist:
            return 0
        return 1
