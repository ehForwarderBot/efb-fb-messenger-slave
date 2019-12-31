
EFB Facebook Messenger 从端 (EFMS)
**********************************

.. image:: https://img.shields.io/pypi/v/efb-fb-messenger-slave.svg
   :target: https://pypi.org/project/efb-fb-messenger-slave/
   :alt: PyPI release

.. image:: https://d322cqt584bo4o.cloudfront.net/ehforwarderbot/localized.svg
   :target: https://crowdin.com/project/ehforwarderbot/
   :alt: Translate this project

.. image:: https://efms.1a23.studio/raw/master/banner.png
   :alt: Banner

`其他语言的 README <./readme_translations>`_.

**信道 ID**: ``blueset.fbmessenger``

EFMS 是一个基于模拟 Facebook Messenger 网页端和 `fbchat
<https://github.com/carpedm20/fbchat>`_ 将 Facebook Messenger 与 EH
Forwarder Bot 连接起来的信道。


测试版
======

该从端非稳定版本，且其功能随时可能会被更改。


依赖
====

* Python >= 3.6

* EH Forwarder Bot >= 2.0.0


使用步骤
========

1. 安装所需的依赖

2. 安装

    ::
       pip3 install efb-fb-messenger-slave

3. 在配置档案中的 ``config.yaml`` 中启用信道。

    该路径可能因您的配置档案而有所不同。

    **（在 EFB 2.0.0a1 中，默认的配置档案路径为**
    ``~/.ehforwarderbot/profiles/default`` **）**

4. 登录

    ::
       $ efms-auth

    然后跟随提示进行操作。


已知问题
========

* 无法处理来自 ``MARTTPLACE`` 类型（例如，来自 Facebook 市场上的相关买家的消息）的会话消息。

* 无法正确更新实时位置。

* 投票消息、提醒和活动尚未支持。

* 没有计划支持语音通话。


可选的配置文件
==============

EFMS
允许用户通过配置文件来启用或关闭实验性功能。位置：``<当前配置档案路径>/blueset.fbmessenger/config.yaml``。


示例
----

::

   # Experimental flags
   # This section can be used to enable experimental functionality.
   # However, those features may be changed or removed at any time.
   # Options in this section is explained afterward.
   flags:
       option_one: 10
       option_two: false
       option_three: "foobar"


提示与技巧
==========

* 要发送大号 emoji，请在 emoji 后面添加``S``、``M`` 或 ``L`` 作为发送小号、中号和大号
  emoji。例如，要发送一个大号微笑 emoji，输入``😆L`` 来发送。


实验性功能
==========

以下的实验性功能随时可能被更改或被删除，请自行承担相关风险。

* ``proxy_links_by_facebook`` *(bool)* [默认值：``false``]

  使用 Facebook 代理发送链接（包括共享内容和缩略图里的链接）。禁用此选项直接显示来源。

* ``send_link_with_description`` *(bool)* [默认值：``false``]

  当处理来自主端的链接消息时，将附带发送标题与描述。

  注解: 无论是否选择此选项，链接消息将作为文本发送，Facebook Messenger 可能会或不会根据其系统设置附加自带的链接预览。

* ``show_pending_threads`` *(bool)* [默认值：``false``]

  显示会话列表时，包括待批准的会话。

* ``show_archived_threads`` *(bool)* [默认值：``false``]

  显示会话列表时，包括已归档的会话。


供应商特定选项（``vendor_specific``）
=====================================

EFMS 的会话提供了以下供应商特定选项：

* ``'chat_type'`` *(str)*: 会话类型：``'User'``、``'Page'`` 或 ``'Group'``。

* ``'profile_picture_url'`` *(str)*: 会话头像链接


License
=======

EFMS is licensed under `GNU Affero General Public License 3.0
<https://www.gnu.org/licenses/agpl-3.0.txt>`_ or later versions:

::

   EFB Facebook Messenger Slave Channel: A slave channel for EH Forwarder Bot.
   Copyright (C) 2016 - 2020 Eana Hufwe, and the EFB Facebook Messenger Slave Channel contributors
   All rights reserved.

   This program is free software: you can redistribute it and/or modify
   it under the terms of the GNU Affero General Public License as
   published by the Free Software Foundation, either version 3 of the
   License, or any later version.

   This program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.

   You should have received a copy of the GNU Affero General Public License
   along with this program.  If not, see <http://www.gnu.org/licenses/>.


翻译支持
========

EFMS supports translated user interface prompts, by setting the locale
environmental variable (``LANGUAGE``, ``LC_ALL``, ``LC_MESSAGES`` or
``LANG``) to one of our \ `supported languages
<https://crowdin.com/project/ehforwarderbot/>`_. Meanwhile, you can
help to translate this project into your languages on `our Crowdin
page <https://crowdin.com/project/ehforwarderbot/>`_.

注解: If your are installing from source code, you will not get
   translations of the user interface without manual compile of
   message catalogs (``.mo``) prior to installation.
