"""Coordinator that consumes passive Apple BLE adverts and tracks AirPods state."""

from __future__ import annotations

import logging
import time
from typing import Any

from apple_ble import AirPodsData, APPLE_MANUFACTURER_ID, parse_proximity_pairing
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import DOMAIN, STALE_AFTER_SECONDS

_LOGGER = logging.getLogger(__name__)


def signal_updated(entry_id: str) -> str:
    """Dispatcher signal fired when new AirPods data arrives."""
    return f"{DOMAIN}_{entry_id}_updated"


class AppleBleCoordinator:
    """Holds the latest AirPods state derived from BLE adverts.

    Not a DataUpdateCoordinator: data is push-driven by the Bluetooth callback,
    and there is no stable device to poll (MAC randomizes).
    """

    def __init__(self, hass: HomeAssistant, model: str, rssi_floor: int) -> None:
        self.hass = hass
        self.model = model  # "" => auto (strongest RSSI wins)
        self.rssi_floor = rssi_floor
        self.data: AirPodsData | None = None
        self.best_rssi: int | None = None
        self.last_seen: float | None = None
        self.entry_id: str | None = None
        self._recent: dict[str, float] = {}  # address -> last-seen monotonic time

    def _prune(self) -> None:
        cutoff = time.monotonic() - STALE_AFTER_SECONDS
        self._recent = {a: t for a, t in self._recent.items() if t >= cutoff}

    @callback
    def refresh_presence(self) -> None:
        """Re-evaluate presence on a timer; notify if the count changed."""
        before = len(self._recent)
        self._prune()
        if len(self._recent) != before and self.entry_id is not None:
            async_dispatcher_send(self.hass, signal_updated(self.entry_id))

    @property
    def apple_devices_nearby(self) -> int:
        self._prune()
        return len(self._recent)

    @property
    def any_apple_nearby(self) -> bool:
        return self.apple_devices_nearby > 0

    @callback
    def handle_advert(self, service_info: BluetoothServiceInfoBleak) -> None:
        """Process one Apple BLE advert (BluetoothServiceInfoBleak)."""
        if service_info.rssi < self.rssi_floor:
            return
        payload = (service_info.manufacturer_data or {}).get(APPLE_MANUFACTURER_ID)
        if payload is None:
            return

        now = time.monotonic()
        # Presence: any Apple manufacturer-76 advert above the floor counts
        # (AirPods, Watch, iPhone, Mac). MAC rotation means we can't say which.
        self._prune()
        before = len(self._recent)
        self._recent[service_info.address] = now
        presence_changed = len(self._recent) != before

        parsed = parse_proximity_pairing(bytes(payload))
        airpods_changed = False
        if parsed is not None and not (self.model and parsed.model != self.model):
            stale = self.last_seen is None or (now - self.last_seen) > STALE_AFTER_SECONDS
            accept = (
                bool(self.model)
                or self.best_rssi is None
                or stale
                or service_info.rssi >= self.best_rssi
            )
            if accept:
                self.last_seen = now
                airpods_changed = parsed != self.data
                self.data = parsed
                self.best_rssi = service_info.rssi

        if (airpods_changed or presence_changed) and self.entry_id is not None:
            async_dispatcher_send(self.hass, signal_updated(self.entry_id))
