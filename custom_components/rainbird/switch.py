"""Support for Rain Bird Irrigation system LNK WiFi Module."""

import logging

import voluptuous as vol
from homeassistant.components.switch import PLATFORM_SCHEMA, SwitchEntity
from homeassistant.const import (
    CONF_FRIENDLY_NAME,
    CONF_SCAN_INTERVAL,
    CONF_SWITCHES,
    CONF_TRIGGER_TIME,
    CONF_ZONE, )
from homeassistant.helpers import config_validation as cv
from pyrainbird import RainbirdController

from . import RuntimeEntryData, DOMAIN

_LOGGER = logging.getLogger(__name__)
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
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


def add_entities(config_entry, data: RuntimeEntryData, async_add_entities, hass):
    if data.number_of_stations:
        for i in range(data.number_of_stations):
            switch = RainBirdSwitch(data.client, {"zone": i, "id": config_entry.entry_id}, hass, data)
            async_add_entities([switch], True)
    else:
        cnt = 0
        for state in data.client.get_available_stations().stations.states:
            cnt = cnt + 1
            if state:
                switch = RainBirdSwitch(data.client, {"zone": cnt, "id": config_entry.entry_id}, hass, data)
                async_add_entities([switch], True)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up ESPHome binary sensors based on a config entry."""
    data = hass.data.get(DOMAIN)[config_entry.entry_id]
    await hass.async_add_executor_job(add_entities, config_entry, data, async_add_entities, hass)


class RainBirdSwitch(SwitchEntity):
    """Representation of a Rain Bird switch."""

    def __init__(self, rb: RainbirdController, dev, hass, data: RuntimeEntryData = None):
        """Initialize a Rain Bird Switch Device."""
        self._data = data
        self._hass = hass
        self._rainbird = rb
        self._zone = int(dev.get(CONF_ZONE))
        self._device_id = dev.get("id")
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

    @property
    def unique_id(self):
        """Return Unique ID string."""
        return "%s_switch_%d" % (DOMAIN, self._zone)

    @property
    def device_info(self):
        """Information about this entity/device."""

        return {
            "identifiers": {(DOMAIN, self._device_id)},
            # If desired, the name for the device could be different to the entity
            "name": "Rainbird controller",
            "sw_version": self._data.get_version(),
            "model": self._data.get_version(),
            "manufacturer": "Rainbird",
        }

    def turn_on(self, **kwargs):
        """Turn the switch on."""
        response = self._rainbird.irrigate_zone(int(self._zone), int(self._duration))
        if response and response["type"] == "AcknowledgeResponse":
            self._state = True

    def turn_off(self, **kwargs):
        """Turn the switch off."""
        response = self._rainbird.stop_irrigation()
        if response and response["type"] == "AcknowledgeResponse":
            self._state = False

    def get_device_status(self):
        """Get the status of the switch from Rain Bird Controller."""
        response = self._rainbird.get_current_irrigation()
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
