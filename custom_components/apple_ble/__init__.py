"""The Apple BLE integration."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval

from .const import CONF_MODEL, CONF_RSSI_FLOOR, DEFAULT_RSSI_FLOOR, DOMAIN, STALE_AFTER_SECONDS
from .coordinator import AppleBleCoordinator

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Apple BLE from a config entry."""
    coordinator = AppleBleCoordinator(
        hass,
        model=entry.data.get(CONF_MODEL, ""),
        rssi_floor=entry.data.get(CONF_RSSI_FLOOR, DEFAULT_RSSI_FLOOR),
    )
    coordinator.entry_id = entry.entry_id

    @callback
    def _on_advert(
        service_info: bluetooth.BluetoothServiceInfoBleak,
        change: bluetooth.BluetoothChange,
    ) -> None:
        coordinator.handle_advert(service_info)

    entry.async_on_unload(
        bluetooth.async_register_callback(
            hass,
            _on_advert,
            {"manufacturer_id": 76, "connectable": False},
            bluetooth.BluetoothScanningMode.PASSIVE,
        )
    )

    @callback
    def _async_tick(now) -> None:
        coordinator.refresh_presence()

    entry.async_on_unload(
        async_track_time_interval(
            hass, _async_tick, timedelta(seconds=STALE_AFTER_SECONDS)
        )
    )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded
