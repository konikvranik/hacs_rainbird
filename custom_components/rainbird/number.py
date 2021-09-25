"""Support for Rain Bird Irrigation system LNK WiFi Module."""
import logging

import voluptuous as vol
from homeassistant.components.number import PLATFORM_SCHEMA, NumberEntity
from homeassistant.const import CONF_NAME
from homeassistant.helpers.typing import HomeAssistantType
from pyrainbird import RainbirdController

from . import RuntimeEntryData, DOMAIN, RainbirdEntity

_LOGGER = logging.getLogger(__name__)


def add_entities(config_entry, data: RuntimeEntryData, async_add_entities, hass: HomeAssistantType):
    async_add_entities([RainDelayEntity(hass, data.client, config_entry.data, data)], True)
    return True


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Rainbird number entities."""
    data = hass.data.get(DOMAIN)[config_entry.entry_id]
    await hass.async_add_executor_job(add_entities, config_entry, data, async_add_entities, hass)


class RainBirdNumber(RainbirdEntity, NumberEntity):
    """Representation of a Rain Bird number."""

    def __init__(self, hass, controller, name, unique_id, device_info, data, icon, attributes=None):
        """Initialize a Rain Bird Number Device."""
        super(RainBirdNumber, self).__init__(hass, controller, name, unique_id, device_info, data, icon, attributes)

        self._state = None

    @property
    def value(self):
        return self._state

class RainDelayEntity(RainBirdNumber):
    def __init__(self, hass, controller, device_info, data = None, attributes=None):
        super().__init__(hass, controller, "Rain Delay", "raindelay", device_info, data, "mdi:clock", attributes)

    @property
    def icon(self):
        return 'mdi:timer-outline' if self._state > 0 else 'mdi:timer-off-outline'

    @property
    def min_value(self):
        return 0

    @property
    def max_value(self):
        return 14

    @property
    def step(self):
        return 1

    @property
    def min_value(self):
        return 0

    @property
    def unit_of_measurement(self):
        return "days"

    def update(self):
        """Update switch status."""
        self._state = self._controller.get_rain_delay()

    def set_value(self, value: float):
        self._controller.set_rain_delay(int(value))
