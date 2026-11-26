"""Exercise Apple BLE setup and unload with isolated HA doubles."""

from __future__ import annotations

import ast
import unittest

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, Mock


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "custom_components" / "apple_ble"


def load_functions(path, names, namespace):
    """Load selected real functions without importing HA."""
    tree = ast.parse(path.read_text())

    nodes = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name in names
    ]

    assert {node.name for node in nodes} == set(names)

    future = ast.ImportFrom(
        module="__future__",
        names=[ast.alias(name="annotations")],
        level=0,
    )

    module = ast.Module(
        body=[future, *nodes],
        type_ignores=[],
    )

    ast.fix_missing_locations(module)

    exec(
        compile(module, str(path), "exec"),
        namespace,
    )

    return namespace


class NativeSetupTests(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.hass = Mock()
        self.entry = Mock()

        self.entry.data = {}
        self.entry.options = {}
        self.entry.entry_id = "test-entry"

        self.unload_callbacks = []

        self.entry.async_on_unload.side_effect = (
            self.unload_callbacks.append
        )

        self.hass.config_entries.async_forward_entry_setups = (
            AsyncMock()
        )

        self.hass.config_entries.async_unload_platforms = (
            AsyncMock(return_value=True)
        )

        self.hass.config_entries.async_reload = AsyncMock()

        self.coordinator = Mock()
        self.manager = Mock()
        self.native_cancel = Mock()
        self.standard_cancel = Mock()

        self.manager.async_register_filtered_apple_callback\
            .return_value = self.native_cancel

        self.bluetooth = Mock()
        self.bluetooth.async_register_callback.return_value = (
            self.standard_cancel
        )

        self.tap = Mock()
        self.tap_factory = Mock(return_value=self.tap)

        self.coordinator_factory = Mock(
            return_value=self.coordinator
        )

        self.timers = []

        def track_interval(hass, handler, interval):
            cancel = Mock()

            self.timers.append(
                (handler, interval, cancel)
            )

            return cancel

        helper_namespace = {}

        load_functions(
            PACKAGE / "native_bluetooth.py",
            {"register_native_callback"},
            helper_namespace,
        )

        helper_namespace["APPLE_PROXIMITY_PAIRING"] = 0x07

        self.namespace = {
            "datetime": datetime,
            "timedelta": timedelta,
            "bluetooth": self.bluetooth,
            "callback": lambda fn: fn,
            "get_manager": Mock(return_value=self.manager),
            "register_native_callback": (
                helper_namespace["register_native_callback"]
            ),
            "AppleBleCoordinator": self.coordinator_factory,
            "EsphomeTap": self.tap_factory,
            "async_track_time_interval": track_interval,
            "parse_key": Mock(),
            "CONF_MODEL": "model",
            "CONF_RSSI_FLOOR": "rssi_floor",
            "CONF_IRK": "irk",
            "CONF_ENC_KEY": "enc_key",
            "DEFAULT_RSSI_FLOOR": -75,
            "STALE_AFTER_SECONDS": 60,
            "TAP_REFRESH_SECONDS": 30,
            "PLATFORMS": ["sensor", "binary_sensor"],
            "_LOGGER": Mock(),
        }

        load_functions(
            PACKAGE / "__init__.py",
            {
                "async_setup_entry",
                "async_unload_entry",
                "_async_reload",
            },
            self.namespace,
        )

    async def setup_entry(self):
        return await self.namespace["async_setup_entry"](
            self.hass,
            self.entry,
        )

    async def test_native_setup(self):
        self.assertTrue(await self.setup_entry())

        register = (
            self.manager
            .async_register_filtered_apple_callback
        )

        register.assert_called_once_with(
            self.coordinator.handle_advert,
            message_type=0x07,
        )

        self.assertIn(
            self.native_cancel,
            self.unload_callbacks,
        )

        self.tap_factory.assert_not_called()

    async def test_standard_callback_preserved(self):
        await self.setup_entry()

        self.bluetooth.async_register_callback\
            .assert_called_once()

        self.assertIn(
            self.standard_cancel,
            self.unload_callbacks,
        )

    async def test_fallback_without_native_api(self):
        self.namespace["get_manager"].return_value = object()

        self.assertTrue(await self.setup_entry())

        self.tap_factory.assert_called_once_with(
            self.hass,
            self.coordinator.handle_payload,
        )

        self.tap.refresh.assert_called_once()

        self.assertIn(
            self.tap.close,
            self.unload_callbacks,
        )

    async def test_native_cleanup_callback_registered(self):
        await self.setup_entry()

        self.assertIn(
            self.native_cancel,
            self.unload_callbacks,
        )

        for callback in reversed(self.unload_callbacks):
            callback()

        self.native_cancel.assert_called_once()
        self.standard_cancel.assert_called_once()

    async def test_fallback_cleanup_callback_registered(self):
        self.namespace["get_manager"].return_value = object()

        await self.setup_entry()

        for callback in reversed(self.unload_callbacks):
            callback()

        self.tap.close.assert_called_once()
        self.standard_cancel.assert_called_once()

    async def test_platform_forwarding(self):
        await self.setup_entry()

        self.hass.config_entries.async_forward_entry_setups\
            .assert_awaited_once_with(
                self.entry,
                ["sensor", "binary_sensor"],
            )

        self.assertIs(
            self.entry.runtime_data,
            self.coordinator,
        )

    async def test_presence_refresh(self):
        await self.setup_entry()

        presence = [
            handler
            for handler, interval, cancel in self.timers
            if handler.__name__ == "_async_tick"
        ]

        self.assertEqual(len(presence), 1)

        presence[0](datetime.now())

        self.coordinator.refresh_presence.assert_called_once()

    async def test_local_and_remote_delivery(self):
        await self.setup_entry()

        handler = (
            self.manager
            .async_register_filtered_apple_callback
            .call_args.args[0]
        )

        local = Mock(source="local", rssi=-75)
        remote = Mock(source="remote", rssi=-61)

        handler(local)
        handler(remote)

        self.coordinator.handle_advert.assert_any_call(local)
        self.coordinator.handle_advert.assert_any_call(remote)

    async def test_unload_platforms(self):
        unload = self.namespace["async_unload_entry"]

        result = await unload(self.hass, self.entry)

        self.assertTrue(result)

        self.hass.config_entries.async_unload_platforms\
            .assert_awaited_once_with(
                self.entry,
                ["sensor", "binary_sensor"],
            )

    async def test_reload_entry(self):
        reload_entry = self.namespace["_async_reload"]

        await reload_entry(self.hass, self.entry)

        self.hass.config_entries.async_reload\
            .assert_awaited_once_with("test-entry")

    async def test_fallback_refresh_timer(self):
        self.namespace["get_manager"].return_value = object()

        await self.setup_entry()

        refresh = [
            handler
            for handler, interval, cancel in self.timers
            if handler.__name__ == "_async_tap"
        ]

        self.assertEqual(len(refresh), 1)

        refresh[0](datetime.now())

        self.assertEqual(self.tap.refresh.call_count, 2)

    async def test_native_mode_has_no_tap_refresh_timer(self):
        await self.setup_entry()

        names = [
            handler.__name__
            for handler, interval, cancel in self.timers
        ]

        self.assertNotIn("_async_tap", names)


if __name__ == "__main__":
    unittest.main()
