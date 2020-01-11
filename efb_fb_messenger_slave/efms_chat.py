# coding=utf-8

import logging
from typing import TYPE_CHECKING, Dict, Any, Optional, Tuple, Union

from fbchat import FBchatException

from ehforwarderbot import Chat, coordinator
from fbchat.models import Thread, User, Page, Group, Room

from ehforwarderbot.chat import PrivateChat, GroupChat, SystemChat
from ehforwarderbot.types import ChatID
from .utils import get_value, ThreadID

if TYPE_CHECKING:
    from . import FBMessengerChannel
    from .efms_client import EFMSClient


class EFMSChat(Chat):
    logger = logging.getLogger("EFMSChat")

    cache: Dict[Tuple[str, Optional[str]], 'EFMSChat'] = dict()

    def __init__(self, channel: 'FBMessengerChannel', thread: Thread = None,
                 graph_ql_thread: Dict[str, Any] = None,
                 uid: ChatID = None, lazy_load=False, parent: Optional['EFMSChat'] = None):
        """
        Create a chat based on fbchat Thread objects or GraphQL result dict.

        Args:
            channel: The EFMS channel object
            thread: fbchat Thread object as information source
            graph_ql_thread: GraphQL thread as information source
            uid: Thread ID, and retrieve necessary details from server
            lazy_load: If chat info need to be loaded later
        """
        super().__init__()
        self.channel = channel
        self.thread = thread
        if uid is not None:
            self.chat_uid = uid
        self.client: EFMSClient = channel.client
        self.loaded = False
        self.graph_ql_thread = graph_ql_thread
        self.parent = parent

        if not lazy_load:
            self.load_chat()

    def load_graph_ql_thread(self, recursive=True):
        self.logger.debug('Parsing chat as GraphQL dict: %s', self.graph_ql_thread)

        if 'thread_key' in self.graph_ql_thread:
            # Data of a thread
            self.logger.debug('GraphQL information provided is a thread.')
            self.chat_name = self.graph_ql_thread['name']
            if self.graph_ql_thread['thread_type'] == 'ONE_TO_ONE':
                # self.chat_type = ChatType.User
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
            elif self.graph_ql_thread['thread_type'] == 'MARKETPLACE':
                # Data of a marketplace thread
                # self.chat_type = ChatType.Group
                self.chat_uid = self.graph_ql_thread['thread_key']['thread_fbid']
                for i in self.graph_ql_thread['all_participants']['nodes']:
                    self.members.append(EFMSChat(self.channel,
                                                 graph_ql_thread=i,
                                                 lazy_load='name' in i['messaging_actor']))
                    self.members[-1].group = self
                    self.members[-1].is_chat = False
                    self.members[-1].has_self = False
                self.vendor_specific['chat_type'] = 'Marketplace'
                if 'marketplace_thread_data' in self.graph_ql_thread:
                    self.vendor_specific['marketplace_thread_data'] = self.graph_ql_thread['marketplace_thread_data']
                    item_picture = self.graph_ql_thread['marketplace_thread_data'] \
                        .get("for_sale_item", {}).get("primary_photo", {}) \
                        .get("image", {}).get("url", None)
                    if item_picture:
                        self.vendor_specific['profile_picture_url'] = item_picture

            elif self.graph_ql_thread['thread_type'] == 'GROUP':
                # self.chat_type = ChatType.Group
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
                # self.chat_type = ChatType.User
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

    def __getstate__(self):
        state = self.__dict__.copy()

        # Convert channel object to channel ID
        if state['channel'] is not None:
            state['channel'] = state['channel'].channel_id
        return state

    def __setstate__(self, state: Dict[str, Any]):
        # Try to load channel object
        try:
            state['channel'] = coordinator.get_module_by_id(state['channel'])
        except NameError:
            del state['channel']

        self.__dict__.update(state)


class EFMSChatManager:
    logger = logging.getLogger("EFMSChatManager")

    cache: Dict[Union[ChatID, ThreadID], Chat] = dict()

    def __init__(self, channel: 'FBMessengerChannel'):
        self.channel: 'FBMessengerChannel' = channel
        self.client = self.channel.client
        self._ = self.channel._
        self.ngettext = self.channel.ngettext
        self.get_thread(self.client.uid)

    def get_thread(self, thread_id: ThreadID) -> Chat:
        if thread_id not in self.cache:
            chat = self.build_chat_by_thread_id(thread_id)
            self.cache[thread_id] = chat
        return self.cache[thread_id]

    def build_chat_by_thread_id(self, thread_id: ThreadID) -> Chat:
        thread: Thread = self.client.fetchThreadInfo(thread_id)[thread_id]
        return self.build_chat_by_thread_obj(thread)

    def build_and_cache_thread(self, thread: Thread) -> Chat:
        chat = self.build_chat_by_thread_obj(thread)
        self.cache[chat.id] = chat
        return chat

    def build_chat_by_thread_obj(self, thread: Thread) -> Chat:
        vendor_specific = {
            "chat_type": thread.type.name.capitalize(),
            "profile_picture_url": thread.photo,
        }
        chat: Chat
        if thread.uid == self.client.uid:
            chat = PrivateChat(channel=self.channel, id=thread.uid, other_is_self=True)
            chat.name = chat.self.name  # type: ignore
        elif isinstance(thread, User):
            chat = PrivateChat(channel=self.channel,
                               name=thread.name,
                               id=ChatID(thread.uid),
                               alias=thread.own_nickname or thread.nickname,
                               vendor_specific=vendor_specific)
        elif isinstance(thread, Page):
            desc = self._("{subtitle}\n{category} in {city}\n"
                          "Likes: {likes}\n{url}").format(
                subtitle=thread.sub_title, category=thread.category,
                city=thread.city, likes=thread.likes, url=thread.url
            )
            chat = PrivateChat(channel=self.channel,
                               name=thread.name,
                               id=ChatID(thread.uid),
                               description=desc,
                               vendor_specific=vendor_specific)
        elif isinstance(thread, Group):
            name = thread.name or ""

            group = GroupChat(channel=self.channel,
                              name=name,
                              id=ChatID(thread.uid),
                              vendor_specific=vendor_specific)
            participant_ids = thread.participants - {self.client.uid}
            try:
                participants: Dict[ThreadID, User] = self.client.fetchThreadInfo(*participant_ids)
                for i in participant_ids:
                    member = participants[i]
                    alias = member.own_nickname or member.nickname or None
                    if thread.nicknames and i in thread.nicknames:
                        alias = thread.nicknames[str(i)] or None
                    group.add_member(name=member.name, alias=alias, id=ChatID(i))
            except FBchatException:
                self.logger.exception("Error occurred while building chat members.")
                for i in participant_ids:
                    group.add_member(name=str(i), id=ChatID(i))

            if thread.name is None:
                names = sorted(i.name for i in group.members)
                # TRANSLATORS: separation symbol between member names when group name is not provided.
                name = self._(", ").join(names[:3])
                if len(names) > 3:
                    extras = len(names) - 3
                    name += self.ngettext(", and {number} more",
                                          ", and {number} more",
                                          extras).format(number=extras)
                group.name = name

            chat = group
        else:
            chat = SystemChat(channel=self.channel,
                              name=thread.name,
                              id=ChatID(thread.uid),
                              vendor_specific=vendor_specific)
        if chat.self:
            chat.self.id = self.client.uid
        return chat
