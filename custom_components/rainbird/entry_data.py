"""Runtime entry data for ESPHome stored in hass.data."""

import attr

from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.typing import HomeAssistantType
from . import DOMAIN

DISPATCHER_UPDATE_ENTITY = DOMAIN + "_{entry_id}_update_{component_key}_{key}"
DISPATCHER_REMOVE_ENTITY = DOMAIN + "_{entry_id}_remove_{component_key}_{key}"
DISPATCHER_ON_LIST = DOMAIN + "_{entry_id}_on_list"
DISPATCHER_ON_DEVICE_UPDATE = DOMAIN + "_{entry_id}_on_device_update"
DISPATCHER_ON_STATE = DOMAIN + "_{entry_id}_on_state"


@attr.s
class RuntimeEntryData:
    """Store runtime data for rainbird config entries."""

    entry_id = attr.ib(type=str)
    client = attr.ib(type="RainbirdController")

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


def _attr_obj_from_dict(cls, **kwargs):
    return cls(**{key: kwargs[key] for key in attr.fields_dict(cls) if key in kwargs})
