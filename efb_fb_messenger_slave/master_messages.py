# coding=utf-8

import logging
import threading
import time
from typing import TYPE_CHECKING, Tuple, List

import emoji
from fbchat.models import Thread, Message, TypingStatus, ThreadType, Mention, EmojiSize, Sticker, LocationAttachment

from ehforwarderbot import MsgType
from ehforwarderbot.message import Message as EFBMessage
from ehforwarderbot.exceptions import EFBMessageTypeNotSupported
from ehforwarderbot.message import LinkAttribute, StatusAttribute, LocationAttribute

if TYPE_CHECKING:
    from . import FBMessengerChannel


class MasterMessageManager:
    class CustomReaction:
        def __init__(self, reaction):
            self.value = reaction

    logger = logging.getLogger("MasterMessageManager")
    supported_message_types = {MsgType.Text, MsgType.Image, MsgType.Sticker,
                               MsgType.Voice, MsgType.File, MsgType.Video,
                               MsgType.Status, MsgType.Unsupported,
                               MsgType.Location, MsgType.Animation}

    def __init__(self, channel: 'FBMessengerChannel'):
        self.channel = channel
        self.client = channel.client
        self.flag = channel.flag

    def send_message(self, msg: EFBMessage) -> Message:
        self.logger.debug("Received message from master: %s", msg)

        try:
            target_msg_offset = 0
            prefix = ""

            mentions = []

            # Send message reaction
            # if msg.target and msg.text.startswith('r`') and \
            #         msg.target.uid.startswith("mid.$"):
            #     self.logger.debug("[%s] Message is a reaction to another message: %s", msg.uid, msg.text)
            #     msg_id = ".".join(msg.target.uid.split(".", 2)[:2])
            #     if getattr(MessageReaction, msg.text[2:], None):
            #         self.client.reactToMessage(msg_id, getattr(MessageReaction, msg.text[2:]))
            #     else:
            #         self.client.reactToMessage(msg_id, self.CustomReaction(msg.text[2:]))
            #     msg.uid = "__reaction__"
            #     return msg

            # Message substitutions
            if msg.substitutions:
                self.logger.debug("[%s] Message has substitutions: %s", msg.uid, msg.substitutions)
                for i in msg.substitutions:
                    mentions.append(Mention(msg.substitutions[i].id,
                                            target_msg_offset + i[0], i[1] - i[0]))
                self.logger.debug("[%s] Translated to mentions: %s", msg.uid, mentions)

            fb_msg = Message(text=prefix + msg.text, mentions=mentions)
            thread: Thread = self.client.fetchThreadInfo(msg.chat.id)[str(msg.chat.id)]

            if msg.target and msg.target.uid:
                fb_msg.reply_to_id = msg.target.uid

            if msg.type in (MsgType.Text, MsgType.Unsupported):
                # Remove variation selector-16 (force colored emoji) for
                # matching.
                emoji_compare = msg.text.replace("\uFE0F", "")
                if emoji_compare == "👍":
                    fb_msg.sticker = Sticker(uid=EmojiSize.SMALL.value)
                    if not prefix:
                        fb_msg.text = None
                elif emoji_compare[:-1] == "👍" and emoji_compare[-1] in 'SML':
                    if emoji_compare[-1] == 'S':
                        fb_msg.sticker = Sticker(uid=EmojiSize.SMALL.value)
                    elif emoji_compare[-1] == 'M':
                        fb_msg.sticker = Sticker(uid=EmojiSize.MEDIUM.value)
                    elif emoji_compare[-1] == 'L':
                        fb_msg.sticker = Sticker(uid=EmojiSize.LARGE.value)
                    if not prefix:
                        fb_msg.text = None
                elif emoji_compare[:-1] in emoji.UNICODE_EMOJI and emoji_compare[-1] in 'SML':  # type: ignore
                    self.logger.debug("[%s] Message is an Emoji message: %s", msg.uid, emoji_compare)
                    if emoji_compare[-1] == 'S':
                        fb_msg.emoji_size = EmojiSize.SMALL
                    elif emoji_compare[-1] == 'M':
                        fb_msg.emoji_size = EmojiSize.MEDIUM
                    elif emoji_compare[-1] == 'L':
                        fb_msg.emoji_size = EmojiSize.LARGE
                    fb_msg.text = emoji_compare[:-1]
                msg.uid = self.client.send(fb_msg, thread_id=thread.uid, thread_type=thread.type)
            elif msg.type in (MsgType.Image, MsgType.Sticker, MsgType.Animation):
                msg_uid = self.client.send_image_file(msg.filename, msg.file, msg.mime, message=fb_msg,
                                                      thread_id=thread.uid, thread_type=thread.type)
                if msg_uid.startswith('mid.$'):
                    self.client.sent_messages.add(msg_uid)
                    self.logger.debug("Sent message with ID %s", msg_uid)
                msg.uid = msg_uid
            elif msg.type == MsgType.Voice:
                files = self.upload_file(msg, voice_clip=True)
                msg_uid = self.client._sendFiles(files=files, message=fb_msg,
                                                 thread_id=thread.uid, thread_type=thread.type)
                if msg_uid.startswith('mid.$'):
                    self.client.sent_messages.add(msg_uid)
                    self.logger.debug("Sent message with ID %s", msg_uid)
                msg.uid = msg_uid
            elif msg.type in (MsgType.File, MsgType.Video):
                files = self.upload_file(msg)
                msg_uid = self.client._sendFiles(files=files, message=fb_msg,
                                                 thread_id=thread.uid, thread_type=thread.type)
                if msg_uid.startswith('mid.$'):
                    self.client.sent_messages.add(msg_uid)
                    self.logger.debug("Sent message with ID %s", msg_uid)
                msg.uid = msg_uid
            elif msg.type == MsgType.Status:
                assert (isinstance(msg.attributes, StatusAttribute))
                status: StatusAttribute = msg.attributes
                if status.status_type in (StatusAttribute.Types.TYPING,
                                          StatusAttribute.Types.UPLOADING_VOICE,
                                          StatusAttribute.Types.UPLOADING_VIDEO,
                                          StatusAttribute.Types.UPLOADING_IMAGE,
                                          StatusAttribute.Types.UPLOADING_FILE):
                    self.client.setTypingStatus(TypingStatus.TYPING, thread_id=thread.uid, thread_type=thread.type)
                    threading.Timer(status.timeout / 1000, self.stop_typing, args=(thread.uid, thread.type)).start()
            elif msg.type == MsgType.Link:
                assert (isinstance(msg.attributes, LinkAttribute))
                link: LinkAttribute = msg.attributes
                if self.flag('send_link_with_description'):
                    info: Tuple[str, ...] = (link.title,)
                    if link.description:
                        info += (link.description,)
                    info += (link.url,)
                    text = "\n".join(info)
                else:
                    text = link.url
                if fb_msg.text:
                    text = fb_msg.text + "\n" + text
                fb_msg.text = text
                msg.uid = self.client.send(fb_msg, thread_id=thread.uid, thread_type=thread.type)
            elif msg.type == MsgType.Location:
                assert (isinstance(msg.attributes, LocationAttribute))
                location_attr: LocationAttribute = msg.attributes
                location = LocationAttachment(latitude=location_attr.latitude,
                                              longitude=location_attr.longitude)
                self.client.sendPinnedLocation(location, fb_msg, thread_id=thread.uid, thread_type=thread.type)
            else:
                raise EFBMessageTypeNotSupported()
            return msg
        finally:
            if msg.file and not msg.file.closed:
                msg.file.close()
            self.client.markAsSeen()
            self.client.markAsRead(msg.chat.id)

    def stop_typing(self, timeout: int, thread_uid: str, thread_type: ThreadType):
        """Wait for a number of milliseconds, and stop typing."""
        time.sleep(timeout / 1000)
        self.client.setTypingStatus(TypingStatus.STOPPED, thread_id=thread_uid, thread_type=thread_type)

    def upload_file(self, msg: EFBMessage, voice_clip=False) -> List[Tuple[int, str]]:
        """Upload media of a message as file, and return the file id."""
        return self.client._upload([(msg.filename, msg.file, msg.mime)], voice_clip)
