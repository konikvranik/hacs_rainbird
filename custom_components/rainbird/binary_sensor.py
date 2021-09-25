"""Support for Rain Bird Irrigation system LNK WiFi Module."""
from __future__ import annotations

import logging

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.binary_sensor import PLATFORM_SCHEMA, BinarySensorEntity
from homeassistant.const import CONF_MONITORED_CONDITIONS
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
    """Set up Rainbird binary sensors."""
    runtime_data = hass.data.get(DOMAIN)[config_entry.entry_id]
    controller = runtime_data.client
    sensor = BiStateRainBirdSensor(hass, controller, config_entry.data, runtime_data)
    async_add_entities([sensor], True)


class BiStateRainBirdSensor(RainbirdEntity, BinarySensorEntity):
    """A sensor implementation for Rain Bird device."""

    def __init__(self, hass, controller, device_info, data = None):
        """Initialize the Rain Bird sensor."""
        self._sensor_type = "rainsensor"
        name = SENSOR_TYPES[self._sensor_type][0]
        super(BiStateRainBirdSensor, self).__init__(hass, controller, name, self._sensor_type, device_info,
                                                    data,
                                                    SENSOR_TYPES[self._sensor_type][2])
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
