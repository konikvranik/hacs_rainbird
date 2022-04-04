"""Support for Rain Bird Irrigation system LNK WiFi Module."""
from __future__ import annotations

import logging

import asyncio
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.binary_sensor import PLATFORM_SCHEMA, BinarySensorEntity
from homeassistant.const import CONF_MONITORED_CONDITIONS
from homeassistant.helpers.typing import HomeAssistantType
from pyrainbird import RainbirdController

from . import SENSOR_TYPES, DOMAIN, RuntimeEntryData, RainbirdEntity

_LOGGER = logging.getLogger(__name__)

# sensor_type [ description, unit, icon ]

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_MONITORED_CONDITIONS, default=list(SENSOR_TYPES)): vol.All(
            cv.ensure_list, [vol.In(SENSOR_TYPES)]
        )
    }
)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Rainbird binary sensor entities."""
    data = hass.data.get(DOMAIN)[config_entry.entry_id]
    
    def _add_entities(future: asyncio.futures.Future):
        async_add_entities(future.result(), True)

    hass.async_add_executor_job(_get_entities, config_entry, data, hass).add_done_callback(_add_entities)


def _get_entities(config_entry, data: RuntimeEntryData, hass: HomeAssistantType):
    return [BiStateRainBirdSensor(data.client, config_entry.data, hass, data)]


class BiStateRainBirdSensor(RainbirdEntity, BinarySensorEntity):
    """A sensor implementation for Rain Bird device."""

    def __init__(self, rb: RainbirdController, device_info: dict, hass: HomeAssistantType,
                data: RuntimeEntryData = None):
        """Initialize the Rain Bird sensor."""
        self._sensor_type = "rainsensor"
        sensor_attrs = SENSOR_TYPES[self._sensor_type]
        name = sensor_attrs[0]
        icon = sensor_attrs[2]

        super(BiStateRainBirdSensor, self).__init__(hass, rb, name, self._sensor_type, device_info, data, icon)
        self._state = None

    def update(self):
        """Get the latest data and updates the states."""
        _LOGGER.debug("Updating sensor: %s", self._name)
        self._sensor_type = self._controller.get_rain_sensor_state()

    @property
    def unique_id(self):
        """Return Unique ID string."""
        return "%s_%s" % (DOMAIN, self._sensor_type)

    @property
    def icon(self):
        return 'mdi:water-check' if self.is_on else 'mdi:water-remove-outline'

    @property
    def device_class(self):
        return "moisture"

    @property
    def is_on(self):
        return self._state
