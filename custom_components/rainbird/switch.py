"""Support for Rain Bird Irrigation system LNK WiFi Module."""
import logging
from typing import Any, Coroutine

import asyncio
import voluptuous as vol
from homeassistant.components.switch import PLATFORM_SCHEMA, SwitchEntity
from homeassistant.const import (
    CONF_FRIENDLY_NAME,
    CONF_SCAN_INTERVAL,
    CONF_SWITCHES,
    CONF_TRIGGER_TIME,
    CONF_ZONE, CONF_HOST, )
from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.helpers.typing import HomeAssistantType
from pyrainbird import RainbirdController
from homeassistant.exceptions import HomeAssistantError

from . import RuntimeEntryData, DOMAIN, RainbirdEntity

CONF_ZONE_RUN_TIME = "zone_run_time"
DEFAULT_ZONE_RUN = 120

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
    """Set up ESPHome binary sensors based on a config entry."""
    data = hass.data.get(DOMAIN)[config_entry.entry_id]

    def _add_entities(future: asyncio.futures.Future):
        async_add_entities(future.result(), True)

    hass.async_add_executor_job(_get_entities, config_entry, data, hass).add_done_callback(_add_entities)
    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service("start_zone", {
        vol.Optional(
            CONF_ZONE_RUN_TIME, default=DEFAULT_ZONE_RUN
        ): cv.positive_int
    }, "async_start_zone")


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
        self._attr_duration = device_info.get(CONF_TRIGGER_TIME)
        super(RainBirdSwitch, self).__init__(hass, rb, device_info.get("id"),
                                             device_info.get(CONF_FRIENDLY_NAME, "Rainbird {} #{}").format(
                                                 device_info.get(CONF_HOST), self._zone), data, 'mdi:sprinkler-variant',
                                             attributes={"duration": self._attr_duration, "zone": self._zone})
        self._state = None

    @property
    def unique_id(self):
        """Return Unique ID string."""
        return "%s_switch_%d" % (DOMAIN, self._zone)

    def turn_on(self, **kwargs):
        """Turn the switch on."""
        duration = kwargs["duration"] if "duration" in kwargs else self._attr_duration
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

    async def async_start_zone(self, *, zone_run_time: int) -> None:
        """Start a particular zone for a certain amount of time."""
        await self.async_turn_on(duration=zone_run_time)
