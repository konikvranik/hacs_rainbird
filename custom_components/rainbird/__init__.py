"""Support for Rain Bird Irrigation system LNK WiFi Module."""

import json
import logging
import os

import attr
import homeassistant
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components import binary_sensor, switch
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_MONITORED_CONDITIONS, CONF_TRIGGER_TIME, \
    CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.helpers import config_validation
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.typing import HomeAssistantType
from pyrainbird import ModelAndVersion, RainbirdController
from voluptuous import ALLOW_EXTRA

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
PLATFORM_BINARY_SENSOR = "binary_sensor"
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


async def async_setup_entry(hass: HomeAssistantType, config_entry):
    """Set up ESPHome binary sensors based on a config entry."""
    _LOGGER.debug(config_entry)
    config = CONFIG_SCHEMA({DOMAIN: dict(config_entry.data)})
    _LOGGER.debug(config)

    host_ = config_entry.data[CONF_HOST]
    cli = RainbirdController(host_, config_entry.data[CONF_PASSWORD],
                             update_delay=config_entry.data[CONF_SCAN_INTERVAL], retry_sleep=3, retry=7)
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    hass_data_raibird_ = hass.data[DOMAIN]
    hass_data_raibird_[config_entry.entry_id] = RuntimeEntryData(client=cli, entry_id=config_entry.entry_id,
                                                                 number_of_stations=config_entry.data.get(
                                                                     CONF_NUMBER_OF_STATIONS, None))
    if 'controllers' not in hass_data_raibird_:
        hass_data_raibird_['controllers'] = {}
    hass_data_controllers_ = hass_data_raibird_['controllers']
    hass_data_controllers_[host_] = cli

    @callback
    def update_model_and_version():
        hass_data_raibird_[config_entry.entry_id].model_and_version = cli.get_model_and_version()

    await hass.async_add_executor_job(update_model_and_version)

    async def rainbird_command_call(call):
        params = call.data['parameters']
        if params is None:
            params = []
        elif not isinstance(params, list):
            params = [params]

        response = await hass.async_add_executor_job(hass_data_controllers_[call.data['host']].command,
                                                     call.data['command'], *params)
        hass.bus.async_fire("rainbird_command_response_event", {'id': call.data['id'], 'response': response})

    @callback
    def rainbird_command_service(call):
        """Rainbird command service."""
        hass.async_create_task(rainbird_command_call(call))

    # Register our service with Home Assistant.
    hass.services.async_register(DOMAIN, "command", rainbird_command_service)
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(config_entry, homeassistant.components.binary_sensor.DOMAIN))
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(config_entry, homeassistant.components.switch.DOMAIN))
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
        await hass.config_entries.async_forward_entry_unload(config_entry,
                                                             homeassistant.components.binary_sensor.DOMAIN)
        await hass.config_entries.async_forward_entry_unload(config_entry, homeassistant.components.switch.DOMAIN)
        _LOGGER.info("Successfully removed sensor from the HDO integration")
    except ValueError:
        pass


async def update_listener(hass, config_entry):
    """Update listener."""
    config_entry.data = config_entry.options
    await hass.config_entries.async_forward_entry_unload(config_entry, homeassistant.components.binary_sensor.DOMAIN)
    await hass.config_entries.async_forward_entry_unload(config_entry, homeassistant.components.switch.DOMAIN)
    await hass.config_entries.async_forward_entry_setup(config_entry, homeassistant.components.binary_sensor.DOMAIN)
    await hass.config_entries.async_forward_entry_setup(config_entry, homeassistant.components.switch.DOMAIN)


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


class RainbirdEntity(Entity):
    def __init__(self, hass, controller, device_id, name, data, icon, attributes=None):
        self._hass = hass
        self._controller = controller
        self._device_id = device_id
        self._name = name
        self._data = data
        self._icon = icon
        self._attributes = attributes

    @property
    def name(self):
        """Return the name of this camera."""
        return self._name

    @property
    def device_info(self):
        """Information about this entity/device."""

        return {
            "identifiers": {(DOMAIN, self._device_id)},
            # If desired, the name for the device could be different to the entity
            "name": "Rainbird controller",
            "sw_version": self._data.get_version(),
            "model": self._data.get_model(),
            "manufacturer": "Rainbird",
        }

    @property
    def extra_state_attributes(self):
        """Return state attributes."""
        return self._attributes

    @property
    def icon(self):
        """Return icon."""
        return self._icon
