# coding=utf-8

"""
Authorize user and store session into the correct path.
"""

import getpass
import argparse
import pickle
import os
from gettext import translation
from pkg_resources import resource_filename

from fbchat import Client
from ehforwarderbot import coordinator, utils

from .__version__ import __version__
from . import FBMessengerChannel


def main():
    translation("efb_fb_messenger_slave",
                resource_filename("efb_fb_messenger_slave", "locale"),
                fallback=True).install()

    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--profile", help=_("Target profile."), default="default")
    parser.add_argument("-i", "--instance", help=_("Target instance ID."), default=None)

    args = parser.parse_args()
    profile = args.profile
    coordinator.profile = profile
    channel_id = FBMessengerChannel.channel_id
    if args.instance:
        channel_id += f"#{args.instance}"
    path = utils.get_data_path(channel_id)

    print(_("EFB Facebook Messenger Slave Session Updater\n"
            "============================================"))
    print()
    print(_("You are running EFMS {0}.").format(__version__))
    print()
    print(_("This will update and overwrite your EFMS token by\n"
            "log into your account again manually."))
    print()
    print(_("You usually need to do this when you want to log into\n"
            "a new account, or when the previous session is expired."))
    print()
    print(_("This session is written to\n"
            "{0}").format(path))
    print()
    print(_("To continue, press Enter/Return."))

    input()

    email = input(_("Email: "))
    password = getpass.getpass(_("Password: "))
    client = Client(email, password)

    if not client.isLoggedIn():
        print(_("Log in failed. Please check the information above and try again."))
        exit(1)

    session_path = os.path.join(path, "session.pickle")

    with open(session_path, 'wb') as f:
        pickle.dump(client.getSession(), f)

    print(_("Your session has been successfully updated. It's stored at\n"
            "{0}").format(session_path))
    print(_("Your session cookies is as valuable as your account credential.\n"
            "Please keep them with equal care."))


if __name__ == '__main__':
    main()
