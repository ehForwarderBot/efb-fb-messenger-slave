# coding=utf-8

import logging
import time
import threading
import emoji
from typing import TYPE_CHECKING, Set

from fbchat.models import Thread, Message, TypingStatus, ThreadType, Mention, EmojiSize, MessageReaction, Sticker
from ehforwarderbot import EFBMsg, MsgType
from ehforwarderbot.message import EFBMsgLinkAttribute, EFBMsgStatusAttribute, ChatType
from ehforwarderbot.exceptions import EFBMessageTypeNotSupported

from .utils import get_value

if TYPE_CHECKING:
    from . import FBMessengerChannel


class MasterMessageManager:

    logger = logging.getLogger("MasterMessageManager")

    def __init__(self, channel: 'FBMessengerChannel'):
        self.channel = channel
        channel.supported_message_types: Set[MsgType] = {MsgType.Text, MsgType.Image, MsgType.Sticker,
                                                         MsgType.Audio, MsgType.File, MsgType.Video,
                                                         MsgType.Status, MsgType.Unsupported}
        self.client = channel.client
        self.flag = channel.flag

    def send_message(self, msg: EFBMsg) -> EFBMsg:
        self.logger.debug("Received message from master: %s", msg)

        try:
            target_msg_offset = 0
            prefix = ""

            mentions = []

            # Send message reaction
            if msg.target and msg.text.startswith('r`') and getattr(MessageReaction, msg.text[2:], None)\
                    and msg.uid.startswith("mid.$"):
                self.logger.debug("[%s] Message is a reaction to another message: %s", msg.uid, msg.text)
                msg_id = ".".join(msg.target.uid.split(".", 2)[:2])
                self.client.reactToMessage(msg_id, getattr(MessageReaction, msg.text[2:]))
                msg.uid = "__reaction__"
                return msg

            # Target message
            if msg.target:
                self.logger.debug("[%s] Message replying to another message: %s", msg.uid, msg.target)
                if msg.target.chat.chat_type == ChatType.Group:
                    target_msg_name = msg.target.author.chat_alias or msg.target.author.chat_name
                    prefix = '@%s "%s"\n' % (target_msg_name, msg.target.text or msg.target.type)
                    mentions.append(Mention(msg.target.author.chat_uid, 1, len(target_msg_name)))
                else:
                    prefix = '"%s"\n' % msg.target.text or msg.target.type
                target_msg_offset = len(prefix)
                self.logger.debug("[%s] Converted to prefix: %s", msg.uid, prefix)

            # Message substitutions
            if msg.substitutions:
                self.logger.debug("[%s] Message has substitutions: %s", msg.uid, msg.substitutions)
                for i in msg.substitutions:
                    mentions.append(Mention(msg.substitutions[i].chat_uid,
                                            target_msg_offset + i[0], i[1] - i[0]))
                self.logger.debug("[%s] Translated to mentions: %s", msg.uid, mentions)

            fb_msg = Message(text=prefix + msg.text, mentions=mentions)
            thread: Thread = self.client.fetchThreadInfo(msg.chat.chat_uid)[str(msg.chat.chat_uid)]

            if msg.type in (MsgType.Text, MsgType.Unsupported):
                if msg.text == "👍":
                    fb_msg.sticker = Sticker(uid=EmojiSize.SMALL)
                elif msg.text[0] == "👍" and len(msg) == 2 and msg[1] in 'SML':
                    if msg.text[-1] == 'S':
                        fb_msg.sticker = Sticker(uid=EmojiSize.SMALL)
                    elif msg.text[-1] == 'M':
                        fb_msg.sticker = Sticker(uid=EmojiSize.MEDIUM)
                    elif msg.text[-1] == 'L':
                        fb_msg.sticker = Sticker(uid=EmojiSize.LARGE)
                elif msg.text[:-1] in emoji.UNICODE_EMOJI and msg.text[-1] in 'SML':
                    self.logger.debug("[%s] Message is an Emoji message: %s", msg.uid, msg.text)
                    if msg.text[-1] == 'S':
                        fb_msg.emoji_size = EmojiSize.SMALL
                    elif msg.text[-1] == 'M':
                        fb_msg.emoji_size = EmojiSize.MEDIUM
                    elif msg.text[-1] == 'L':
                        fb_msg.emoji_size = EmojiSize.LARGE
                    fb_msg.text = msg.text[:-1]
                msg.uid = self.client.send(fb_msg, thread_id=thread.uid, thread_type=thread.type)
            elif msg.type in (MsgType.Image, MsgType.Sticker):
                msg.uid = self.client.send_image_file(msg.path, msg.mime, message=fb_msg,
                                                      thread_id=thread.uid, thread_type=thread.type)
            elif msg.type == MsgType.Audio:
                file_id = self.upload_file(msg)
                msg.uid = self.client.send_audio(file_id=file_id, message=fb_msg,
                                                 thread_id=thread.uid, thread_type=thread.type)
            elif msg.type == MsgType.File:
                file_id = self.upload_file(msg)
                msg.uid = self.client.send_file(file_id=file_id, message=fb_msg,
                                                thread_id=thread.uid, thread_type=thread.type)
            elif msg.type == MsgType.Video:
                file_id = self.upload_file(msg)
                msg.uid = self.client.send_video(file_id=file_id, message=fb_msg,
                                                 thread_id=thread.uid, thread_type=thread.type)
            elif msg.type == MsgType.Status:
                attribute: EFBMsgStatusAttribute = msg.attributes
                if attribute.status_type in (EFBMsgStatusAttribute.Types.TYPING,
                                             EFBMsgStatusAttribute.Types.UPLOADING_AUDIO,
                                             EFBMsgStatusAttribute.Types.UPLOADING_VIDEO,
                                             EFBMsgStatusAttribute.Types.UPLOADING_IMAGE,
                                             EFBMsgStatusAttribute.Types.UPLOADING_FILE):
                    self.client.setTypingStatus(TypingStatus.TYPING, thread_id=thread.uid, thread_type=thread.type)
                    threading.Thread(target=self.stop_typing, args=(attribute.timeout, thread.uid, thread.type)).run()
            elif msg.type == MsgType.Link:
                attribute: EFBMsgLinkAttribute = msg.attributes
                if self.flag('send_link_with_description'):
                    info = (attribute.title,)
                    if attribute.description:
                        info += (attribute.description,)
                    info += (attribute.url,)
                    text = "\n".join(info)
                else:
                    text = attribute.url
                if fb_msg.text:
                    text = fb_msg.text + "\n" + text
                fb_msg.text = text
                msg.uid = self.client.send(fb_msg, thread_id=thread.uid, thread_type=thread.type)
            else:
                raise EFBMessageTypeNotSupported()
            return msg
        finally:
            if msg.file and not msg.file.closed:
                msg.file.close()
            self.client.markAsSeen()
            self.client.markAsRead(msg.chat.chat_uid)

    def stop_typing(self, timeout: int, thread_uid: str, thread_type: ThreadType):
        """Wait for a number of milliseconds, and stop typing."""
        time.sleep(timeout / 1000)
        self.client.setTypingStatus(TypingStatus.STOPPED, thread_id=thread_uid, thread_type=thread_type)

    def upload_file(self, msg: EFBMsg) -> int:
        """Upload media of a message as file, and return the file id."""
        response = self.client._postFile(self.client.req_url.UPLOAD, {
            'file': (msg.filename, msg.file, msg.mime)
        }, fix_request=True, as_json=True)
        return get_value(response, ('payload', 'metadata', 0, 'file_id')) or \
               get_value(response, ('payload', 'metadata', 0, 'audio_id')) or \
               get_value(response, ('payload', 'metadata', 0, 'video_id'))
