import time
import threading
from typing import TYPE_CHECKING, Set

from fbchat.models import Thread, Message, TypingStatus, ThreadType
from ehforwarderbot import EFBMsg, MsgType
from ehforwarderbot.message import EFBMsgLinkAttribute, EFBMsgStatusAttribute
from ehforwarderbot.exceptions import EFBMessageTypeNotSupported

from .utils import get_value

if TYPE_CHECKING:
    from . import FBMessengerChannel


class MasterMessageManager:
    def __init__(self, channel: 'FBMessengerChannel'):
        self.channel = channel
        channel.supported_message_types: Set[MsgType] = {MsgType.Text, MsgType.Image, MsgType.Sticker,
                                                         MsgType.Audio, MsgType.File, MsgType.Video,
                                                         MsgType.Status, MsgType.Unsupported}
        self.client = channel.client
        self.flag = channel.flag

    def send_message(self, msg: EFBMsg) -> EFBMsg:
        try:
            thread: Thread = self.client.fetchThreadInfo(msg.chat.chat_uid)[str(msg.chat.chat_uid)]
            if msg.type in (MsgType.Text, MsgType.Unsupported):
                # TODO: send emoji with size option using formatted text
                msg.uid = self.client.send(Message(text=msg.text), thread_id=thread.uid, thread_type=thread.type)
                return msg.uid
            elif msg.type in (MsgType.Image, MsgType.Sticker):
                msg.uid = self.client.send_image_file(msg.path, msg.mime, message=Message(text=msg.text),
                                                      thread_id=thread.uid, thread_type=thread.type)
            elif msg.type == MsgType.Audio:
                file_id = self.upload_file(msg)
                msg.uid = self.client.send_audio(file_id=file_id, message=Message(text=msg.text),
                                                 thread_id=thread.uid, thread_type=thread.type)
            elif msg.type == MsgType.File:
                file_id = self.upload_file(msg)
                msg.uid = self.client.send_file(file_id=file_id, message=Message(text=msg.text),
                                                thread_id=thread.uid, thread_type=thread.type)
            elif msg.type == MsgType.Video:
                file_id = self.upload_file(msg)
                msg.uid = self.client.send_video(file_id=file_id, message=Message(text=msg.text),
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
                if msg.text:
                    text = msg.text + "\n" + text
                msg.uid = self.client.send(Message(text=text), thread_id=thread.uid, thread_type=thread.type)
            else:
                raise EFBMessageTypeNotSupported()
        finally:
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
