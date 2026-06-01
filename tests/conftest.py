"""Shared test fixtures."""

from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest

pytest_plugins = ["pytest_homeassistant_custom_component"]


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Allow loading the custom integration in tests."""
    yield


@pytest.fixture(autouse=True)
def expected_lingering_timers() -> bool:
    """Allow lingering timers from the bluetooth stack in teardown."""
    return True


@pytest.fixture(autouse=True)
def expected_lingering_tasks() -> bool:
    """Allow lingering tasks from the bluetooth stack in teardown."""
    return True


@pytest.fixture(autouse=True, scope="session")
def patch_linux_adapters_history():
    """Patch LinuxAdapters.history to avoid DBus calls on macOS in tests."""
    with patch(
        "bluetooth_adapters.systems.linux.LinuxAdapters.history",
        new_callable=PropertyMock,
        return_value={},
    ):
        yield


@pytest.fixture(autouse=True, scope="session")
def patch_ha_scanner():
    """Patch homeassistant.components.bluetooth.HaScanner to avoid real BLE on macOS."""
    mock_scanner = MagicMock()
    mock_scanner.return_value.async_start = AsyncMock()
    mock_scanner.return_value.async_stop = AsyncMock()
    mock_scanner.return_value.async_setup = MagicMock()
    with patch("homeassistant.components.bluetooth.HaScanner", mock_scanner):
        yield


@pytest.fixture(autouse=True)
async def auto_enable_bluetooth(enable_bluetooth):
    """Enable the mocked Bluetooth stack for all tests."""
    yield
