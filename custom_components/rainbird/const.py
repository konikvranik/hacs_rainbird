"""Consts for Rain Bird Irrigation system LNK WiFi Module."""

import json
import os

DOMAIN = "rainbird"

DISPATCHER_UPDATE_ENTITY = DOMAIN + "_{entry_id}_update_{component_key}_{key}"
DISPATCHER_REMOVE_ENTITY = DOMAIN + "_{entry_id}_remove_{component_key}_{key}"
DISPATCHER_ON_LIST = DOMAIN + "_{entry_id}_on_list"
DISPATCHER_ON_DEVICE_UPDATE = DOMAIN + "_{entry_id}_on_device_update"
DISPATCHER_ON_STATE = DOMAIN + "_{entry_id}_on_state"

MANIFEST = json.load(open("%s/manifest.json" % os.path.dirname(os.path.realpath(__file__))))
VERSION = MANIFEST["version"]
DOMAIN = MANIFEST["domain"]
DEFAULT_NAME = MANIFEST["name"]

PLATFORM_SENSOR = "sensor"
PLATFORM_BINARY_SENSOR = "binary_sensor"
CONF_NUMBER_OF_STATIONS = "number_of_stations"
SENSOR_TYPES = {"rainsensor": ["Rain Sensor", None, "mdi:water"]}

CONF_RETRY_COUNT = "retry_count"
CONF_RETRY_DELAY = "retry_delay"

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
