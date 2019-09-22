# coding=utf-8

import logging
import pickle
from gettext import translation
from io import BytesIO
from typing import Optional, List, IO, Dict, Any, Tuple

import requests
import yaml
from fbchat import FBchatUserError, ThreadLocation, MessageReaction, FBchatException, Message
from fbchat.models import Thread
from pkg_resources import resource_filename

from ehforwarderbot import EFBChannel, EFBChat, EFBMsg, EFBStatus, ChannelType
from ehforwarderbot import utils as efb_utils
from ehforwarderbot.exceptions import EFBException, EFBOperationNotSupported, EFBMessageReactionNotPossible
from ehforwarderbot.status import EFBMessageRemoval, EFBReactToMessage
from ehforwarderbot.types import ChatID, MessageID, ModuleID, InstanceID
from ehforwarderbot.utils import extra
from . import utils as efms_utils
from .__version__ import __version__
from .efms_chat import EFMSChat
from .efms_client import EFMSClient
from .extra_functions import ExtraFunctionsManager
from .master_messages import MasterMessageManager
from .utils import ExperimentalFlagsManager


class FBMessengerChannel(EFBChannel):
    channel_name: str = "Facebook Messenger Slave"
    channel_emoji: str = "⚡️"
    channel_id: ModuleID = ModuleID("blueset.fbmessenger")
    channel_type: ChannelType = ChannelType.Slave
    __version__: str = __version__

    client: EFMSClient
    config: Dict[str, Any] = {}

    logger = logging.getLogger(channel_id)

    suggested_reactions = [MessageReaction.LOVE.value,
                           MessageReaction.SMILE.value,
                           MessageReaction.WOW.value,
                           MessageReaction.SAD.value,
                           MessageReaction.ANGRY.value,
                           MessageReaction.YES.value,
                           MessageReaction.NO.value]

    # Translator
    translator = translation("efb_fb_messenger_slave",
                             resource_filename("efb_fb_messenger_slave", 'locale'),
                             fallback=True)

    _ = translator.gettext  # type: ignore
    ngettext = translator.ngettext  # type: ignore

    def __init__(self, instance_id: InstanceID = None):
        super().__init__(instance_id)
        session_path = efb_utils.get_data_path(self.channel_id) / "session.pickle"
        try:
            data = pickle.load(session_path.open('rb'))
            self.client = EFMSClient(self, None, None, session_cookies=data)
            EFMSChat.cache[EFBChat.SELF_ID] = EFMSChat(self,
                                                       self.client.fetchThreadInfo(self.client.uid)[self.client.uid])
        except FileNotFoundError:
            raise EFBException(self._("Session not found, please authorize your account.\n"
                                      "To do so, run: efms-auth"))
        except FBchatUserError as e:
            message = str(e) + "\n" + \
                      self._("You may need to re-authorize your account.\n" +
                             "To do so, run: efms-auth")
            raise EFBException(message)

        self.load_config()
        self.flag: ExperimentalFlagsManager = ExperimentalFlagsManager(self)
        self.master_message: MasterMessageManager = MasterMessageManager(self)
        self.extra_functions: ExtraFunctionsManager = ExtraFunctionsManager(self)

        # Initialize list of chat from server
        self.get_chats()

        # Monkey patching
        Thread.__eq__ = lambda a, b: a.uid == b.uid

    def load_config(self):
        """
        Load configuration from path specified by the framework.

        Configuration file is in YAML format.
        """
        config_path = efb_utils.get_config_path(self.channel_id)
        if not config_path.exists():
            self.config: Dict[str, Any] = dict()
            return
        with config_path.open() as f:
            self.config: Dict[str, Any] = yaml.load(f) or dict()

    def get_chats(self) -> List[EFBChat]:
        locations: Tuple[ThreadLocation, ...] = (ThreadLocation.INBOX,)
        if self.flag('show_pending_threads'):
            locations += (ThreadLocation.PENDING, ThreadLocation.OTHER)
        if self.flag('show_archived_threads'):
            locations += (ThreadLocation.ARCHIVED,)
        chats: List[EFBChat] = list(map(lambda graphql: EFMSChat(self, graph_ql_thread=graphql),
                                        self.client.get_thread_list(location_obj=locations)))
        loaded_chats = set(i.chat_uid for i in chats)
        for i in self.client.fetchAllUsers():
            if i.uid not in loaded_chats:
                chats.append(EFMSChat(self, thread=i))

        return chats

    def get_chat(self, chat_uid: str, member_uid: Optional[str] = None) -> EFMSChat:
        thread_id = member_uid or chat_uid
        if thread_id in EFMSChat.cache:
            chat = EFMSChat.cache[thread_id]
        else:
            # thread = self.client.fetchThreadInfo(thread_id)[str(thread_id)]
            # chat = EFMSChat(self, thread=thread)
            graph_ql = self.client.get_thread_info(thread_id)
            chat = EFMSChat(self, graph_ql_thread=graph_ql)
        if member_uid:
            chat.is_chat = False
            chat.group = self.get_chat(chat_uid)
        return chat

    def send_message(self, msg: EFBMsg) -> EFBMsg:
        return self.master_message.send_message(msg)

    def send_status(self, status: EFBStatus):
        if isinstance(status, EFBMessageRemoval):
            return self.client.unsend(status.message.uid)
        elif isinstance(status, EFBReactToMessage):
            try:
                self.client.reactToMessage(status.msg_id, status.reaction and MessageReaction(status.reaction))
            except (FBchatException, ValueError) as e:
                self.logger.error(f"Error occurred while sending status: {e}")
                raise EFBMessageReactionNotPossible(*e.args)
            return
        # Other status types go here
        raise EFBOperationNotSupported()

    def poll(self):
        self.client.listen(False)

    def stop_polling(self):
        self.client.listening = False

    def get_chat_picture(self, chat: EFBChat) -> IO[bytes]:
        self.logger.debug("Getting picture of chat %s", chat)
        photo_url = EFMSChat.cache[chat.chat_uid] and \
                    EFMSChat.cache[chat.chat_uid].vendor_specific.get('profile_picture_url')
        self.logger.debug("[%s] has photo_url from cache: %s", chat.chat_uid, photo_url)
        if not photo_url:
            thread = self.client.get_thread_info(chat.chat_uid)
            photo_url = efms_utils.get_value(thread, ('messaging_actor', 'big_image_src', 'uri'))
        self.logger.debug("[%s] has photo_url from GraphQL: %s", chat.chat_uid, photo_url)
        if not photo_url:
            thread = self.client.fetchThreadInfo(chat.chat_uid)[chat.chat_uid]
            photo_url = getattr(thread, 'photo', None)
        self.logger.debug("[%s] has photo_url from legacy API: %s", chat.chat_uid, photo_url)
        if not photo_url:
            raise EFBOperationNotSupported('This chat has no picture.')
        photo = BytesIO(requests.get(photo_url).content)
        photo.seek(0)
        return photo

    def get_message_by_id(self, chat: EFBChat, msg_id: MessageID) -> Optional['EFBMsg']:
        index = None
        if msg_id.split('.')[-1].isdecimal():
            # is sub-message
            index = int(msg_id.split('.')[-1])
            msg_id = MessageID('.'.join(msg_id.split('.')[:-1]))

        thread_id, thread_type = self.client._getThread(chat.chat_uid, None)
        message_info = self.client._forcedFetch(thread_id, msg_id).get("message")
        message = Message._from_graphql(message_info)

        efb_msg = self.client.build_efb_msg(msg_id, chat.chat_uid, message.author,
                                            message)

        attachments = message_info.get('delta', {}).get('attachments', [])

        if attachments:
            attachment = attachments[index]
            self.client.attach_media(efb_msg, attachment)

        efb_msg.uid = msg_id

        return efb_msg

    # Additional features

    @extra(name=_("Show threads list"),
           desc=_("Usage:\n"
                  "    {function_name}"))
    def threads_list(self, args: str) -> str:
        return self.extra_functions.threads_list(args)

    @extra(name=_("Search for users"),
           desc=_("Show the first 10 results.\n"
                  "Usage:\n"
                  "    {function_name} keyword"))
    def search_users(self, args: str) -> str:
        return self.extra_functions.search_users(args)

    @extra(name=_("Search for groups"),
           desc=_("Show the first 10 results.\n"
                  "Usage:\n"
                  "    {function_name} keyword"))
    def search_groups(self, args: str) -> str:
        return self.extra_functions.search_groups(args)

    @extra(name=_("Search for pages"),
           desc=_("Show the first 10 results.\n"
                  "Usage:\n"
                  "    {function_name} keyword"))
    def search_pages(self, args: str) -> str:
        return self.extra_functions.search_pages(args)

    @extra(name=_("Search for threads"),
           desc=_("Show the first 10 results.\n"
                  "Usage:\n"
                  "    {function_name} keyword"))
    def search_threads(self, args: str) -> str:
        return self.extra_functions.search_threads(args)

    @extra(name=_("Add to group"),
           desc=_("Add members to a group.\n"
                  "Usage:\n"
                  "    {function_name} GroupID UserID [UserID ...]"))
    def add_to_group(self, args: str) -> str:
        return self.extra_functions.add_to_group(args)

    @extra(name=_("Remove from group"),
           desc=_("Remove members from a group.\n"
                  "Usage:\n"
                  "    {function_name} GroupID UserID [UserID ...]"))
    def remove_from_group(self, args: str) -> str:
        return self.extra_functions.remove_from_group(args)

    @extra(name=_("Change nickname"),
           desc=_("Change nickname of a user.\n"
                  "Usage:\n"
                  "    {function_name} UserID nickname"))
    def set_nickname(self, args: str) -> str:
        return self.extra_functions.set_nickname(args)

    @extra(name=_("Change group title"),
           desc=_("Change the title of a group.\n"
                  "Usage:\n"
                  "    {function_name} GroupID title"))
    def set_group_title(self, args: str) -> str:
        return self.extra_functions.set_group_title(args)

    @extra(name=_("Change chat emoji"),
           desc=_("Change the emoji of a chat.\n"
                  "Usage:\n"
                  "    {function_name} ChatID emoji"))
    def set_chat_emoji(self, args: str) -> str:
        return self.extra_functions.set_chat_emoji(args)

    @extra(name=_("Change member nickname"),
           desc=_("Change the nickname of a group member.\n"
                  "Usage:\n"
                  "    {function_name} GroupID MemberID nickname"))
    def set_member_nickname(self, args: str) -> str:
        return self.extra_functions.set_member_nickname(args)
