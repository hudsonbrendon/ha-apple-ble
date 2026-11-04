"""Read Apple 0x07 adverts straight from ESPHome Bluetooth proxies.

Home Assistant's Bluetooth manager (habluetooth) drops every Apple-only advert
whose first byte is not 0x02/0x06/0x10/0x11/0x12 before any integration sees it,
so AirPods proximity-pairing (0x07) adverts never reach a bluetooth callback.
The filter is compiled Cython and cannot be patched, but every ESPHome proxy
already streams raw adverts to HA; we add a second, passive handler on that
same API connection. No extra subscription is sent, and removing the handler
never unsubscribes HA's own scanner.
"""

from __future__ import annotations

from collections.abc import Callable
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, callback

try:  # shipped with HA's esphome integration; absent if never installed
    from aioesphomeapi.api_pb2 import BluetoothLERawAdvertisementsResponse
except ImportError:  # pragma: no cover
    BluetoothLERawAdvertisementsResponse = None

_LOGGER = logging.getLogger(__name__)

_APPLE_PP_PREFIX = b"\x4c\x00\x07"  # company id 0x004C (LE) + type 0x07

type RawCallback = Callable[[str, int, bytes], None]


def apple_payloads(ad: bytes) -> list[bytes]:
    """Return manufacturer_data[76] payloads (type byte first) that are 0x07."""
    out = []
    i = 0
    while i + 1 < len(ad) and ad[i]:
        end = i + 1 + ad[i]
        if ad[i + 1] == 0xFF and ad[i + 2 : i + 5] == _APPLE_PP_PREFIX:
            out.append(ad[i + 4 : end])
        i = end
    return out


def _fmt_addr(value: int) -> str:
    return ":".join(f"{b:02X}" for b in value.to_bytes(6, "big"))


class EsphomeTap:
    """Keeps one passive raw-advert handler per ESPHome proxy connection."""

    def __init__(self, hass: HomeAssistant, on_advert: RawCallback) -> None:
        """Initialize the tap."""
        self.hass = hass
        self._on_advert = on_advert
        self._attached: dict[str, tuple[Any, Callable[[], None]]] = {}

    @callback
    def _handle(self, msg: BluetoothLERawAdvertisementsResponse) -> None:
        advs = msg.advertisements
        for i in range(len(advs)):  # see bleak_esphome: avoid protobuf __iter__
            adv = advs[i]
            for payload in apple_payloads(adv.data):
                self._on_advert(_fmt_addr(adv.address), adv.rssi, payload)

    @callback
    def refresh(self) -> None:
        """(Re)attach to every connected ESPHome proxy; call periodically.

        ponytail: polled from the coordinator tick instead of hooking ESPHome
        reconnect events; worst case we miss ~30 s after a proxy reconnects.
        """
        if BluetoothLERawAdvertisementsResponse is None:
            return
        for entry in self.hass.config_entries.async_entries("esphome"):
            conn = None
            if entry.state is ConfigEntryState.LOADED:
                data = getattr(entry, "runtime_data", None)
                try:
                    if data is not None and data.available:
                        conn = data.client._get_connection()
                except Exception:
                    conn = None
            current = self._attached.get(entry.entry_id)
            if current and current[0] is conn:
                continue
            if current:
                self._detach(entry.entry_id)
            if conn is not None:
                remove = conn.add_message_callback(
                    self._handle, (BluetoothLERawAdvertisementsResponse,)
                )
                self._attached[entry.entry_id] = (conn, remove)
                _LOGGER.debug("Tapped raw adverts of ESPHome proxy %s", entry.title)

    def _detach(self, entry_id: str) -> None:
        _conn, remove = self._attached.pop(entry_id)
        try:
            remove()
        except KeyError:  # connection already torn down its handlers
            pass

    @callback
    def close(self) -> None:
        """Detach from all proxies."""
        for entry_id in list(self._attached):
            self._detach(entry_id)
