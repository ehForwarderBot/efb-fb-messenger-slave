# coding=utf-8

import logging
from typing import TYPE_CHECKING, Dict, Any
from ehforwarderbot import EFBChat, ChatType
from fbchat.models import Thread, User, Page, Group, Room

from .utils import get_value

if TYPE_CHECKING:
    from . import FBMessengerChannel
    from .efms_client import EFMSClient


class EFMSChat(EFBChat):

    logger = logging.getLogger("EFMSChat")

    cache = dict()

    def __init__(self, channel: 'FBMessengerChannel', thread: Thread=None,
                 graph_ql_thread: Dict[str, Any]=None,
                 uid: str=None, lazy_load=False):
        """
        Create a chat based on fbchat Thread objects or GraphQL result dict.

        Args:
            channel: The EFMS channel object
            thread: fbchat Thread object as information source
            graph_ql_thread: GraphQL thread as information source
            uid: Thread ID, and retrieve necessary details from server
            lazy_load: If chat info need to be loaded later
        """
        super().__init__(channel)
        self.channel = channel
        self.thread = thread
        self.chat_uid = uid
        self.client: EFMSClient = channel.client
        self.loaded = False
        self.graph_ql_thread = graph_ql_thread

        # Mark shelf
        if self.chat_uid == self.client.uid:
            self.self()
            return
        if not lazy_load:
            self.load_chat()

    def load_chat(self):
        self.loaded = True

        thread: Thread = self.thread

        if self.is_self:
            return

        if self.graph_ql_thread:
            return self.load_graph_ql_thread()

        if not thread:
            if self.chat_uid in EFMSChat.cache:
                self.clone(EFMSChat.cache[self.chat_uid])
                return
            thread = self.client.fetchThreadInfo(self.chat_uid)[str(self.chat_uid)]
            self.thread = thread

        self.logger.debug("Parsing fbchat thread object: %s", thread)

        self.chat_uid = thread.uid
        self.chat_name = thread.name
        self.vendor_specific['chat_type'] = thread.type.name.capitalize()

        if self.chat_uid == self.client.uid:
            self.self()
            EFMSChat.cache[self.chat_uid] = self
            return

        if isinstance(thread, User):
            self.chat_type = ChatType.User
            self.chat_alias = thread.own_nickname or thread.nickname
        elif isinstance(thread, Page):
            self.chat_type = ChatType.User
        elif isinstance(thread, Group) or isinstance(thread, Room):
            self.chat_type = ChatType.Group

            # Lazy load if the group has a name,
            # otherwise members' names are needed to build group name

            lazy_load = bool(self.chat_name)
            names = []

            if self.is_chat:
                for i in thread.participants:
                    member = EFMSChat(self.channel, uid=i, lazy_load=lazy_load)
                    if thread.nicknames and i in thread.nicknames:
                        member.chat_alias = thread.nicknames[str(i)]
                    if not lazy_load:
                        names.append(member.chat_alias or member.chat_name)
                    member.is_chat = False
                    self.members.append(member)

            if not lazy_load:
                if names:
                    names.sort()
                    self.chat_name = ", ".join(names[:3])
                    if len(names) > 3:
                        self.chat_name += ", and %d more" % (len(names) - 3)
                else:
                    self.chat_name = "Group %s" % self.chat_uid
        else:
            self.chat_type = ChatType.System
        EFMSChat.cache[self.chat_uid] = self

    def load_graph_ql_thread(self, recursive=True):
        self.logger.debug('Parsing chat as GraphQL dict: %s', self.graph_ql_thread)

        if 'thread_key' in self.graph_ql_thread:
            # Data of a thread
            self.logger.debug('GraphQL information provided is a thread.')
            self.chat_name = self.graph_ql_thread['name']
            if self.graph_ql_thread['thread_type'] == 'ONE_TO_ONE':
                self.chat_type = ChatType.User
                self.chat_uid = self.graph_ql_thread['thread_key']['other_user_id']
                item = None
                for i in self.graph_ql_thread['all_participants']['nodes']:
                    if i['messaging_actor']['id'] == self.chat_uid:
                        item = i['messaging_actor']
                        break
                self.logger.debug("[%s] One to one member info: %s", self.chat_uid, item)
                if item:
                    self.chat_name = self.chat_name or item['name']
                    self.vendor_specific['profile_picture_url'] = item['big_image_src']['uri']
                    self.vendor_specific['chat_type'] = item.get('__typename')
            elif self.graph_ql_thread['thread_type'] == 'GROUP':
                self.chat_type = ChatType.Group
                self.chat_uid = self.graph_ql_thread['thread_key']['thread_fbid']
                self.vendor_specific['chat_type'] = 'Group'
                self.vendor_specific['profile_picture_url'] = \
                    get_value(self.graph_ql_thread, ('image', 'uri'))
                for i in self.graph_ql_thread['all_participants']['nodes']:
                    self.members.append(EFMSChat(self.channel,
                                                 graph_ql_thread=i,
                                                 lazy_load='name' in i['messaging_actor']))
                    self.members[-1].group = self
                    self.members[-1].is_chat = False
                if not self.chat_name:
                    names = sorted(i.chat_name for i in self.members)
                    self.chat_name = ", ".join(names[:3])
                    if len(names) > 3:
                        self.chat_name += ", and %s more" % (len(names) - 3)
        elif 'messaging_actor' in self.graph_ql_thread:
            self.logger.debug('GraphQL information provided is a thread member.')
            # data of a group member
            self.chat_uid = self.graph_ql_thread['messaging_actor']['id']
            if 'name' in self.graph_ql_thread['messaging_actor']:
                self.logger.debug('[%s] Thread member information is complete.', self.chat_uid)
                self.chat_name = self.graph_ql_thread['messaging_actor']['name']
                self.chat_type = ChatType.User
                self.vendor_specific['chat_type'] = self.graph_ql_thread['messaging_actor'].get('__typename')
                self.vendor_specific['profile_picture_url'] = \
                    get_value(self.graph_ql_thread, ('messaging_actor', 'big_image_src', 'uri'))
            elif recursive:
                self.logger.debug('[%s] Thread member information is incomplete.', self.chat_uid)
                self.graph_ql_thread = self.client.get_thread_info(self.chcat_uid)
                return self.load_graph_ql_thread(recursive=False)

        if self.chat_uid == self.client.uid:
            self.self()

        EFMSChat.cache[self.chat_uid] = self

    def clone(self, other: 'EFMSChat'):
        self.__dict__.update(**other.__dict__)

    def __getattribute__(self, item):
        if item in {"chat_name", "chat_alias", "members", "chat_type"} and not self.loaded:
            self.load_chat()
        return super().__getattribute__(item)
