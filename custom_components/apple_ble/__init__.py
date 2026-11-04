"""The Apple BLE integration."""

from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval

from apple_ble import parse_key

from .const import (
    CONF_ENC_KEY,
    CONF_IRK,
    CONF_MODEL,
    CONF_RSSI_FLOOR,
    DEFAULT_RSSI_FLOOR,
    STALE_AFTER_SECONDS,
    TAP_REFRESH_SECONDS,
)
from .coordinator import AppleBleCoordinator
from .esphome_tap import EsphomeTap

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]

type AppleBleConfigEntry = ConfigEntry[AppleBleCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: AppleBleConfigEntry) -> bool:
    """Set up Apple BLE from a config entry."""
    opts = entry.options
    coordinator = AppleBleCoordinator(
        hass,
        model=entry.data.get(CONF_MODEL, ""),
        rssi_floor=entry.data.get(CONF_RSSI_FLOOR, DEFAULT_RSSI_FLOOR),
        irk=parse_key(opts[CONF_IRK]) if opts.get(CONF_IRK) else None,
        enc_key=parse_key(opts[CONF_ENC_KEY]) if opts.get(CONF_ENC_KEY) else None,
    )
    coordinator.entry_id = entry.entry_id

    @callback
    def _on_advert(
        service_info: BluetoothServiceInfoBleak,
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

    # HA's Bluetooth stack drops AirPods (0x07) adverts; read ESPHome proxies.
    tap = EsphomeTap(hass, coordinator.handle_payload)
    tap.refresh()
    entry.async_on_unload(tap.close)

    @callback
    def _async_tap(now: datetime) -> None:
        tap.refresh()

    entry.async_on_unload(
        async_track_time_interval(
            hass, _async_tap, timedelta(seconds=TAP_REFRESH_SECONDS)
        )
    )
    entry.async_on_unload(entry.add_update_listener(_async_reload))

    @callback
    def _async_tick(now: datetime) -> None:
        coordinator.refresh_presence()

    entry.async_on_unload(
        async_track_time_interval(
            hass, _async_tick, timedelta(seconds=STALE_AFTER_SECONDS)
        )
    )

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_reload(hass: HomeAssistant, entry: AppleBleConfigEntry) -> None:
    """Reload when keys change in the options flow."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: AppleBleConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
