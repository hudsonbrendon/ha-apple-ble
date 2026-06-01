from dataclasses import dataclass
from unittest.mock import patch

from custom_components.apple_ble.coordinator import AppleBleCoordinator
from custom_components.apple_ble.const import STALE_AFTER_SECONDS


@dataclass
class _Info:
    address: str
    rssi: int
    manufacturer_data: dict
    name: str = "AirPods"


def _airpods_payload() -> bytes:
    hexstr = "0719070e2070a93601000045121212"
    hexstr = hexstr + "0" * (54 - len(hexstr))
    return bytes.fromhex(hexstr)


async def test_coordinator_parses_and_stores_strongest(hass):
    coord = AppleBleCoordinator(hass, model="", rssi_floor=-75)

    weak = _Info("AA:BB:CC:00:00:01", -70, {76: _airpods_payload()})
    strong = _Info("AA:BB:CC:00:00:02", -50, {76: _airpods_payload()})

    coord.handle_advert(weak)
    coord.handle_advert(strong)

    assert coord.data is not None
    assert coord.data.model == "AirPods Pro"
    assert coord.best_rssi == -50  # strongest wins in auto mode


async def test_coordinator_ignores_below_rssi_floor(hass):
    coord = AppleBleCoordinator(hass, model="", rssi_floor=-60)
    coord.handle_advert(_Info("AA:BB:CC:00:00:03", -90, {76: _airpods_payload()}))
    assert coord.data is None


async def test_coordinator_model_pin_filters_other_models(hass):
    coord = AppleBleCoordinator(hass, model="AirPods Max", rssi_floor=-90)
    # Sample decodes to "AirPods Pro" -> should be ignored when pinned to Max.
    coord.handle_advert(_Info("AA:BB:CC:00:00:04", -40, {76: _airpods_payload()}))
    assert coord.data is None


async def test_coordinator_weaker_ignored_within_freshness_window(hass):
    """Within the freshness window, a weaker advert must not replace a stronger one."""
    t0 = 1000.0
    with patch("custom_components.apple_ble.coordinator.time.monotonic", return_value=t0):
        coord = AppleBleCoordinator(hass, model="", rssi_floor=-75)
        strong = _Info("AA:BB:CC:00:00:05", -40, {76: _airpods_payload()})
        coord.handle_advert(strong)

    # Feed a weaker advert well within STALE_AFTER_SECONDS.
    t_within = t0 + STALE_AFTER_SECONDS / 2
    with patch("custom_components.apple_ble.coordinator.time.monotonic", return_value=t_within):
        weaker = _Info("AA:BB:CC:00:00:06", -70, {76: _airpods_payload()})
        coord.handle_advert(weaker)

    assert coord.best_rssi == -40  # strong advert still wins inside window


async def test_coordinator_stale_winner_accepts_weaker_advert(hass):
    """Once the previous winner goes stale, a weaker (but above-floor) advert is accepted."""
    t0 = 1000.0
    with patch("custom_components.apple_ble.coordinator.time.monotonic", return_value=t0):
        coord = AppleBleCoordinator(hass, model="", rssi_floor=-75)
        strong = _Info("AA:BB:CC:00:00:07", -40, {76: _airpods_payload()})
        coord.handle_advert(strong)

    assert coord.best_rssi == -40

    # Advance time past STALE_AFTER_SECONDS so the winner is considered stale.
    t_stale = t0 + STALE_AFTER_SECONDS + 1
    with patch("custom_components.apple_ble.coordinator.time.monotonic", return_value=t_stale):
        weaker = _Info("AA:BB:CC:00:00:08", -70, {76: _airpods_payload()})
        coord.handle_advert(weaker)

    # The weak advert must now be accepted because the strong one went stale.
    assert coord.data is not None
    assert coord.best_rssi == -70


async def test_presence_counts_distinct_recent_apple_devices(hass):
    coord = AppleBleCoordinator(hass, model="", rssi_floor=-90)

    # Two distinct Apple adverts (any manufacturer-76 payload, not only AirPods).
    coord.handle_advert(_Info("AA:BB:CC:00:00:10", -55, {76: b"\x10\x05abcd"}))
    coord.handle_advert(_Info("AA:BB:CC:00:00:11", -60, {76: b"\x10\x05wxyz"}))
    # Repeat of the first address -> still 2 distinct.
    coord.handle_advert(_Info("AA:BB:CC:00:00:10", -55, {76: b"\x10\x05abcd"}))

    assert coord.apple_devices_nearby == 2
    assert coord.any_apple_nearby is True


async def test_presence_decays_after_staleness(hass):
    """Devices that stop advertising must drop from the count after STALE_AFTER_SECONDS."""
    t0 = 5000.0
    with patch("custom_components.apple_ble.coordinator.time.monotonic", return_value=t0):
        coord = AppleBleCoordinator(hass, model="", rssi_floor=-90)
        coord.handle_advert(_Info("AA:BB:CC:00:00:20", -55, {76: b"\x10\x05abcd"}))
        coord.handle_advert(_Info("AA:BB:CC:00:00:21", -60, {76: b"\x10\x05efgh"}))
        assert coord.apple_devices_nearby == 2

    # Advance monotonic past STALE_AFTER_SECONDS; no new adverts arrive.
    t_stale = t0 + STALE_AFTER_SECONDS + 1
    with patch("custom_components.apple_ble.coordinator.time.monotonic", return_value=t_stale):
        assert coord.apple_devices_nearby == 0
        assert coord.any_apple_nearby is False
