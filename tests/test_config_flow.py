import time

from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from habluetooth.models import BluetoothServiceInfoBleak

from custom_components.apple_ble.const import CONF_MODEL, DOMAIN
from homeassistant.data_entry_flow import FlowResultType


def _make_service_info(
    address: str,
    rssi: int,
    manufacturer_data: dict,
    name: str = "AirPods Pro",
) -> BluetoothServiceInfoBleak:
    """Build a BluetoothServiceInfoBleak for use in bluetooth-discovery flow tests."""
    device = BLEDevice(address, name, {})
    advert = AdvertisementData(
        local_name=name,
        manufacturer_data=manufacturer_data,
        service_data={},
        service_uuids=[],
        rssi=rssi,
        tx_power=None,
        platform_data=(),
    )
    return BluetoothServiceInfoBleak(
        name,
        address,
        rssi,
        manufacturer_data,
        {},
        [],
        "local",
        device,
        advert,
        False,
        time.monotonic(),
        None,
    )


def _airpods_pro_payload() -> bytes:
    hexstr = "0719070e2070a93601000045121212"
    hexstr = hexstr + "0" * (54 - len(hexstr))
    return bytes.fromhex(hexstr)


async def test_user_flow_auto_mode(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_MODEL: ""}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_MODEL] == ""
    assert result["title"]  # non-empty


async def test_single_auto_entry_is_unique(hass):
    # First auto entry succeeds.
    r1 = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    await hass.config_entries.flow.async_configure(r1["flow_id"], {CONF_MODEL: ""})

    # Second auto entry should abort as already configured.
    r2 = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    r2 = await hass.config_entries.flow.async_configure(r2["flow_id"], {CONF_MODEL: ""})
    assert r2["type"] is FlowResultType.ABORT
    assert r2["reason"] == "already_configured"


async def test_bluetooth_discovery_happy_path(hass):
    """A valid AirPods Pro discovery advances to the confirm form, then creates an entry."""
    service_info = _make_service_info(
        "AA:BB:CC:DD:EE:01",
        -60,
        {76: _airpods_pro_payload()},
    )

    # Step 1: bluetooth discovery → confirm form.
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "bluetooth"}, data=service_info
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "confirm"

    # Step 2: user confirms → entry created.
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "AirPods Pro"
    assert result["data"][CONF_MODEL] == "AirPods Pro"


async def test_bluetooth_discovery_not_airpods_abort(hass):
    """A discovery whose manufacturer-76 payload fails parse is aborted as not_airpods."""
    # type byte 0x10 is not 0x07 (proximity pairing), so parse_proximity_pairing returns None.
    bad_payload = bytes.fromhex("1005") + b"abcd"
    service_info = _make_service_info(
        "AA:BB:CC:DD:EE:02",
        -60,
        {76: bad_payload},
        name="Unknown",
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "bluetooth"}, data=service_info
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "not_airpods"


async def test_bluetooth_discovery_already_configured_abort(hass):
    """A second bluetooth discovery for an already-configured model is aborted."""
    service_info = _make_service_info(
        "AA:BB:CC:DD:EE:03",
        -60,
        {76: _airpods_pro_payload()},
    )

    # Create the entry via the first discovery.
    r1 = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "bluetooth"}, data=service_info
    )
    await hass.config_entries.flow.async_configure(r1["flow_id"], {})

    # Second discovery for the same model → already_configured.
    service_info2 = _make_service_info(
        "AA:BB:CC:DD:EE:04",
        -55,
        {76: _airpods_pro_payload()},
    )
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "bluetooth"}, data=service_info2
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
