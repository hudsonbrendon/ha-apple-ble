"""Coordinator that consumes passive Apple BLE adverts and tracks AirPods state."""

from __future__ import annotations

import logging
import time

from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send

from apple_ble import (
    APPLE_MANUFACTURER_ID,
    AirPodsData,
    DecryptedStatus,
    decrypt_status,
    parse_proximity_pairing,
    resolve_rpa,
)

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

    def __init__(
        self,
        hass: HomeAssistant,
        model: str,
        rssi_floor: int,
        irk: bytes | None = None,
        enc_key: bytes | None = None,
    ) -> None:
        """Initialize the coordinator."""
        self.hass = hass
        self.model = model  # "" => auto (strongest RSSI wins)
        self.rssi_floor = rssi_floor
        # With the IRK only *these* AirPods are accepted (no RSSI guessing);
        # with the EncKey batteries are exact and the connected host is known.
        self.irk = irk
        self.enc_key = enc_key
        self.data: AirPodsData | None = None
        self.decrypted: DecryptedStatus | None = None
        self.address: str | None = None
        self._state: dict[str, int | bool | None] = {}
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
        """Number of distinct Apple devices seen recently."""
        self._prune()
        return len(self._recent)

    @property
    def any_apple_nearby(self) -> bool:
        """Whether any Apple device was seen recently."""
        return self.apple_devices_nearby > 0

    @callback
    def handle_advert(self, service_info: BluetoothServiceInfoBleak) -> None:
        """Process one Apple BLE advert from HA's Bluetooth stack."""
        payload = (service_info.manufacturer_data or {}).get(APPLE_MANUFACTURER_ID)
        if payload is not None:
            self.handle_payload(service_info.address, service_info.rssi, bytes(payload))

    @callback
    def handle_payload(self, address: str, rssi: int, payload: bytes) -> None:
        """Process manufacturer_data[76] (type byte first) from any source."""
        mine = self.irk is not None and resolve_rpa(address, self.irk)
        if rssi < self.rssi_floor and not mine:
            return

        now = time.monotonic()
        # Presence: any Apple manufacturer-76 advert above the floor counts
        # (AirPods, Watch, iPhone, Mac). MAC rotation means we can't say which.
        self._prune()
        before = len(self._recent)
        self._recent[address] = now
        presence_changed = len(self._recent) != before

        parsed = parse_proximity_pairing(payload)
        airpods_changed = False
        if parsed is not None and self._accept(parsed, rssi, mine, now):
            decrypted = (
                decrypt_status(payload, self.enc_key, flipped=parsed.flipped)
                if mine and self.enc_key is not None
                else None
            )
            self.last_seen = now
            airpods_changed = parsed != self.data or (
                decrypted is not None
                and (
                    self.decrypted is None
                    or decrypted.raw[:7] != self.decrypted.raw[:7]
                )
            )
            self.data = parsed
            self.decrypted = decrypted
            self._merge(parsed, decrypted)
            self.best_rssi = rssi
            self.address = address

        if (airpods_changed or presence_changed) and self.entry_id is not None:
            async_dispatcher_send(self.hass, signal_updated(self.entry_id))

    def _accept(self, parsed: AirPodsData, rssi: int, mine: bool, now: float) -> bool:
        if self.irk is not None:
            return mine
        if self.model and parsed.model != self.model:
            return False
        stale = self.last_seen is None or (now - self.last_seen) > STALE_AFTER_SECONDS
        return (
            bool(self.model)
            or self.best_rssi is None
            or stale
            or rssi >= self.best_rssi
        )

    def _merge(self, parsed: AirPodsData, dec: DecryptedStatus | None) -> None:
        """Fold one frame into the sticky state.

        Each bud advertises on its own (rotating) address and a bud in a closed
        case goes silent, so the other bud reports it as unknown; keep the last
        known battery/charging per side instead of flapping to unknown.
        """
        src = dec or parsed
        st = self._state
        for side in ("left", "right", "case"):
            battery = getattr(src, f"{side}_battery")
            if battery is not None:
                st[f"{side}_battery"] = battery
                st[f"{side}_charging"] = getattr(src, f"{side}_charging")
        st["left_in_ear"] = parsed.left_in_ear
        st["right_in_ear"] = parsed.right_in_ear
        st["pods_in_case"] = parsed.pods_in_case
        if parsed.lid_open is not None:
            st["lid_open"] = parsed.lid_open
        elif parsed.left_in_ear and parsed.right_in_ear:
            st["lid_open"] = None  # both buds out: nothing reports the lid

    def value(self, field: str) -> int | bool | None:
        """Latest known value of an AirPods field (None until first advert)."""
        return self._state.get(field)
