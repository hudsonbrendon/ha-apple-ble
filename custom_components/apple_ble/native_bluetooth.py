"""Optional native reception of filtered Apple advertisements."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

APPLE_PROXIMITY_PAIRING = 0x07


def register_native_callback(
    manager: Any,
    handler: Callable[..., None],
) -> Callable[[], None] | None:
    """Register native Apple reception when supported.

    Return the cancellation callback, or None when the
    installed Bluetooth manager does not expose the API.
    """
    register = getattr(
        manager,
        "async_register_filtered_apple_callback",
        None,
    )

    if not callable(register):
        return None

    return register(
        handler,
        message_type=APPLE_PROXIMITY_PAIRING,
    )
