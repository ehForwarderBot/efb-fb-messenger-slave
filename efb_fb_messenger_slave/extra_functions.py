from typing import TYPE_CHECKING

from fbchat.models import ThreadType

if TYPE_CHECKING:
    from . import FBMessengerChannel


def catch_exceptions(func):
    """
    Decorator to wrap additional features.
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
        self._ = channel._
        self.ngettext = channel.ngettext
        self.chat_manager = channel.chat_manager

    @catch_exceptions
    def threads_list(self, args: str) -> str:
        chats = self.channel.get_chats()
        msg = self.ngettext("You have {0} thread in your thread list.",
                            "You have {0} threads in your thread list.",
                            len(chats)).format(len(chats)) + "\n"
        for i in chats:
            msg += "\n{chat.id}: {chat.name} [{type}]" \
                .format(chat=i,
                        type=i.vendor_specific.get('chat_type'))
        return msg

    @catch_exceptions
    def search_users(self, args: str) -> str:
        users = list(map(self.chat_manager.build_chat_by_thread_obj,
                         self.client.searchForUsers(args, limit=10)))
        msg = self.ngettext("Found {} user.",
                            "Found {} users.",
                            len(users)).format(len(users)) + "\n"
        for i in users:
            msg += "\n{chat.id}: {chat.name}".format(chat=i)
        return msg

    @catch_exceptions
    def search_groups(self, args: str) -> str:
        groups = list(map(self.chat_manager.build_chat_by_thread_obj,
                          self.client.searchForGroups(args, limit=10)))
        msg = self.ngettext("Found {} group.",
                            "Found {} groups.",
                            len(groups)).format(len(groups)) + "\n"
        for i in groups:
            msg += "\n{chat.id}: {chat.name}".format(chat=i)
        return msg

    @catch_exceptions
    def search_pages(self, args: str) -> str:
        pages = list(map(self.chat_manager.build_chat_by_thread_obj,
                         self.client.searchForPages(args, limit=10)))
        msg = self.ngettext("Found {} page.",
                            "Found {} pages.",
                            len(pages)).format(len(pages)) + "\n"
        for i in pages:
            msg += "\n{chat.id}: {chat.name}".format(chat=i)
        return msg

    @catch_exceptions
    def search_threads(self, args: str) -> str:
        threads = list(map(self.chat_manager.build_chat_by_thread_obj,
                           self.client.searchForThreads(args, limit=10)))
        msg = self.ngettext("Found {} thread.",
                            "Found {} threads.",
                            len(threads)).format(len(threads)) + "\n"
        for i in threads:
            msg += "\n{chat.id}: {chat.name} [{type}]" \
                .format(chat=i,
                        type=i.vendor_specific.get('chat_type'))
        return msg

    @catch_exceptions
    def add_to_group(self, argv: str) -> str:
        """GroupID UserID [UserID ...]"""
        args = argv.split(' ')
        if len(args) < 2:
            return self._("Group ID and user IDs are required")
        self.client.addUsersToGroup(args[1:], args[0])
        return self.ngettext("User {0} are successfully added to group {1}.",
                             "Users {0} are successfully added to group {1}.",
                             len(args) - 1).format(args[1:], args[0])

    @catch_exceptions
    def remove_from_group(self, argv: str) -> str:
        """GroupID UserID"""
        args = argv.split(' ')
        if len(args) != 2:
            return self._("Group ID and user ID are required.")
        self.client.removeUserFromGroup(args[1], args[0])
        return self._("User {0} is successfully removed from group {1}.").format(args[1], args[0])

    @catch_exceptions
    def set_nickname(self, argv: str) -> str:
        """UserID nickname"""
        args = argv.split(' ', 1)
        if len(args) < 2:
            return self._("User ID and nickname are required.")
        self.client.changeNickname(args[1], args[0], args[0])
        return self._("Nickname of {0} is set to {1}.").format(*args)

    @catch_exceptions
    def set_group_title(self, argv: str) -> str:
        """GroupID title"""
        args = argv.split(' ', 1)
        if len(args) < 2:
            return self._("User ID and title are required.")
        self.client.changeThreadTitle(args[1], args[0], thread_type=ThreadType.GROUP)
        return self._("Title of group {0} is set to {1}.").format(*args)

    @catch_exceptions
    def set_chat_emoji(self, argv: str) -> str:
        """ChatID emoji"""
        args = argv.split(' ', 1)
        if len(args) < 2:
            return self._("User ID and emoji are required.")
        self.client.changeThreadEmoji(args[1], args[0])
        return self._("Emoji of group {0} is set to {1}.").format(*args)

    @catch_exceptions
    def set_member_nickname(self, argv: str) -> str:
        """GroupID MemberID nickname"""
        args = argv.split(' ', 2)
        if len(args) < 3:
            return self._("Group ID, member ID and are nickname required.")
        self.client.changeNickname(args[2], args[1], args[0])
        return self._("Nickname of {1} in {0} is set as {2}.").format(*args)
