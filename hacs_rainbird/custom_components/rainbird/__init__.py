"""Support for Rain Bird Irrigation system LNK WiFi Module."""
import logging

import voluptuous as vol
from pyrainbird import RainbirdController
from voluptuous import ALLOW_EXTRA

import homeassistant.helpers.config_validation as cv
from entry_data import RuntimeEntryData
from homeassistant import config_entries
from homeassistant.components import sensor, switch
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.core import callback
from homeassistant.helpers.typing import HomeAssistantType

_LOGGER = logging.getLogger(__name__)

DATA_RAINBIRD = "rainbird"
DOMAIN = "rainbird"
PLATFORM_SENSOR = "sensor"
SCHEMA = {vol.Required(CONF_HOST): cv.string, vol.Required(CONF_PASSWORD): cv.string}
CONFIG_SCHEMA = vol.Schema({vol.Optional(DOMAIN): vol.Schema(SCHEMA)}, extra=ALLOW_EXTRA)


async def async_setup_entry(hass, entry):
    """Set up ESPHome binary sensors based on a config entry."""
    _LOGGER.debug(entry)
    config = CONFIG_SCHEMA({DOMAIN: dict(entry.data)})
    _LOGGER.debug(config)

    cli = RainbirdController(entry.data[CONF_HOST], entry.data[CONF_PASSWORD])
    entry_data = hass.data[DOMAIN][entry.entry_id] = RuntimeEntryData(client=cli, entry_id=entry.entry_id)

    @callback
    def irrigation_start(call):
        """My first service."""
        _LOGGER.debug("Called HDO: %s", call)
        zone = call.data["zone"]
        response = entry_data.client.startIrrigation(int(zone), int(call.data["duration"]))
        if response and response["type"] == "AcknowledgeResponse":
            return True

    # Register our service with Home Assistant.
    hass.services.async_register(DOMAIN, "start_irrigation", irrigation_start)
    hass.services.async_register(DOMAIN, "set_rain_delay", irrigation_start)
    hass.async_create_task(hass.config_entries.async_forward_entry_setup(entry, sensor.DOMAIN))
    hass.async_create_task(hass.config_entries.async_forward_entry_setup(entry, switch.DOMAIN))
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


def setup(hass, config):
    """Set up the Rain Bird component."""
    conf = config[DOMAIN]
    server = conf.get(CONF_HOST)
    password = conf.get(CONF_PASSWORD)

    from pyrainbird import RainbirdController

    controller = RainbirdController(server, password)

    _LOGGER.debug("Rain Bird Controller set to: %s", server)

    initial_status = controller.currentIrrigation()
    if initial_status and initial_status["type"] != "CurrentStationsActiveResponse":
        _LOGGER.error("Error getting state. Possible configuration issues")
        return False

    hass.data[DATA_RAINBIRD] = controller
    return True
