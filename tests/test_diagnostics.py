from unittest.mock import patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.apple_ble.const import (
    CONF_MODEL,
    CONF_RSSI_FLOOR,
    DEFAULT_RSSI_FLOOR,
    DOMAIN,
)
from custom_components.apple_ble.diagnostics import (
    async_get_config_entry_diagnostics,
)


async def test_diagnostics_redacts_unique_id(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="AirPods Pro",
        data={CONF_MODEL: "AirPods Pro", CONF_RSSI_FLOOR: DEFAULT_RSSI_FLOOR},
        unique_id="apple_ble_airpods_pro",
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.apple_ble.bluetooth.async_register_callback",
        return_value=lambda: None,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    diag = await async_get_config_entry_diagnostics(hass, entry)
    assert diag["entry"]["unique_id"] == "**REDACTED**"
    assert diag["entry"]["data"][CONF_MODEL] == "AirPods Pro"
    assert diag["data"] is None
    assert diag["apple_devices_nearby"] == 0
