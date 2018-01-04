import os
import pickle
from io import BytesIO
from typing import Optional, List, IO, Set, Dict, Any

import requests
import yaml
from fbchat import FBchatUserError
from fbchat.models import Thread
from ehforwarderbot import EFBChannel, EFBChat, EFBMsg, EFBStatus, ChannelType, MsgType
from ehforwarderbot import utils as efb_utils
from ehforwarderbot.status import EFBMessageRemoval
from ehforwarderbot.exceptions import EFBException, EFBOperationNotSupported

from .__version__ import __version__ as version
from .efms_chat import EFMSChat
from .efms_client import EFMSClient
from .master_messages import MasterMessageManager
from . import utils as efms_utils
from .utils import ExperimentalFlagsManager


class FBMessengerChannel(EFBChannel):
    channel_name: str = "EFB Facebook Messenger Slave"
    channel_emoji: str = "⚡️"
    channel_type: ChannelType = ChannelType.Slave
    __version__: str = version

    client: EFMSClient = None
    config: Dict[str, Any] = None

    def __init__(self):
        session_path = os.path.join(efb_utils.get_data_path(FBMessengerChannel.channel_id), "session.pickle")
        try:
            data = pickle.load(session_path)
            self.client = EFMSClient(None, None, session_cookies=data)
            self.client.channel = self
        except FBchatUserError as e:
            message = str(e) + "\n" + \
                "You may need to re-authorize your account.\n" + \
                "To do so, run:" + \
                "     python3 -m " + self.__module__
            raise EFBException(message)

        self.load_config()
        self.flag: ExperimentalFlagsManager = ExperimentalFlagsManager(self)
        self.master_message: MasterMessageManager = MasterMessageManager(self)

        # Monkey patching
        Thread.__eq__ = lambda a, b: a.uid == b.uid

    def load_config(self):
        """
        Load configuration from path specified by the framework.

        Configuration file is in YAML format.
        """
        config_path = efb_utils.get_config_path(self.channel_id)
        if not os.path.exists(config_path):
            return
        with open(config_path) as f:
            self.config: Dict[str, Any] = yaml.load(f)

    def get_chats(self) -> List[EFBChat]:
        chats = self.client.fetchThreadList()
        for i in self.client.fetchAllUsers():
            if i not in chats:
                chats.append(i)
            return list(map(lambda thread: EFMSChat(self, thread=thread), chats))

    def get_chat(self, chat_uid: str, member_uid: Optional[str] = None) -> EFBChat:
        thread_id = member_uid or chat_uid
        thread = self.client.fetchThreadInfo(thread_id)[str(thread_id)]
        chat = EFMSChat(self, thread=thread)
        if member_uid:
            chat.is_chat = False
        return chat

    def send_message(self, msg: EFBMsg) -> EFBMsg:
        return self.master_message.send_message(msg)

    def send_status(self, status: EFBStatus):
        if isinstance(status, EFBMessageRemoval):
            raise EFBOperationNotSupported("Messages cannot be removed in Facebook Messenger.")
        # Other status types go here
        raise EFBOperationNotSupported()

    def poll(self):
        self.client.listen()

    def stop_polling(self):
        self.client.listening = False

    def get_chat_picture(self, chat: EFBChat) -> IO[bytes]:
        thread = self.client.fetchThreadInfo(chat.chat_uid)[chat.chat_uid]
        photo_url = getattr(thread, 'photo', None)
        if not photo_url:
            raise EFBOperationNotSupported()
        photo = BytesIO(requests.get(photo_url).content)
        photo.seek(0)
        return photo
