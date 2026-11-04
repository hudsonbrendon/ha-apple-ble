"""ESPHome raw-advert tap + IRK/EncKey handling (the path that works on HA 2026.10)."""

import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from aioesphomeapi.api_pb2 import BluetoothLERawAdvertisementsResponse
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from homeassistant.config_entries import ConfigEntryState
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.apple_ble.const import CONF_ENC_KEY, CONF_IRK, CONF_MODEL, DOMAIN
from custom_components.apple_ble.coordinator import AppleBleCoordinator
from custom_components.apple_ble.esphome_tap import EsphomeTap, apple_payloads

CLEAR = bytes.fromhex("07190114202b888f100009")  # real AirPods Pro 2, both in ears


def _aes(key: bytes, block: bytes) -> bytes:
    e = Cipher(algorithms.AES(key), modes.ECB()).encryptor()
    return e.update(block) + e.finalize()


def _keys_and_addr():
    irk_le, enc = os.urandom(16), os.urandom(16)
    prand = bytes([0x7E, 0xAF, 0x23])
    addr = prand + _aes(irk_le[::-1], bytes(13) + prand)[-3:]
    return irk_le, enc, addr


def _ad(payload: bytes) -> bytes:
    flags = bytes([2, 0x01, 0x1A])
    mfr = bytes([len(payload) + 3, 0xFF, 0x4C, 0x00]) + payload
    return flags + mfr


def test_apple_payloads_extracts_only_proximity_pairing():
    pp = CLEAR + bytes(16)
    assert apple_payloads(_ad(pp)) == [pp]
    assert apple_payloads(_ad(bytes.fromhex("1202000a"))) == []
    assert apple_payloads(b"\x02\x01") == []  # truncated


async def test_irk_pins_and_enc_key_gives_exact_battery(hass):
    irk, enc, addr = _keys_and_addr()
    coord = AppleBleCoordinator(hass, model="", rssi_floor=-75, irk=irk, enc_key=enc)
    plain = bytes.fromhex("095456ffbccf27000000261cfb80b07a")
    payload = CLEAR + _aes(enc, plain)

    coord.handle_payload("7E:00:00:00:00:01", -40, payload)  # someone else's
    assert coord.data is None

    coord.handle_payload(addr.hex(":").upper(), -90, payload)  # ours, even if weak
    assert coord.value("left_battery") == 84
    assert coord.value("right_battery") == 86
    assert coord.value("left_in_ear") is True
    assert coord.decrypted is not None and coord.decrypted.host_suffix == "BC:CF:27"


async def test_tap_attaches_and_feeds_coordinator(hass):
    seen = []
    tap = EsphomeTap(hass, lambda a, r, p: seen.append((a, r, p)))

    handlers = {}
    conn = MagicMock()
    conn.add_message_callback.side_effect = lambda cb, types: (
        handlers.setdefault(types[0], cb),
        lambda: handlers.pop(types[0]),
    )[1]
    # A fake loaded esphome entry (a real one would load ESPHome on teardown).
    entry = SimpleNamespace(
        entry_id="proxy",
        title="proxy",
        state=ConfigEntryState.LOADED,
        runtime_data=SimpleNamespace(
            available=True, client=SimpleNamespace(_get_connection=lambda: conn)
        ),
    )
    with patch.object(hass.config_entries, "async_entries", return_value=[entry]):
        tap.refresh()
        tap.refresh()  # idempotent while the connection is the same
    assert conn.add_message_callback.call_count == 1

    msg = BluetoothLERawAdvertisementsResponse()
    adv = msg.advertisements.add()
    adv.address, adv.rssi, adv.data = 0x7EAF23346B34, -70, _ad(CLEAR + bytes(16))
    handlers[BluetoothLERawAdvertisementsResponse](msg)
    assert seen == [("7E:AF:23:34:6B:34", -70, CLEAR + bytes(16))]

    tap.close()
    assert handlers == {}


async def test_options_flow_validates_keys(hass):
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_MODEL: ""}, title="AirPods")
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_IRK: "zz", CONF_ENC_KEY: ""}
    )
    assert result["errors"] == {CONF_IRK: "invalid_key"}

    key = "-".join(["AB"] * 16)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_IRK: key, CONF_ENC_KEY: key}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {CONF_IRK: key, CONF_ENC_KEY: key}


async def test_closed_case_bud_keeps_last_known(hass):
    """Real sequence: left bud in open case (charging), lid closes, it goes silent."""
    irk, enc, addr = _keys_and_addr()
    coord = AppleBleCoordinator(hass, model="", rssi_floor=-75, irk=irk)
    a = addr.hex(":").upper()
    head = bytes.fromhex("0719011420")
    coord.handle_payload(a, -60, head + bytes.fromhex("73789f510004") + bytes(16))
    assert coord.value("lid_open") is True and coord.value("left_charging") is True
    coord.handle_payload(a, -60, head + bytes.fromhex("737897590004") + bytes(16))
    assert coord.value("lid_open") is False
    # Right bud now reports left unknown and no pod in case.
    coord.handle_payload(a, -60, head + bytes.fromhex("02f78f110004") + bytes(16))
    assert coord.value("left_battery") == 80 and coord.value("left_charging") is True
    assert coord.value("lid_open") is False
    assert coord.value("right_battery") == 70
