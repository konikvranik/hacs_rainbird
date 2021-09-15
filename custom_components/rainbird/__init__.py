"""Support for Rain Bird Irrigation system LNK WiFi Module."""
import datetime
import json
import logging
import os

import attr
import homeassistant
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components import sensor, switch
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_MONITORED_CONDITIONS, CONF_TRIGGER_TIME, \
    CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.helpers import config_validation
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.typing import HomeAssistantType
from voluptuous import ALLOW_EXTRA

from pyrainbird import ModelAndVersion, RainbirdController

DOMAIN = "rainbird"

DISPATCHER_UPDATE_ENTITY = DOMAIN + "_{entry_id}_update_{component_key}_{key}"
DISPATCHER_REMOVE_ENTITY = DOMAIN + "_{entry_id}_remove_{component_key}_{key}"
DISPATCHER_ON_LIST = DOMAIN + "_{entry_id}_on_list"
DISPATCHER_ON_DEVICE_UPDATE = DOMAIN + "_{entry_id}_on_device_update"
DISPATCHER_ON_STATE = DOMAIN + "_{entry_id}_on_state"

_LOGGER = logging.getLogger(__name__)

MANIFEST = json.load(open("%s/manifest.json" % os.path.dirname(os.path.realpath(__file__))))
VERSION = MANIFEST["version"]
DOMAIN = MANIFEST["domain"]
DEFAULT_NAME = MANIFEST["name"]

PLATFORM_SENSOR = "sensor"
CONF_NUMBER_OF_STATIONS = "number_of_stations"
SENSOR_TYPES = {"rainsensor": ["Rainsensor", None, "mdi:water"]}

SCHEMA = {
    vol.Required(CONF_HOST): cv.string, vol.Required(CONF_PASSWORD): cv.string,
    vol.Optional(CONF_NUMBER_OF_STATIONS): int,
    vol.Optional(CONF_MONITORED_CONDITIONS): config_validation.multi_select(SENSOR_TYPES),
    vol.Optional(CONF_TRIGGER_TIME): int,
    vol.Optional(CONF_SCAN_INTERVAL): int
}
CONFIG_SCHEMA = vol.Schema({vol.Optional(DOMAIN): vol.Schema(SCHEMA)}, extra=ALLOW_EXTRA)

RAINBIRD_MODELS = {
    0x003: ["ESP_RZXe", 0, "ESP-RZXe", False, 0, 6],
    0x007: ["ESP_ME", 1, "ESP-Me", True, 4, 6],
    0x006: ["ST8X_WF", 2, "ST8x-WiFi", False, 0, 6],
    0x005: ["ESP_TM2", 3, "ESP-TM2", True, 3, 4],
    0x008: ["ST8X_WF2", 4, "ST8x-WiFi2", False, 8, 6],
    0x009: ["ESP_ME3", 5, "ESP-ME3", True, 4, 6],
    0x010: ["MOCK_ESP_ME2", 6, "ESP=Me2", True, 4, 6],
    0x00A: ["ESP_TM2v2", 7, "ESP-TM2", True, 3, 4],
    0x10A: ["ESP_TM2v3", 8, "ESP-TM2", True, 3, 4],
    0x099: ["TBOS_BT", 9, "TBOS-BT", True, 3, 8],
    0x107: ["ESP_MEv2", 10, "ESP-Me", True, 4, 6],
    0x103: ["ESP_RZXe2", 11, "ESP-RZXe2", False, 8, 6]
}


