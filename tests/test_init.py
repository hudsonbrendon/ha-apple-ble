from unittest.mock import patch

from homeassistant.config_entries import ConfigEntryState
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.apple_ble.const import (
    CONF_MODEL,
    CONF_RSSI_FLOOR,
    DEFAULT_RSSI_FLOOR,
    DOMAIN,
)


async def test_setup_and_unload(hass):
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
    ) as reg:
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert reg.called

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED
