"""
Authorize user and store session into the correct path.
"""

import getpass
import argparse
import pickle
import os

from fbchat import Client
from ehforwarderbot import coordinator, utils

from .__version__ import __version__
from . import FBMessengerChannel

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--profile", help="Choose a profile to start with. ", default="default")

    args = parser.parse_args()
    profile = args.profile
    coordinator.profile = profile
    path = utils.get_data_path(FBMessengerChannel.channel_id)

    print("EFB Facebook Messenger Slave Session Updater")
    print("============================================")
    print()
    print("You are running EFMS %s." % __version__)
    print()
    print("This will update and overwrite your EFMS token by")
    print("log into your account again manually.")
    print()
    print("You usually need to do this when you want to log into")
    print("a new account, or when the previous session is expired.")
    print()
    print("This session is written to EFB profile \"%s\"," % profile)
    print("which has its EFMS data located at")
    print(path)
    print()
    print("To continue, press Enter/Return.")

    input()

    email = input("Email: ")
    password = getpass.getpass("Password: ")
    client = Client(email, password)

    if not client.isLoggedIn():
        print("Log in failed. Please check the information above and try again.")
        exit(1)

    session_path = os.path.join(path, "session.pickle")

    with open(session_path, 'wb') as f:
        pickle.dump(client.getSession(), f)

    print("Your session has been successfully updated. It's stored at")
    print(session_path)
    print("Your session cookies is as valuable as your account credential.")
    print("Please keep them with equal care.")

if __name__ == '__main__':
    main()