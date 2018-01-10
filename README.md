# EFB Facebook Messenger Slave (EFMS)
<!-- badges -->

**Channel ID**: `ehforwarderbot.channels.slave.blueset.fbmessenger.FBMessengerChannel`

EFMS is a channel that connects to Facebook Messenger for 
EH Forwarder Bot, based on simulation of Facebook Messenger Web,
and [`fbchat`](https://github.com/carpedm20/fbchat).

## Alpha version
This is an unstable alpha version, and functionality may 
change at any time.

## Requirements
* Python >= 3.5
* EH Forwarder Bot >= 2.0.0
<!-- Other requirements go here -->

## Getting started

1. Install required binary dependencies
1. Install

    ```shell
    pip3 install efb-fb-messenger-slave
    ```
2. Enable the channel in the profile's `config.yaml`.
   
    The path to the current profile may vary depends on
    your configuration.

    __(In EFB 2.0.0a1, the default profile path is `~/.ehforwarderbot/profiles/defualt`)__
    
3. Sign in

    ```shell
    python3 -m ehforwarderbot.channels.slave.blueset.fbmessenger
    ```
    
    And follow the instructions.

## Optional configuration file
EFMS allows user to enable or disable experimental 
features with the configuration file. It is located at
`<Path to current profile>/ehforwarderbot.channels.slave.blueset.wechat/config.yaml`. 

### Example

```yaml
# Experimental flags
# This section can be used to enable experimental functionality.
# However, those features may be changed or removed at any time.
# Options in this section is explained afterward.
flags:
    option_one: 10
    option_two: false
    option_three: "foobar"
```

## Tips and tricks
* To react to a message, reply (target) to the message with
  one of the following commands:
    * <code>r\`LOVE</code> for 😍
    * <code>r\`SMILE</code> for 😆
    * <code>r\`WOW</code> for 😮
    * <code>r\`SAD</code> for 😢
    * <code>r\`ANGRY</code> for 😠
    * <code>r\`YES</code> for 👍
    * <code>r\`NO</code> for 👎
* To send large emoji, send the emoji as text following by
  `S`, `M`, or `L` as small, medium and large emoji
  accordingly.

## Experimental flags
The following flags are experimental features, may change, 
break, or disappear at any time. Use at your own risk.

* `proxy_links_by_facebook` _(bool)_  [Default: `true`]  
  Deliver links (including links in share entities and 
  thumbnails) using Facebook's proxy. Disable this option
  to show the source directly._
* `send_link_with_description` _(bool)_ [Default: `false`]  
  When processing link message from the Master Channel, 
  attach the title and description besides the link when
  the option is enabled. _Note: Regardless of this option,
  link messages are sent as text, and Facebook Messenger
  may or may not attach its own link preview per
  its system configuration._
* `show_pending_threads` _(bool)_ [Default: `false`]  
  When showing the threads list, include threads pending 
  approval.
* `show_archived_threads` _(bool)_ [Default: `false`]  
  When showing the threads list, include archived threads.