async def async_setup_entry(hass: HomeAssistantType, entry):
    """Set up ESPHome binary sensors based on a config entry."""
    _LOGGER.debug(entry)
    config = CONFIG_SCHEMA({DOMAIN: dict(entry.data)})
    _LOGGER.debug(config)

    cli = RainbirdController(entry.data[CONF_HOST], entry.data[CONF_PASSWORD])
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    entry_data = hass.data[DOMAIN][entry.entry_id] = RuntimeEntryData(client=cli, entry_id=entry.entry_id,
                                                                      number_of_stations=entry.data.get(
                                                                          CONF_NUMBER_OF_STATIONS, None))

    @callback
    def update_model_and_version():
        hass.data[DOMAIN][entry.entry_id].model_and_version = cli.get_model_and_version()

    await hass.async_add_executor_job(update_model_and_version)

    @callback
    def irrigation_start(call):
        """My first service."""
        _LOGGER.debug("Called HDO: %s", call)
        zone = call.data["zone"]
        response = entry_data.client.irrigate_zone(int(zone), int(call.data["duration"]))
        if response and response["type"] == "AcknowledgeResponse":
            return True

    # Register our service with Home Assistant.
    hass.services.async_register(DOMAIN, "start_irrigation", irrigation_start)
    hass.services.async_register(DOMAIN, "set_rain_delay", irrigation_start)
    hass.async_create_task(hass.config_entries.async_forward_entry_setup(entry, homeassistant.components.sensor.DOMAIN))
    hass.async_create_task(hass.config_entries.async_forward_entry_setup(entry, homeassistant.components.switch.DOMAIN))
    # Return boolean to indicate that initialization was successfully.
    return True


async def platform_async_setup_entry(
        hass: HomeAssistantType,
        config_entry: ConfigEntry,
        async_add_entities,
        *,
        component_key: str,
        info_type,
        entity_type,
        state_type,
) -> bool:
    """Set up this integration using UI."""
    if config_entry.source == config_entries.SOURCE_IMPORT:
        # We get here if the integration is set up using YAML
        hass.async_create_task(hass.config_entries.async_remove(config_entry.entry_id))
        return False
    # Print startup message
    config_entry.options = config_entry.data
    config_entry.add_update_listener(update_listener)
    # Add sensor
    return await hass.config_entries.async_forward_entry_setup(config_entry, DOMAIN)


async def async_remove_entry(hass, config_entry):
    """Handle removal of an entry."""
    try:
        await hass.config_entries.async_forward_entry_unload(config_entry, DOMAIN)
        _LOGGER.info("Successfully removed sensor from the HDO integration")
    except ValueError:
        pass


async def update_listener(hass, entry):
    """Update listener."""
    entry.data = entry.options
    await hass.config_entries.async_forward_entry_unload(entry, DOMAIN)
    hass.async_add_job(hass.config_entries.async_forward_entry_setup(entry, DOMAIN))


@attr.s
class RuntimeEntryData:
    """Store runtime data for rainbird config entries."""

    entry_id = attr.ib(type=str)
    client = attr.ib(type=RainbirdController)
    number_of_stations = attr.ib(type=int)
    model_and_version = attr.ib(type=ModelAndVersion, init=False)

    def get_version(self):
        return "%d.%d" % (
            self.model_and_version.major,
            self.model_and_version.minor) if self.model_and_version else "UNKNOWN"

    def get_model(self):
        return RAINBIRD_MODELS[self.model_and_version.model][
            2] if self.model_and_version and self.model_and_version.model in RAINBIRD_MODELS else "UNKNOWN MODEL"

    def async_update_entity(
            self, hass: HomeAssistantType, component_key: str, key: int
    ) -> None:
        """Schedule the update of an entity."""
        signal = DISPATCHER_UPDATE_ENTITY.format(
            entry_id=self.entry_id, component_key=component_key, key=key
        )
        async_dispatcher_send(hass, signal)

    def async_remove_entity(
            self, hass: HomeAssistantType, component_key: str, key: int
    ) -> None:
        """Schedule the removal of an entity."""
        signal = DISPATCHER_REMOVE_ENTITY.format(
            entry_id=self.entry_id, component_key=component_key, key=key
        )
        async_dispatcher_send(hass, signal)

    def async_update_device_state(self, hass: HomeAssistantType) -> None:
        """Distribute an update of a core device state like availability."""
        signal = DISPATCHER_ON_DEVICE_UPDATE.format(entry_id=self.entry_id)
        async_dispatcher_send(hass, signal)
