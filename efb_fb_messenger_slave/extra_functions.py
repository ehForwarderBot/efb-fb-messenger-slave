from typing import TYPE_CHECKING

from fbchat import ThreadType

from ehforwarderbot.utils import extra

from .efms_chat import EFMSChat

if TYPE_CHECKING:
    from . import FBMessengerChannel


def catch_exceptions(func):
    """
    Decorator to wrap extra functions.
    Return the exception string when caught.
    """
    def catch_exceptions_wrap(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            return "Error occurred in %s(%s, %s): %r" % (func.__name__, args, kwargs, e)
    return catch_exceptions_wrap


class ExtraFunctionsManager:
    def __init__(self, channel: 'FBMessengerChannel'):
        self.channel = channel
        self.client = channel.client

    @catch_exceptions
    def threads_list(self, args: str) -> str:
        chats = self.channel.get_chats()
        msg = "You have %s thread(s) in your thread list.\n" % len(chats)
        for i in chats:
            msg += "\n{chat.chat_uid}: {chat.chat_name} [{type}]" \
                .format(chat=i,
                        type=i.vendor_specific.get('chat_type'))
        return msg

    @catch_exceptions
    def search_users(self, args: str) -> str:
        users = list(map(lambda a: EFMSChat(self.channel, a), self.client.searchForUsers(args, limit=10)))
        msg = "Found %s user(s).\n" % len(users)
        for i in users:
            msg += "\n{chat.chat_uid}: {chat.chat_name}".format(chat=i)
        return msg

    @catch_exceptions
    def search_groups(self, args: str) -> str:
        groups = list(map(lambda a: EFMSChat(self.channel, a), self.client.searchForGroups(args, limit=10)))
        msg = "Found %s group(s).\n" % len(groups)
        for i in groups:
            msg += "\n{chat.chat_uid}: {chat.chat_name}".format(chat=i)
        return msg

    @catch_exceptions
    def search_pages(self, args: str) -> str:
        pages = list(map(lambda a: EFMSChat(self.channel, a), self.client.searchForPages(args, limit=10)))
        msg = "Found %s page(s).\n" % len(pages)
        for i in pages:
            msg += "\n{chat.chat_uid}: {chat.chat_name}".format(chat=i)
        return msg

    @catch_exceptions
    def search_threads(self, args: str) -> str:
        threads = list(map(lambda a: EFMSChat(self.channel, a), self.client.searchForThreads(args, limit=10)))
        msg = "Found %s thread(s).\n" % len(threads)
        for i in threads:
            msg += "\n{chat.chat_uid}: {chat.chat_name} [{type}]" \
                .format(chat=i,
                        type=i.vendor_specific.get('chat_type'))
        return msg

    @catch_exceptions
    def add_to_group(self, args: str) -> str:
        """GroupID UserID [UserID ...]"""
        args = args.split(' ')
        if len(args) < 2:
            return "Group ID and user IDs are required"
        self.client.addUsersToGroup(args[1:], args[0])
        return "Users %s are successfully added to group %s." % (args[1:], args[0])

    @catch_exceptions
    def remove_from_group(self, args: str) -> str:
        """GroupID UserID"""
        args = args.split(' ')
        if len(args) != 2:
            return "Group ID and user ID are required"
        self.client.removeUserFromGroup(args[1], args[0])
        return "User %s is successfully removed from group %s." % (args[1], args[0])

    @catch_exceptions
    def set_nickname(self, args: str) -> str:
        """UserID nickname"""
        args = args.split(' ', 1)
        if len(args) < 2:
            return "User ID and nickname are required."
        self.client.changeNickname(args[1], args[0], args[0])
        return "Nickname of %s is set to %s." % args

    @catch_exceptions
    def set_group_title(self, args: str) -> str:
        """GroupID title"""
        args = args.split(' ', 1)
        if len(args) < 2:
            return "User ID and title are required."
        self.client.changeThreadTitle(args[1], args[0], thread_type=ThreadType.GROUP)
        return "Title of group %s is set to %s." % args

    @catch_exceptions
    def set_chat_emoji(self, args: str) -> str:
        """ChatID emoji"""
        args = args.split(' ', 1)
        if len(args) < 2:
            return "User ID and emoji are required."
        self.client.changeThreadEmoji(args[1], args[0])
        return "Emoji of group %s is set to %s." % args

    @catch_exceptions
    def set_member_nickname(self, args: str) -> str:
        """GroupID MemberID nickname"""
        args = args.split(' ', 2)
        if len(args) < 3:
            return "Group ID, member ID and are nickname required."
        self.client.changeNickname(args[2], args[1], args[0])
        return "Nickname of %s -> %s is set as %s." % args
