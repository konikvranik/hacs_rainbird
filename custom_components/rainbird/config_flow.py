"""Adds config flow for HDO."""
import datetime
import logging

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_HOST, CONF_MONITORED_CONDITIONS, CONF_TRIGGER_TIME, \
    CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.helpers import config_validation

from . import DOMAIN, CONF_NUMBER_OF_STATIONS, SENSOR_TYPES

_LOGGER = logging.getLogger(__name__)


@config_entries.HANDLERS.register(DOMAIN)
class HDOFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
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
            if user_input[CONF_HOST] != "":
                await self.async_set_unique_id(user_input[CONF_HOST])
                self._abort_if_unique_id_configured()
                self._data.update(user_input)
                # Call next step
                return self.async_create_entry(title=self._data[CONF_HOST], data=self._data)
            else:
                self._errors["base"] = "host"
        return self.async_show_form(
            step_id="user", data_schema=vol.Schema({
                vol.Required(CONF_HOST, default='rainbird.home'): str,
                vol.Optional(CONF_PASSWORD): str,
                vol.Optional(CONF_NUMBER_OF_STATIONS): int,
                vol.Optional(CONF_MONITORED_CONDITIONS,
                             default=list(SENSOR_TYPES.keys())): config_validation.multi_select(SENSOR_TYPES),
                vol.Optional(CONF_TRIGGER_TIME, default={"minutes": 2}): cv.positive_time_period_dict,
                vol.Optional(CONF_SCAN_INTERVAL, default={"minutes": 1}): cv.positive_time_period_dict
            })
        )

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
        if config_entry.unique_id is not None:
            return OptionsFlowHandler(config_entry)
        else:
            return EmptyOptions(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Change the configuration."""

    def __init__(self, config_entry):
        """Read the configuration and initialize data."""
        self.config_entry = config_entry
        self._data = dict(config_entry.options)
        self._errors = {}

    async def async_step_init(self, user_input=None):
        """Display the form, then store values and create entry."""

        if user_input is not None:
            # Update entry
            self._data.update(user_input)
            self._data[CONF_HOST] = self.config_entry.unique_id
            if CONF_PASSWORD in user_input:
                self._data[CONF_PASSWORD] = user_input[CONF_PASSWORD]
            return self.async_create_entry(title=self._data[CONF_HOST], data=self._data)
        else:
            return self.async_show_form(
                step_id="init", data_schema=vol.Schema({
                    vol.Optional(CONF_PASSWORD, default=self._data.get(CONF_PASSWORD, None)): str,
                    vol.Optional(CONF_NUMBER_OF_STATIONS, default=self._data.get(CONF_NUMBER_OF_STATIONS, None)): int,
                    vol.Optional(CONF_MONITORED_CONDITIONS,
                                 default=self._data.get(CONF_TRIGGER_TIME,
                                                        list(SENSOR_TYPES.keys()))): config_validation.multi_select(
                        SENSOR_TYPES),
                    vol.Optional(CONF_TRIGGER_TIME,
                                 default=self._data.get(CONF_TRIGGER_TIME,
                                                        {"minutes": 2})): cv.positive_time_period_dict,
                    vol.Optional(CONF_SCAN_INTERVAL,
                                 default=self._data.get(CONF_SCAN_INTERVAL,
                                                        {"minutes": 1})): cv.positive_time_period_dict
                })
            )


class EmptyOptions(config_entries.OptionsFlow):
    """Empty class in to be used if no configuration."""

    def __init__(self, config_entry):
        """Initialize data."""
        self.config_entry = config_entry
