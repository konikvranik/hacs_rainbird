"""Support for Rain Bird Irrigation system LNK WiFi Module."""

import logging

import voluptuous as vol
from pyrainbird import RainbirdController

from homeassistant.components.switch import PLATFORM_SCHEMA, SwitchDevice
from homeassistant.const import (
    CONF_FRIENDLY_NAME,
    CONF_SCAN_INTERVAL,
    CONF_SWITCHES,
    CONF_TRIGGER_TIME,
    CONF_ZONE, CONF_PASSWORD, CONF_HOST,
)
from homeassistant.helpers import config_validation as cv
from . import SCHEMA

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    SCHEMA.extend(
        {vol.Required(CONF_SWITCHES, default={}): vol.Schema(
            {
                cv.string: {
                    vol.Optional(CONF_FRIENDLY_NAME): cv.string,
                    vol.Required(CONF_ZONE): cv.string,
                    vol.Required(CONF_TRIGGER_TIME): cv.string,
                    vol.Optional(CONF_SCAN_INTERVAL): cv.string,
                }
            }
        )}
    )
)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up ESPHome binary sensors based on a config entry."""
    switch = RainBirdSwitch(RainbirdController(config_entry.data[CONF_HOST], config_entry.data[CONF_PASSWORD]),
                            config_entry.data)
    config_entry.unique_id = switch.unique_id
    async_add_entities([switch], True)


class RainBirdSwitch(SwitchDevice):
    """Representation of a Rain Bird switch."""

    def __init__(self, rb, dev):
        """Initialize a Rain Bird Switch Device."""
        self._rainbird = rb
        self._zone = int(dev.get(CONF_ZONE))
        self._name = dev.get(CONF_FRIENDLY_NAME, "Sprinkler {}".format(self._zone))
        self._state = None
        self._duration = dev.get(CONF_TRIGGER_TIME)
        self._attributes = {"duration": self._duration, "zone": self._zone}

    @property
    def device_state_attributes(self):
        """Return state attributes."""
        return self._attributes

    @property
    def name(self):
        """Get the name of the switch."""
        return self._name

    def turn_on(self, **kwargs):
        """Turn the switch on."""
        response = self._rainbird.startIrrigation(int(self._zone), int(self._duration))
        if response and response["type"] == "AcknowledgeResponse":
            self._state = True

    def turn_off(self, **kwargs):
        """Turn the switch off."""
        response = self._rainbird.stopIrrigation()
        if response and response["type"] == "AcknowledgeResponse":
            self._state = False

    def get_device_status(self):
        """Get the status of the switch from Rain Bird Controller."""
        response = self._rainbird.currentIrrigation()
        if response is None:
            return None
        if isinstance(response, dict) and "sprinklers" in response:
            return response["sprinklers"][self._zone]

    def update(self):
        """Update switch status."""
        self._state = self.get_device_status()

    @property
    def is_on(self):
        """Return true if switch is on."""
        return self._state
