from dataclasses import dataclass
from unittest.mock import patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.apple_ble.const import (
    CONF_MODEL,
    CONF_RSSI_FLOOR,
    DEFAULT_RSSI_FLOOR,
    DOMAIN,
)


@dataclass
class _Info:
    address: str
    rssi: int
    manufacturer_data: dict
    name: str = "AirPods"


def _payload() -> bytes:
    hexstr = "0719070e2070a93601000045121212"
    hexstr = hexstr + "0" * (54 - len(hexstr))
    return bytes.fromhex(hexstr)


async def _setup(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="AirPods Pro",
        data={CONF_MODEL: "AirPods Pro", CONF_RSSI_FLOOR: DEFAULT_RSSI_FLOOR},
        unique_id="apple_ble_airpods_pro",
    )
    entry.add_to_hass(hass)
    captured = {}

    def _fake_register(hass_, cb, matcher, mode):
        captured["cb"] = cb
        return lambda: None

    with patch(
        "custom_components.apple_ble.bluetooth.async_register_callback",
        side_effect=_fake_register,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry, captured


async def test_battery_sensors_populate_after_advert(hass):
    _, captured = await _setup(hass)
    # Feed one advert through the registered callback.
    captured["cb"](_Info("AA:BB:CC:00:00:02", -50, {76: _payload()}), None)
    await hass.async_block_till_done()

    left = hass.states.get("sensor.airpods_pro_left_battery")
    right = hass.states.get("sensor.airpods_pro_right_battery")
    case = hass.states.get("sensor.airpods_pro_case_battery")
    assert left.state == "90"
    assert right.state == "100"
    assert case.state == "60"
    assert left.attributes["device_class"] == "battery"
    assert left.attributes["unit_of_measurement"] == "%"


async def test_battery_unknown_before_any_advert(hass):
    await _setup(hass)
    left = hass.states.get("sensor.airpods_pro_left_battery")
    assert left.state == "unknown"


async def test_apple_nearby_count_sensor(hass):
    _, captured = await _setup(hass)
    captured["cb"](_Info("AA:BB:CC:00:00:20", -55, {76: b"\x10\x05abcd"}), None)
    captured["cb"](_Info("AA:BB:CC:00:00:21", -60, {76: b"\x10\x05wxyz"}), None)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.airpods_pro_apple_devices_nearby")
    assert state.state == "2"
