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


async def test_charging_binary_sensors(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="AirPods Pro",
        data={CONF_MODEL: "AirPods Pro", CONF_RSSI_FLOOR: DEFAULT_RSSI_FLOOR},
        unique_id="apple_ble_airpods_pro",
    )
    entry.add_to_hass(hass)
    captured = {}

    with patch(
        "custom_components.apple_ble.bluetooth.async_register_callback",
        side_effect=lambda h, cb, m, mode: captured.update(cb=cb) or (lambda: None),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    captured["cb"](_Info("AA:BB:CC:00:00:02", -50, {76: _payload()}), None)
    await hass.async_block_till_done()

    # charge nibble '3' = 0b0011, not flipped: left & right charging, case not.
    assert hass.states.get("binary_sensor.airpods_pro_left_charging").state == "on"
    assert hass.states.get("binary_sensor.airpods_pro_right_charging").state == "on"
    assert hass.states.get("binary_sensor.airpods_pro_case_charging").state == "off"
    # An AirPods advert is also an Apple manufacturer-76 advert, so presence is on.
    assert hass.states.get("binary_sensor.airpods_pro_apple_device_nearby").state == "on"
