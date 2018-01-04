from typing import TYPE_CHECKING
from ehforwarderbot import EFBChat, ChatType
from fbchat.models import Thread, User, Page, Group, Room

if TYPE_CHECKING:
    from . import FBMessengerChannel
    from .efms_client import EFMSClient


class EFMSChat(EFBChat):

    def __init__(self, channel: 'FBMessengerChannel', thread: Thread=None, uid: int=None, lazy_load=False):
        super().__init__(channel)
        self.channel = channel
        self.thread = thread
        self.chat_uid = uid
        self.client: EFMSClient = channel.client
        self.loaded = False
        if self.chat_uid == self.client.get_my_id():
            self.self()
            return
        if not lazy_load:
            self.load_chat()

    def load_chat(self):
        self.loaded = True
        thread = self.thread
        if not thread:
            thread = self.client.fetchThreadInfo(self.chat_uid)[str(self.chat_uid)]
            self.thread = thread
        self.chat_uid = thread.uid

        if self.chat_uid == self.client.get_my_id():
            self.self()
            return

        self.chat_name = thread.name
        if isinstance(thread, User):
            self.chat_type = ChatType.User
            self.chat_alias = thread.own_nickname or thread.nickname
        elif isinstance(thread, Page):
            self.chat_type = ChatType.User
        elif isinstance(thread, Group) or isinstance(thread, Room):
            self.chat_type = ChatType.Group
            if self.is_chat:
                for i in thread.participants:
                    member = EFMSChat(self.channel, uid=i, lazy_load=True)
                    member.is_chat = False
                    self.members.append(member)
        else:
            self.chat_type = ChatType.System

    def __getattribute__(self, item):
        if item in {"chat_name", "chat_alias", "members", "chat_type"} and not self.loaded:
            self.load_chat()
        return super().__getattribute__(item)
