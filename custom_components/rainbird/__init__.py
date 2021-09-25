"""Support for Rain Bird Irrigation system LNK WiFi Module."""

import logging

import attr
import homeassistant
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components import binary_sensor, switch, number
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, CONF_HOST, CONF_PASSWORD, CONF_MONITORED_CONDITIONS, CONF_TRIGGER_TIME, \
    CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.helpers import config_validation
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.typing import HomeAssistantType
from pyrainbird import ModelAndVersion, RainbirdController
from voluptuous import ALLOW_EXTRA

from .const import DOMAIN, SENSOR_TYPES, CONF_NUMBER_OF_STATIONS, RAINBIRD_MODELS, CONF_RETRY_DELAY, CONF_RETRY_COUNT


SCHEMA = {
    vol.Required(CONF_NAME): cv.string,
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Optional(CONF_NUMBER_OF_STATIONS): int,
    vol.Optional(CONF_MONITORED_CONDITIONS): config_validation.multi_select(SENSOR_TYPES),
    vol.Optional(CONF_TRIGGER_TIME): int,
    vol.Optional(CONF_SCAN_INTERVAL): int,
    vol.Optional(CONF_RETRY_COUNT): int,
    vol.Optional(CONF_RETRY_DELAY): int
}

CONFIG_SCHEMA = vol.Schema({vol.Optional(DOMAIN): vol.Schema(SCHEMA)}, extra=ALLOW_EXTRA)
_LOGGER = logging.getLogger(__name__)

def get_rainbird_controller(data):
    return RainbirdController(
        data[CONF_HOST],
        data[CONF_PASSWORD],
        update_delay=data[CONF_SCAN_INTERVAL],
        retry_sleep=data[CONF_RETRY_DELAY],
        retry=data[CONF_RETRY_COUNT])

async def async_setup_entry(hass: HomeAssistantType, config_entry):
    """Set up rainbird from a config entry."""
    _LOGGER.debug(config_entry)
    config = CONFIG_SCHEMA({DOMAIN: dict(config_entry.data)})
    _LOGGER.debug(config)

    rainbird_api = get_rainbird_controller(config_entry.data)
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    hass_data_rainbird_ = hass.data[DOMAIN]
    hass_data_rainbird_[config_entry.entry_id] = RuntimeEntryData(
        client=rainbird_api,
        entry_id=config_entry.entry_id,
        serial=config_entry.entry_id,
        number_of_stations=config_entry.data.get(CONF_NUMBER_OF_STATIONS, None)
    )
    if 'controllers' not in hass_data_rainbird_:
        hass_data_rainbird_['controllers'] = {}
    hass_data_controllers_ = hass_data_rainbird_['controllers']
    hass_data_controllers_[config_entry.entry_id] = rainbird_api

    @callback
    def update_model_and_version():
        hass_data_rainbird_[config_entry.entry_id].model_and_version = rainbird_api.get_model_and_version()
        hass_data_rainbird_[config_entry.entry_id].serial = rainbird_api.get_serial_number()

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
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(config_entry, homeassistant.components.number.DOMAIN))
    # Return boolean to indicate that initialization was successfully.
    return True


async def async_remove_entry(hass, config_entry):
    """Handle removal of an entry."""
    try:
        await hass.config_entries.async_forward_entry_unload(config_entry,
                                                             homeassistant.components.binary_sensor.DOMAIN)
        await hass.config_entries.async_forward_entry_unload(config_entry, homeassistant.components.switch.DOMAIN)
        await hass.config_entries.async_forward_entry_unload(config_entry, homeassistant.components.number.DOMAIN)
        _LOGGER.info("Successfully removed sensor from the HDO integration")
    except ValueError:
        pass


async def update_listener(hass, config_entry):
    """Update listener."""
    config_entry.data = config_entry.options
    await hass.config_entries.async_forward_entry_unload(config_entry, homeassistant.components.binary_sensor.DOMAIN)
    await hass.config_entries.async_forward_entry_unload(config_entry, homeassistant.components.switch.DOMAIN)
    await hass.config_entries.async_forward_entry_unload(config_entry, homeassistant.components.number.DOMAIN)
    await hass.config_entries.async_forward_entry_setup(config_entry, homeassistant.components.binary_sensor.DOMAIN)
    await hass.config_entries.async_forward_entry_setup(config_entry, homeassistant.components.switch.DOMAIN)
    await hass.config_entries.async_forward_entry_setup(config_entry, homeassistant.components.number.DOMAIN)


@attr.s
class RuntimeEntryData:
    """Store runtime data for rainbird config entries."""

    entry_id = attr.ib(type=str)
    client = attr.ib(type=RainbirdController)
    number_of_stations = attr.ib(type=int)
    model_and_version = attr.ib(type=ModelAndVersion, init=False)
    serial = attr.ib(type=str)

    def get_version(self):
        return "%d.%d" % (
            self.model_and_version.major,
            self.model_and_version.minor) if self.model_and_version else "UNKNOWN"

    def get_model(self):
        if self.model_and_version and self.model_and_version.model in RAINBIRD_MODELS:
            return RAINBIRD_MODELS[self.model_and_version.model][2]
        else:
            return "UNKNOWN MODEL"


class RainbirdEntity(Entity):
    def __init__(self, hass, controller, name, unique_id, device_info, data, icon, attributes=None):
        self._hass = hass
        self._controller = controller
        self._name = "{} {}".format(device_info.get(CONF_NAME), name)
        self._unique_id = "{}_{}_{}".format(DOMAIN, data.serial, unique_id)
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
            "identifiers": {(DOMAIN, self._data.serial)},
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

    @property
    def unique_id(self):
        """Return Unique ID string."""
        return self._unique_id
