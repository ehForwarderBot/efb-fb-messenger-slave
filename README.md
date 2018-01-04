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

## Optional Configuration File
EFMS allows user to enable or disable experimental 
features with the configuration file. It is located at
`<Path to current profile>/ehforwarderbot.channels.slave.blueset.wechat/config.yaml`. 
The path to the current profile may vary depends on
your configuration.

__(In EFB 2.0.0a1, the default profile path is `~/.ehforwarderbot/profiles/defualt`)__

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
  may or may not attach its own link preview based on
  its system configuration._