"""Tests for optional native Apple BLE reception."""

import importlib.util
import unittest
from pathlib import Path
from unittest.mock import Mock


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "apple_ble"
    / "native_bluetooth.py"
)

spec = importlib.util.spec_from_file_location(
    "native_bluetooth",
    MODULE_PATH,
)

module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

register_native_callback = module.register_native_callback


class NativeBluetoothTests(unittest.TestCase):

    def test_api_unavailable(self):
        manager = object()
        handler = Mock()

        result = register_native_callback(manager, handler)

        self.assertIsNone(result)
        handler.assert_not_called()

    def test_non_callable_api(self):
        manager = Mock()
        manager.async_register_filtered_apple_callback = None

        self.assertIsNone(
            register_native_callback(manager, Mock())
        )

    def test_registers_apple_message_type(self):
        manager = Mock()
        handler = Mock()

        register_native_callback(manager, handler)

        manager.async_register_filtered_apple_callback\
            .assert_called_once_with(
                handler,
                message_type=0x07,
            )

    def test_returns_cancellation_callback(self):
        manager = Mock()
        cancel = Mock()

        manager.async_register_filtered_apple_callback\
            .return_value = cancel

        result = register_native_callback(manager, Mock())

        self.assertIs(result, cancel)

        result()

        cancel.assert_called_once_with()

    def test_local_and_remote_advertisements(self):
        manager = Mock()
        handler = Mock()

        register_native_callback(manager, handler)

        registered = (
            manager.async_register_filtered_apple_callback
            .call_args.args[0]
        )

        local = Mock(source="local")
        remote = Mock(source="remote")

        registered(local)
        registered(remote)

        self.assertEqual(handler.call_count, 2)
        handler.assert_any_call(local)
        handler.assert_any_call(remote)

    def test_registration_error_is_not_hidden(self):
        manager = Mock()

        manager.async_register_filtered_apple_callback\
            .side_effect = RuntimeError("registration failed")

        with self.assertRaises(RuntimeError):
            register_native_callback(manager, Mock())


class NativeLifecycleTests(unittest.TestCase):

    def test_multiple_independent_registrations(self):
        manager = Mock()
        first_handler = Mock()
        second_handler = Mock()
        first_cancel = Mock()
        second_cancel = Mock()

        manager.async_register_filtered_apple_callback.side_effect = [
            first_cancel,
            second_cancel,
        ]

        first = register_native_callback(
            manager, first_handler
        )
        second = register_native_callback(
            manager, second_handler
        )

        self.assertIs(first, first_cancel)
        self.assertIs(second, second_cancel)

        first()

        first_cancel.assert_called_once_with()
        second_cancel.assert_not_called()

        second()

        second_cancel.assert_called_once_with()

    def test_handler_receives_original_service_info(self):
        manager = Mock()
        handler = Mock()

        register_native_callback(manager, handler)

        registered = (
            manager.async_register_filtered_apple_callback
            .call_args.args[0]
        )

        info = Mock(
            source="remote",
            rssi=-61,
            manufacturer_data={76: bytes([0x07, 0x19])},
        )

        registered(info)

        self.assertIs(handler.call_args.args[0], info)

    def test_handler_not_called_during_registration(self):
        manager = Mock()
        handler = Mock()

        register_native_callback(manager, handler)

        handler.assert_not_called()

    def test_missing_api_does_not_invoke_handler(self):
        handler = Mock()

        result = register_native_callback(
            object(), handler
        )

        self.assertIsNone(result)
        handler.assert_not_called()


if __name__ == "__main__":
    unittest.main()
