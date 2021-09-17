# Rain Bird

Instructions on how to integrate your Rain Bird LNK WiFi Module within Home Assistant.

category: `Irrigation`, `Sensor`, `Switch`
ha_domain: rainbird
ha_platforms:
  - binary_sensor
  - sensor
  - switch


This `rainbird` integration allows interacting with [LNK WiFi](https://www.rainbird.com/products/lnk-wifi-module) module of the Rain Bird Irrigation system in Home Assistant.

There is currently support for the following device types within Home Assistant:

- [Binary Sensor](https://www.home-assistant.io/integrations/binary_sensor/)
- [Switch](https://www.home-assistant.io/integrations/switch)

## Installation

Copy the content of the `custom_components` folder to `custom_components` folder in your HA config directory or add this repository (`https://github.com/konikvranik/hacs_rainbird.git`) to your [HACS](https://github.com/hacs/integration) integration.

## Configuration

Use UI to add new integration. You can add multiple Rainbird controllers.

<div class='note'>
Please note that due to the implementation of the API within the LNK Module, there is a concurrency issue. For example, the Rain Bird app will give connection issues (like already a connection active).
</div>

## Binary Sensor

This `rainbird` sensor allows interacting with [LNK WiFi](https://www.rainbird.com/products/lnk-wifi-module) module of the Rain Bird Irrigation system in Home Assistant.

The integration adds `rainsensor` and `raindelay` sensors and their `binary_sensor` alternatives.

## Switch

This `rainbird` switch platform allows interacting with [LNK WiFi](https://www.rainbird.com/products/lnk-wifi-module) module of the Rain Bird Irrigation system in Home Assistant.

Switches are automatically added for all available zones of configured controllers.

## Services

The Rain Bird integration registers the `command` service, which allows you to sent arbitrary Rainbird commands to the controller.
Please see [commands in pyrainbird project](https://github.com/jbarrancos/pyrainbird/blob/master/pyrainbird/resources/sipcommands.json) for available commands

| Service | Description |
| ------- | ----------- |
| rainbird.command | Sends arbitrary Ainbird command to the controller |

