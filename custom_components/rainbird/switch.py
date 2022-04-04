"""Support for Rain Bird Irrigation system LNK WiFi Module."""
import logging

import asyncio
import voluptuous as vol
from homeassistant.components.switch import PLATFORM_SCHEMA, SwitchEntity
from homeassistant.const import (
    CONF_FRIENDLY_NAME,
    CONF_SCAN_INTERVAL,
    CONF_SWITCHES,
    CONF_TRIGGER_TIME,
    CONF_ZONE, CONF_NAME, )
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import HomeAssistantType
from pyrainbird import RainbirdController

from . import RuntimeEntryData, DOMAIN, RainbirdEntity

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


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Rainbird switch entities."""
    data = hass.data.get(DOMAIN)[config_entry.entry_id]

    def _add_entities(future: asyncio.futures.Future):
        async_add_entities(future.result(), True)

    hass.async_add_executor_job(_get_entities, config_entry, data, hass).add_done_callback(_add_entities)


def _get_entities(config_entry, data: RuntimeEntryData, hass: HomeAssistantType):
    entities = []
    if data.number_of_stations:
        for i in range(data.number_of_stations):
            entities.append(RainBirdSwitch(data.client,
                                           {"zone": i, "id": config_entry.entry_id, **config_entry.data}, hass, data))
    else:
        i = 0
        stations = data.client.get_available_stations()
        if stations:
            for state in stations.stations.states:
                i = i + 1
                if state:
                    entities.append(RainBirdSwitch(data.client,
                                                   {"zone": i, "id": config_entry.entry_id, **config_entry.data}, hass,
                                                   data))
    return entities


class RainBirdSwitch(RainbirdEntity, SwitchEntity):
    """Representation of a Rain Bird switch."""

    def __init__(self, rb: RainbirdController, device_info: dict, hass: HomeAssistantType,
                 data: RuntimeEntryData = None):
        """Initialize a Rain Bird Switch Device."""
        self._zone = int(device_info.get(CONF_ZONE))
        self._duration = device_info.get(CONF_TRIGGER_TIME)
        super(RainBirdSwitch, self).__init__(hass, rb,
                                             "Zone {}".format(self._zone),
                                             "switch_%d" % self._zone,
                                             device_info, data, 'mdi:sprinkler-variant',
                                             attributes={"duration": self._duration, "zone": self._zone})
        self._state = None

    def turn_on(self, **kwargs):
        """Turn the switch on."""
        duration = kwargs["duration"] if "duration" in kwargs else self._duration
        response = self._controller.irrigate_zone(int(self._zone), int(duration // 60))
        if response:
            self._state = True

    def turn_off(self, **kwargs):
        """Turn the switch off."""
        response = self._controller.stop_irrigation()
        if response:
            self._state = False

    @property
    def is_on(self):
        """Return true if switch is on."""
        return self._state

    def update(self):
        """Update switch status."""
        self._state = self._controller.get_zone_state(self._zone)
