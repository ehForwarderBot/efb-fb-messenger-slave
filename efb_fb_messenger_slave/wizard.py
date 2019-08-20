from gettext import translation
from io import StringIO

import bullet
import cjkwrap
from bullet import YesNo, Numbers, Bullet
from pkg_resources import resource_filename
from ruamel.yaml import YAML

from ehforwarderbot import coordinator, utils
from ehforwarderbot.types import ModuleID
from . import FBMessengerChannel
from .__main__ import run


def print_wrapped(text):
    paras = text.split("\n")
    for i in paras:
        print(*cjkwrap.wrap(i), sep="\n")


translator = translation("efb_fb_messenger_slave",
                         resource_filename("efb_fb_messenger_slave", "locale"),
                         fallback=True)

_ = translator.gettext
ngettext = translator.ngettext


class DataModel:
    data: dict

    def __init__(self, profile: str, instance_id: str):
        coordinator.profile = profile
        self.profile = profile
        self.instance_id = instance_id
        self.channel_id = FBMessengerChannel.channel_id
        if instance_id:
            self.channel_id = ModuleID(self.channel_id + "#" + instance_id)
        self.config_path = utils.get_config_path(self.channel_id)
        self.session_path = utils.get_data_path(self.channel_id) / "session.pickle"
        self.yaml = YAML()
        if not self.config_path.exists():
            self.build_default_config()
        else:
            self.data = self.yaml.load(self.config_path.open())

    def build_default_config(self):
        # TRANSLATORS: This part of text must be formatted in a monospaced font and no line shall exceed the width of a 70-cell-wide terminal.
        s = _(
            "# =======================================================\n"
            "# EFB Facebook Messenger Slave Channel Configuration File\n"
            "# =======================================================\n"
            "#\n"
            "# This file can help you to adjust some experimental features provided in\n"
            "# EFMS. It is not required to have this file for EFMS to work.\n"
        )
        s += "\n"
        s += "flags: {}"

        str_io = StringIO(s)
        str_io.seek(0)
        self.data = self.yaml.load(str_io)

    def save(self):
        with self.config_path.open('w') as f:
            self.yaml.dump(self.data, f)


def setup_account(data):
    print_wrapped(_(
        "Log in to your Facebook (Messenger) account\n"
        "-------------------------------------------"
    ))
    print()
    if data.session_path.exists():
        print_wrapped(_(
            "We find that you have successfully logged in once before. "
            "You don't need to log in again if everything is already "
            "working properly."
        ))

        widget = bullet.YesNo(prompt=_("Do you want to log in again? "),
                              prompt_prefix="[yN] ")
        if not widget.launch(default="n"):
            return
    run(data.profile, data.instance_id)


flags_settings = {
    "proxy_links_by_facebook":
        (False, 'bool', None,
         _('Deliver links (including links in share entities and thumbnails) '
           'using Facebook’s proxy. Disable this option to show the source '
           'directly.')
         ),
    "send_link_with_description":
        (False, 'bool', None,
         _('When processing link message from the Master Channel, attach '
           'the title and description besides the link when the option is '
           'enabled.\n'
           '\n'
           'Note: Regardless of this option, link messages are sent as text, '
           'and Facebook Messenger may or may not attach its own link '
           'preview per its system configuration.')
         ),
    "show_pending_threads":
        (False, 'bool', None,
         _('When showing the threads list, include threads '
           'pending approval.')
         ),
    "show_archived_threads":
        (False, 'bool', None,
         _('When showing the threads list, include archived threads.')
         )
}


def setup_experimental_flags(data):
    print()
    print_wrapped(_(
        "EFMS has also provided some experimental features that you can use. "
        "They are not required to be enabled for EFMS to work."
    ))

    widget = YesNo(prompt=_("Do you want to config experimental features? "),
                   prompt_prefix="[yN] ")
    if not widget.launch(default="n"):
        return

    for key, value in flags_settings.items():
        default, cat, params, desc = value
        if data.data['flags'].get(key) is not None:
            default = data.data['flags'].get(key)
        if cat == 'bool':
            prompt_prefix = '[Yn] ' if default else '[yN] '
            print()
            print(key)
            print_wrapped(desc)

            ans = YesNo(prompt=f"{key}? ",
                        prompt_prefix=prompt_prefix) \
                .launch(default='y' if default else 'n')

            data.data['flags'][key] = ans
        elif cat == 'int':
            print()
            print(key)
            print_wrapped(desc)
            ans = Numbers(prompt=f"{key} [{default}]? ") \
                .launch(default=default)
            data.data['flags'][key] = ans
        elif cat == 'choices':
            print()
            print(key)
            print_wrapped(desc)
            ans = Bullet(prompt=f"{key}?", choices=params) \
                .launch(default=default)
            data.data['flags'][key] = ans

    print(_("Saving configurations..."), end="", flush=True)
    data.save()
    print(_("OK"))


def wizard(profile, instance_id):
    data = DataModel(profile, instance_id)

    print_wrapped(_(
        "=================================================\n"
        "EFB Facebook Messenger Slave Channel Setup Wizard\n"
        "=================================================\n"
        "\n"
        "This wizard will guide you to setup your EFB Facebook Messenger "
        "Slave channel (EFMS). This would be really quick and simple."
    ))
    print()
    setup_account(data)
    setup_experimental_flags(data)

    print()
    print_wrapped(_(
        "Congratulations! You have finished the setup wizard for EFB Facebook "
        "Messenger Slave channel."
    ))
