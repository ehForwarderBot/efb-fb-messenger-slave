# coding=utf-8

import logging
import copy
import os
import re
import urllib.parse
import threading
import time
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Tuple, Set, List, DefaultDict, cast, Collection
from tempfile import NamedTemporaryFile

import requests
from fbchat import Client, _graphql
from fbchat._exception import FBchatException, FBchatUserError
from fbchat._thread import ThreadType, ThreadLocation, Thread
from fbchat.models import Message, EmojiSize, Group, User
from ehforwarderbot import MsgType, coordinator
from ehforwarderbot.chat import ChatMember
from ehforwarderbot.message import Message as EFBMessage, Substitutions
from ehforwarderbot.message import LinkAttribute, LocationAttribute
from ehforwarderbot.status import MessageRemoval, MessageReactionsUpdate, ChatUpdates
from ehforwarderbot.types import MessageID, ReactionName, ChatID

from .utils import get_value, PahoMQTTPingFilter

if TYPE_CHECKING:
    from . import FBMessengerChannel


class EFMSClient(Client):
    channel: 'FBMessengerChannel'

    logger = logging.getLogger("EFMSClient")

    sent_messages: Set[str] = set()
    """Set of messages IDs sent by EFMS, popped when message is received again."""

    # Overrides for patches

    def __init__(self, channel: 'FBMessengerChannel', *args, **kwargs):
        kwargs['logging_level'] = logging.CRITICAL
        # Disable all logging inside the module
        self.channel = channel
        self._ = self.channel._
        self.ngettext = self.channel.ngettext

        # Mapping of message ID to number of EFB Messages sent.
        # Used when messages recalls from FB server
        self.message_mappings: Dict[str, int] = dict()

        # Suppress ping logs from paho.mqtt.client
        logging.getLogger("paho.mqtt.client").addFilter(PahoMQTTPingFilter())
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(__name__)

    @property
    def chat_manager(self):
        # Using property to avoid cyclic reference.
        return self.channel.chat_manager

    def send_image_file(self, filename, file, mimetype, message=None, thread_id=None, thread_type=ThreadType.USER):
        """
        Sends a local image to a thread

        Args:
            filename: Name of the image file to send
            file: image file (IO) object to send
            mimetype: MIME type of the image
            message: Additional message
            thread_id: User/Group ID to send to. See :ref:`intro_threads`
            thread_type (models.ThreadType): See :ref:`intro_threads`

        Returns:
            :ref:`Message ID <intro_message_ids>` of the sent image

        Raises:
            FBchatException: if request failed
        """
        thread_id, thread_type = self._getThread(thread_id, thread_type)
        files = [(filename, file, mimetype)]
        file_ids = self._upload(files)
        return self._sendFiles(files=file_ids, message=message, thread_id=thread_id, thread_type=thread_type)

    def markAsDelivered(self, thread_id, message_id):
        """Mark message as delivered"""
        super().markAsDelivered(thread_id, message_id)

    # region [EFMS methods]

    def get_thread_list(self, limit: int = 50, before: int = None,
                        location_obj: Tuple[ThreadLocation, ...] = (ThreadLocation.INBOX,)):
        location = list(i.name for i in location_obj)

        j = self.graphql_request(_graphql.from_doc_id(doc_id='1349387578499440', params={
            'limit': limit,
            'tags': location,
            'includeDeliveryReceipts': True,
            'includeSeqID': False,
            'before': before
        }))

        if j.get('viewer') is None:
            raise FBchatException('Could not fetch thread list: {}'.format(j))

        return j['viewer']['message_threads']['nodes']

    def get_thread_info(self, tid: str):
        j = self.graphql_request(_graphql.from_doc_id(doc_id='1508526735892416', params={
            'id': tid,
            'message_limit': 0,
            'load_message': 0,
            'load_read_receipt': False,
            'before': None,
        }))

        if j.get('message_thread') is None:
            raise FBchatException('Could not fetch thread list: {}'.format(j))

        return j['message_thread']

    def process_url(self, url: str, override: bool = False) -> str:
        """Unwrap Facebook-proxied URL if necessary."""
        if not url:
            return url
        if not override and self.channel.flag('proxy_links_by_facebook'):
            return url
        if 'safe_image.php' in url:
            query = urllib.parse.urlparse(url).query
            escaped = urllib.parse.parse_qs(query).get('url', [url])[0]
            return escaped
        elif 'l.facebook.com/l.php' in url:
            query = urllib.parse.urlparse(url).query
            escaped = urllib.parse.parse_qs(query).get('u', [url])[0]
            return escaped
        else:
            return url

    def attach_msg_type(self, msg: Message, attachment: Dict[str, Any]):
        """
        Attach message_type to a message.

        Args:
            msg: Message to be attached to
            attachment:
                Dict of information of the attachment
                ``fbchat`` entity is not used as it is not completed.
        """
        blob_attachment: Dict[str, Any] = attachment.get('mercury', {}).get('blob_attachment', attachment)
        attachment_type: str = blob_attachment.get("__typename", None)
        if 'sticker_attachment' in attachment.get('mercury', {}):
            attachment_type = '__Sticker'
        if 'extensible_attachment' in attachment.get('mercury', {}):
            attachment_type = '__Link'
            if get_value(attachment, ('mercury', 'extensible_attachment',
                                      'story_attachment', 'target', '__typename')) == 'MessageLocation':
                attachment_type = 'MessageLocation'

        if attachment_type == "MessageAudio":
            msg.type = MsgType.Voice
        elif attachment_type == 'MessageImage':
            msg.type = MsgType.Image
        elif attachment_type == 'MessageAnimatedImage':
            msg.type = MsgType.Image
        elif attachment_type == 'MessageFile':
            msg.type = MsgType.File
        elif attachment_type == 'MessageVideo':
            msg.type = MsgType.Image
        elif attachment_type == '__Sticker':
            msg.type = MsgType.Sticker
            msg.text = attachment['mercury']['sticker_attachment'].get('label', '')
        elif attachment_type == '__Link':
            msg.type = MsgType.Link
            link_information = get_value(attachment, ('mercury', 'extensible_attachment', 'story_attachment'), {})
            title = get_value(link_information, ('title_with_entities', 'text'), '')
            description = get_value(link_information, ('description', 'text'), '')
            source = get_value(link_information, ('source', 'text'), None)
            if source:
                description += " (via %s)" % source
            preview = get_value(link_information, ('media', 'playable_url'), None) if \
                get_value(link_information, ('media', 'is_playable'), False) else None
            preview = preview or get_value(link_information, ('media', 'image', 'uri'), None)
            url = link_information['media'].get('url', preview)
            msg.attributes = LinkAttribute(title=title,
                                           description=description,
                                           image=self.process_url(preview),
                                           url=self.process_url(url))
        elif attachment_type == 'MessageLocation':
            msg.type = MsgType.Location
            link_information = get_value(attachment, ('mercury', 'extensible_attachment', 'story_attachment'), {})
            title = get_value(link_information, ('title_with_entities', 'text'), '')
            description = get_value(link_information, ('description', 'text'), '')
            msg.text = '\n'.join([title, description])
            preview = get_value(link_information, ('media', 'image', 'uri'), None)
            matches = re.search(r'markers=([\d.-]+)%2C([\d.-]+)', preview)
            if matches:
                latitude, longitude = map(float, matches.groups())
            else:
                msg.type = MsgType.Unsupported
                msg.text = self._("Message type unsupported.\n{content}").format(msg.text)
                return
            msg.attributes = LocationAttribute(
                latitude=latitude, longitude=longitude
            )
        else:
            msg.type = MsgType.Unsupported
            msg.text = self._("Message type unsupported.\n{content}").format(msg.text)

    def attach_media(self, msg: Message, attachment: Dict[str, Any]):
        """
        Attach an attachment to a message.

        Args:
            msg: Message to be attached to
            attachment:
                Dict of information of the attachment
                ``fbchat`` entity is not used as it is not completed.
        """
        self.logger.debug("[%s] Trying to attach media: %s", msg.uid, attachment)

        blob_attachment: Dict[str, Any] = attachment.get('mercury', {}).get('blob_attachment', {})
        attachment_type: str = blob_attachment.get("__typename", None)
        if 'sticker_attachment' in attachment.get('mercury', {}):
            attachment_type = '__Sticker'
        if 'extensible_attachment' in attachment.get('mercury', {}):
            attachment_type = '__Link'
            extensible_type = get_value(attachment, ('mercury', 'extensible_attachment',
                                                     'story_attachment', 'target', '__typename'))
            if extensible_type == 'MessageLocation':
                attachment_type = 'MessageLocation'
            elif extensible_type == 'MessageLiveLocation':
                attachment_type = 'MessageLocation'  # TODO: Change if live location is supported by framework.

        self.logger.debug("[%s] The attachment has type %s", msg.uid, attachment_type)

        msg.filename = attachment.get('filename', None)
        msg.mime = attachment.get('mimeType', None)
        if attachment_type == "MessageAudio":
            msg.type = MsgType.Voice
            msg.filename = msg.filename or 'audio.mp3'
            msg.mime = msg.mime or 'audio/mpeg'
            ext = os.path.splitext(msg.filename)[1]
            msg.file = NamedTemporaryFile(suffix=ext)
            msg.file.write(requests.get(blob_attachment['playable_url']).content)
            msg.file.seek(0)
            msg.path = Path(msg.file.name)
        elif attachment_type == 'MessageImage':
            msg.type = MsgType.Image
            msg.filename = msg.filename or 'image.png'
            msg.mime = msg.mime or 'image/png'
            attribution_app = get_value(blob_attachment, ('attribution_app', 'name'))
            if attribution_app:
                if msg.text:
                    msg.text += " (via %s)" % attribution_app
                else:
                    msg.text = "via %s" % attribution_app
            ext = os.path.splitext(msg.filename)[1]
            msg.file = NamedTemporaryFile(suffix=ext)
            url = self.fetchImageUrl(attachment['id'])
            msg.file.write(requests.get(url).content)
            msg.file.seek(0)
            msg.path = Path(msg.file.name)
        elif attachment_type == 'MessageAnimatedImage':
            msg.type = MsgType.Animation
            msg.filename = msg.filename or 'image.gif'
            msg.mime = msg.mime or 'image/gif'
            ext = os.path.splitext(msg.filename)[1]
            msg.file = NamedTemporaryFile(suffix=ext)
            msg.file.write(requests.get(blob_attachment['animated_image']['uri'], allow_redirects=True).content)
            msg.file.seek(0)
            msg.path = Path(msg.file.name)
        elif attachment_type == 'MessageFile':
            msg.type = MsgType.File
            msg.filename = msg.filename or 'file'
            msg.mime = msg.mime or 'application/octet-stream'
            ext = os.path.splitext(msg.filename)[1]
            msg.file = NamedTemporaryFile(suffix=ext)
            msg.file.write(requests.get(self.process_url(blob_attachment['url'], True), allow_redirects=True).content)
            msg.file.seek(0)
            msg.path = Path(msg.file.name)
        elif attachment_type == 'MessageVideo':
            msg.type = MsgType.Image
            msg.filename = msg.filename or 'video.mp4'
            msg.mime = msg.mime or 'video/mpeg'
            ext = os.path.splitext(msg.filename)[1]
            msg.file = NamedTemporaryFile(suffix=ext)
            msg.file.write(requests.get(blob_attachment['playable_url'], allow_redirects=True).content)
            msg.file.seek(0)
            msg.path = Path(msg.file.name)
        elif attachment_type == '__Sticker':
            if get_value(attachment, ('mercury', 'sticker_attachment', 'pack', 'id')) == "227877430692340":
                self.logger.debug("[%s] Sticker received is a \"Like\" sticker. Converting message to text.", msg.uid)

                sticker_id = get_value(attachment, ('mercury', 'sticker_attachment', 'id'))
                for i in EmojiSize:
                    if sticker_id == i.value:
                        msg.type = MsgType.Text
                        msg.text = "👍 (%s)" % i.name[0]
                        return
            msg.type = MsgType.Sticker
            url = attachment['mercury']['sticker_attachment']['url']
            msg.text = attachment['mercury']['sticker_attachment'].get('label', '')
            filename = os.path.split(urllib.parse.urlparse(url).path)[1]
            msg.filename = filename
            ext = os.path.splitext(filename)[1]
            response = requests.get(url)
            msg.mime = response.headers['content-type']
            msg.file = NamedTemporaryFile(suffix=ext)
            msg.file.write(response.content)
            msg.file.seek(0)
            msg.path = Path(msg.file.name)
        elif attachment_type == '__Link':
            msg.type = MsgType.Link
            link_information = get_value(attachment, ('mercury', 'extensible_attachment', 'story_attachment'), {})
            title = get_value(link_information, ('title_with_entities', 'text'), '')
            description = get_value(link_information, ('description', 'text'), '')
            source = get_value(link_information, ('source', 'text'), None)
            if source:
                description += " (via %s)" % source
            preview = get_value(link_information, ('media', 'playable_url'), None) if \
                get_value(link_information, ('media', 'is_playable'), False) else None
            preview = preview or get_value(link_information, ('media', 'image', 'uri'), None)
            url = link_information.get('url', preview)
            msg.attributes = LinkAttribute(title=title,
                                           description=description,
                                           image=self.process_url(preview),
                                           url=self.process_url(url))
        elif attachment_type == 'MessageLocation':
            msg.type = MsgType.Location
            link_information = get_value(attachment, ('mercury', 'extensible_attachment', 'story_attachment'), {})
            title = get_value(link_information, ('title_with_entities', 'text'), '')
            description = get_value(link_information, ('description', 'text'), '')
            msg.text = '\n'.join([title, description])
            preview = get_value(link_information, ('media', 'image', 'uri'), None)
            matches = re.search(r'markers=([\d.-]+)%2C([\d.-]+)', preview)
            if matches:
                latitude, longitude = map(float, matches.groups())
            else:
                msg.type = MsgType.Unsupported
                msg.text = self._("Message type unsupported.\n{content}").format(msg.text)
                return
            msg.attributes = LocationAttribute(
                latitude=latitude, longitude=longitude
            )
        else:
            msg.type = MsgType.Unsupported
            msg.text = self._("Message type unsupported.\n{content}").format(msg.text)

    def send(self, *args, **kwargs):
        result = super().send(*args, **kwargs)
        if result.startswith('mid.$'):
            self.sent_messages.add(result)
        return result

    # Triggers

    def onMessage(self, *args, **kwargs):
        """Migrate message precessing to another thread to prevent blocking."""
        threading.Thread(target=self.on_message, args=args, kwargs=kwargs,
                         name=f"EFMS slave message thread for {kwargs['mid']}").run()

    def on_message(self, mid: str = '', author_id: str = '', message: str = '', message_object: Message = None,
                   thread_id: str = '', thread_type: str = ThreadType.USER, ts: str = '', metadata=None, msg=None):
        """
        Called when the client is listening, and somebody sends a message

        Args:
            mid: The message ID
            author_id: The ID of the author
            message: (deprecated. Use `message_object.text` instead)
            message_object (models.Message): The message (As a `Message` object)
            thread_id: Thread ID that the message was sent to. See :ref:`intro_threads`
            thread_type (models.ThreadType): Type of thread that the message was sent to. See :ref:`intro_threads`
            ts: The timestamp of the message
            metadata: Extra metadata about the message
            msg: A full set of the data received
        """

        # Ignore messages sent by EFMS
        time.sleep(0.25)

        if mid in self.sent_messages:
            self.sent_messages.remove(mid)
            return

        self.logger.debug("[%s] Received message from Messenger: %s", mid, message_object)

        efb_msg = self.build_efb_msg(mid, thread_id, author_id, message_object)

        attachments = msg.get('attachments', [])

        if len(attachments) > 1:
            self.logger.debug("[%s] Multiple attachments detected. Splitting into %s messages.",
                              mid, len(attachments))
            self.message_mappings[mid] = len(attachments)
            for idx, i in enumerate(attachments):
                sub_msg = copy.copy(efb_msg)
                sub_msg.uid = MessageID(f"{efb_msg.uid}.{idx}")
                self.attach_media(sub_msg, i)
                coordinator.send_message(sub_msg)
            return

        if attachments:
            self.attach_media(efb_msg, attachments[0])

        coordinator.send_message(efb_msg)

        self.markAsDelivered(mid, thread_id)

    def build_efb_msg(self, mid: str, thread_id: str, author_id: str, message_object: Message,
                      nested: bool = False) -> EFBMessage:
        efb_msg = EFBMessage(
            uid=MessageID(mid),
            text=message_object.text,
            type=MsgType.Text,
            deliver_to=coordinator.master,
        )

        # Authors
        efb_msg.chat = self.chat_manager.get_thread(thread_id)
        efb_msg.author = efb_msg.chat.get_member(ChatID(author_id))

        if not nested and message_object.replied_to:
            efb_msg.target = self.build_efb_msg(message_object.reply_to_id,
                                                thread_id=thread_id,
                                                author_id=message_object.author,
                                                message_object=message_object.replied_to,
                                                nested=True)

        if message_object.mentions:
            mentions: Dict[Tuple[int, int], ChatMember] = dict()
            for i in message_object.mentions:
                mentions[(i.offset, i.offset + i.length)] = efb_msg.chat.get_member(i.thread_id)
            efb_msg.substitutions = Substitutions(mentions)

        if message_object.emoji_size:
            efb_msg.text += " (%s)" % message_object.emoji_size.name[0]
            # " (S)", " (M)", " (L)"

        if message_object.reactions:
            reactions: DefaultDict[ReactionName, List[ChatMember]] = defaultdict(list)
            for user_id, reaction in message_object.reactions.items():
                reactions[ReactionName(reaction.value)].append(
                    efb_msg.chat.get_member(user_id))
            efb_msg.reactions = reactions
        return efb_msg

    # endregion

    def onChatTimestamp(self, buddylist=None, msg=None):
        # No action needed on receiving timestamp update
        # Suppress timestamp log
        pass

    def fetchThreadList(
            self, offset=None, limit: int = 20,
            thread_location: Collection[ThreadLocation] = (ThreadLocation.INBOX,),
            before: int = None
    ) -> List[Thread]:
        """Fetch the client's thread list.

        Args:
            offset: Deprecated. Do not use!
            limit (int): Max. number of threads to retrieve. Capped at 20
            thread_location (ThreadLocation): INBOX, PENDING, ARCHIVED or OTHER
            before (int): A timestamp (in milliseconds), indicating from which point to retrieve threads

        Returns:
            list: :class:`Thread` objects

        Raises:
            FBchatException: If request failed

        Notes:
            Modified based on fbchat 1.9.3
        """
        if offset is not None:
            self.logger.warning(
                "Using `offset` in `fetchThreadList` is no longer supported, "
                "since Facebook migrated to the use of GraphQL in this request. "
                "Use `before` instead."
            )

        if limit > 20 or limit < 1:
            raise FBchatUserError("`limit` should be between 1 and 20")

        params = {
            "limit": limit,
            "tags": [i.value for i in thread_location],
            "before": before,
            "includeDeliveryReceipts": True,
            "includeSeqID": False,
        }
        (j,) = self.graphql_requests(_graphql.from_doc_id("1349387578499440", params))

        rtn = []
        for node in j["viewer"]["message_threads"]["nodes"]:
            _type = node.get("thread_type")
            if _type == "GROUP":
                rtn.append(Group._from_graphql(node))
            elif _type == "ONE_TO_ONE":
                rtn.append(User._from_thread_fetch(node))
            elif _type == "MARKETPLACE":  # MOD: Added branch
                self.logger.warning("Marketplace chat is yet to be supported: %s", node)
                # TODO: support marketplace chat
            else:  # MOD: Modified branch
                self.logger.error("Unknown thread type: %s, %s", _type, node)
        return rtn

    # region [Callbacks]

    def onReactionAdded(self, mid=None, reaction=None, author_id=None, thread_id=None, thread_type=None, ts=None,
                        msg=None):
        self.on_message_reaction(thread_id, mid)

    def onReactionRemoved(self, mid=None, author_id=None, thread_id=None, thread_type=None, ts=None, msg=None):
        self.on_message_reaction(thread_id, mid)

    def on_message_reaction(self, thread_id, message_id):
        thread_id, thread_type = self._getThread(thread_id, None)
        msg_data = self._forcedFetch(thread_id, message_id).get("message")
        msg: Message = Message._from_graphql(msg_data)

        chat = self.chat_manager.get_thread(thread_id)

        reactions = {}
        if msg.reactions:
            reactions = defaultdict(list)
            for user_id, reaction in msg.reactions.items():
                reactions[reaction.value].append(chat.get_member(user_id))

        update = MessageReactionsUpdate(chat=chat, msg_id=message_id, reactions=reactions)

        coordinator.send_status(update)

    def onMessageUnsent(self, mid=None, author_id=None, thread_id=None, thread_type=None, ts=None, msg=None):
        chat = self.chat_manager.get_thread(thread_id)
        author = chat.get_member(author_id)
        if mid in self.message_mappings:
            for i in range(self.message_mappings[mid]):
                coordinator.send_status(
                    MessageRemoval(source_channel=self.channel,
                                   destination_channel=coordinator.master,
                                   message=EFBMessage(chat=chat, author=author, uid=f"{mid}.{i}"))
                )
        else:
            coordinator.send_status(
                MessageRemoval(source_channel=self.channel,
                               destination_channel=coordinator.master,
                               message=EFBMessage(chat=chat, author=author, uid=mid))
            )

    def onMessageError(self, exception=None, msg=None):
        self.logger.exception("Error %s occurred while parsing %s", exception, msg, exc_info=exception)

    def onUnknownMesssageType(self, msg=None):
        if msg.get("class") == 'ForcedFetch':
            # New chat appears.
            # {'forceInsert': False, 'irisSeqId': '538', 'isLazy': False, 'threadKey': {'threadFbId': '1234567890'}, 'class': 'ForcedFetch'}
            coordinator.send_status(ChatUpdates(
                channel=self.channel,
                new_chats=[msg['threadKey']['threadFbId']]
            ))
        super().onUnknownMesssageType(msg)

    # endregion [Callbacks]
