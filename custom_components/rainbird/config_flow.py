"""Adds config flow for HDO."""
import datetime
import logging

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_HOST, CONF_MONITORED_CONDITIONS, CONF_TRIGGER_TIME, \
    CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowHandler

from . import DOMAIN, CONF_NUMBER_OF_STATIONS, SENSOR_TYPES

_LOGGER = logging.getLogger(__name__)


async def show_form(flow: FlowHandler, step: str, first_time: bool, data=None):
    if data is None:
        data = {}
    dict_ = {}
    if first_time:
        dict_.update({vol.Required(CONF_HOST, default='rainbird.home'): str})
    dict_.update({
        vol.Optional(CONF_PASSWORD, default=data.get(CONF_PASSWORD, None)): str,
        vol.Optional(CONF_NUMBER_OF_STATIONS, default=data.get(CONF_NUMBER_OF_STATIONS, 0)): int,
        vol.Optional(CONF_MONITORED_CONDITIONS,
                     default=data.get(CONF_MONITORED_CONDITIONS, list(SENSOR_TYPES.keys()))): cv.multi_select(
            SENSOR_TYPES),
        vol.Optional(CONF_TRIGGER_TIME,
                     default=data.get(CONF_TRIGGER_TIME, {"minutes": 2})): cv.positive_time_period_dict,
        vol.Optional(CONF_SCAN_INTERVAL,
                     default=data.get(CONF_SCAN_INTERVAL, {"seconds": 20})): cv.positive_time_period_dict
    })
    return flow.async_show_form(
        step_id=step, data_schema=vol.Schema(dict_), description_placeholders={"host": data.get(CONF_HOST, '')}
    )


def time_to_secs(data, key):
    if key in data and type(data[key]) == dict:
        data[key] = datetime.timedelta(data[key])
    if key in data and type(data[key]) == datetime.timedelta:
        data[key] = int(data[key].total_seconds())


def secs_to_dime_dict(data: int) -> dict:
    return {"seconds": data % 60, "minutes": int(data / 60) % 60, "hours": int(data / 3600)}


@config_entries.HANDLERS.register(DOMAIN)
class ConfigFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Rainbird."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        """Initialize."""
        self._errors = {}
        self._data = {}

    async def async_step_user(self, user_input=None):  # pylint: disable=dangerous-default-value
        """Display the form, then store values and create entry."""
        self._errors = {}
        if user_input is not None:
            if user_input[CONF_HOST]:
                await self.async_set_unique_id(user_input[CONF_HOST])
                self._abort_if_unique_id_configured()
                time_to_secs(user_input, CONF_TRIGGER_TIME)
                time_to_secs(user_input, CONF_SCAN_INTERVAL)
                self._data.update(user_input)
                # Call next step
                return self.async_create_entry(title=self._data[CONF_HOST], data=self._data)
            else:
                self._errors["base"] = "host"
        return await show_form(self, "user", True)

    async def async_step_import(self, user_input):  # pylint: disable=unused-argument
        """Import a config entry.

        Special type of import, we're not actually going to store any data.
        Instead, we're going to rely on the values that are in config file.
        """
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        return self.async_create_entry(title="configuration.yaml", data={})

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return the options flow handler."""
        if config_entry.unique_id is None:
            return EmptyOptions(config_entry)
        else:
            return OptionsFlowHandler(config_entry)


def time_to_dict(data, key):
    if key in data and type(data[key]) == int:
        data.update({key: secs_to_dime_dict(data[key])})


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Change the configuration."""

    def __init__(self, config_entry):
        """Read the configuration and initialize data."""
        self.config_entry = config_entry
        config_entry.options = dict(config_entry.data, **config_entry.options)
        self._data = dict(config_entry.options)
        self._errors = {}

    async def async_step_init(self, user_input=None):
        """Display the form, then store values and create entry."""

        if user_input is None:
            time_to_dict(self._data, CONF_TRIGGER_TIME)
            time_to_dict(self._data, CONF_SCAN_INTERVAL)
            return await show_form(self, "init", False, self._data)
        else:
            # Update entry
            self._data.update(user_input)
            time_to_secs(self._data, CONF_TRIGGER_TIME)
            time_to_secs(self._data, CONF_SCAN_INTERVAL)
            return self.async_create_entry(title=self._data[CONF_HOST], data=self._data)


class EmptyOptions(config_entries.OptionsFlow):
    """Empty class in to be used if no configuration."""

    def __init__(self, config_entry):
        """Initialize data."""
        self.config_entry = config_entry
