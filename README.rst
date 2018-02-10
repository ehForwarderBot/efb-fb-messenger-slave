EFB Facebook Messenger Slave (EFMS)
===================================

.. image:: https://img.shields.io/pypi/v/efb-fb-messenger-slave.svg
   :alt: PyPI release
   :target: https://pypi.org/project/efb-fb-messenger-slave/
.. image:: https://d322cqt584bo4o.cloudfront.net/ehforwarderbot/localized.svg
   :alt: Translate this project
   :target: https://crowdin.com/project/ehforwarderbot/

**Channel ID**: ``blueset.fbmessenger``

EFMS is a channel that connects to Facebook Messenger for EH Forwarder
Bot, based on simulation of Facebook Messenger Web, and
`fbchat <https://github.com/carpedm20/fbchat>`_.

Beta version
-------------

This is an unstable beta version, and its functionality may change at any
time.

Requirements
------------

-  Python >= 3.6
-  EH Forwarder Bot >= 2.0.0

Getting started
---------------

1. Install required binary dependencies
2. Install

   .. code:: shell

       pip3 install efb-fb-messenger-slave

3. Enable the channel in the profile’s ``config.yaml``.

   The path to the current profile may vary depends on your
   configuration.

   **(In EFB 2.0.0a1, the default profile path is**
   ``~/.ehforwarderbot/profiles/default`` **)**

4. Sign in

   .. code:: shell

       $ efms-auth

   And follow the instructions.

Optional configuration file
---------------------------

EFMS allows user to enable or disable experimental features with the
configuration file. It is located at
``<Path to current profile>/blueset.fbmessenger/config.yaml``.

Example
~~~~~~~

.. code:: yaml

    # Experimental flags
    # This section can be used to enable experimental functionality.
    # However, those features may be changed or removed at any time.
    # Options in this section is explained afterward.
    flags:
        option_one: 10
        option_two: false
        option_three: "foobar"

Tips and tricks
---------------

-  To react to a message, reply (target) to the message with one of the
   following commands:

   -  ``r`LOVE`` for 😍
   -  ``r`SMILE`` for 😆
   -  ``r`WOW`` for 😮
   -  ``r`SAD`` for 😢
   -  ``r`ANGRY`` for 😠
   -  ``r`YES`` for 👍
   -  ``r`NO`` for 👎

-  To send large emoji, send the emoji as text following by ``S``,
   ``M``, or ``L`` as small, medium and large emoji accordingly.

Experimental flags
------------------

The following flags are experimental features, may change, break, or
disappear at any time. Use at your own risk.

-  ``proxy_links_by_facebook`` *(bool)* [Default: ``true``]

   Deliver links (including links in share entities and thumbnails)
   using Facebook’s proxy. Disable this option to show the source
   directly.

-  ``send_link_with_description`` *(bool)* [Default: ``false``]

   When processing link message from the Master Channel, attach the
   title and description besides the link when the option is enabled.

   .. note::
        Regardless of this option, link messages are sent as text, and
        Facebook Messenger may or may not attach its own link preview per its
        system configuration.*

-  ``show_pending_threads`` *(bool)* [Default: ``false``]

   When showing the threads list, include threads pending approval.

-  ``show_archived_threads`` *(bool)* [Default: ``false``]

   When showing the threads list, include archived threads.

Vendor-specifics
----------------

EFMS’s chats provides the following vendor specific options:

* ``'chat_type'`` *(str)*: Type of the thread: ``'User'``, ``'Page'``, or
  ``'Group'``.
* ``'profile_picture_url'`` *(str)*: URL to the thread’s
  profile picture.

Experimental localization support
---------------------------------

EFMS supports localized user interface prompts experimentally,
by setting the locale environmental variable (``LANGUAGE``,
``LC_ALL``, ``LC_MESSAGES`` or ``LANG``) to one of our
`supported languages`_. Meanwhile, you can help to translate
this project into your languages on `our Crowdin page`_.

.. _supported languages: https://crowdin.com/project/ehforwarderbot/
.. _our Crowdin page: https://crowdin.com/project/ehforwarderbot/