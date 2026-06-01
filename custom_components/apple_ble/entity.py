"""Base entity for Apple BLE."""

from __future__ import annotations

from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity, DeviceInfo

from .const import DOMAIN
from .coordinator import AppleBleCoordinator, signal_updated


class AppleBleEntity(Entity):
    """Common base: pulls state from the coordinator, updates on dispatcher signal."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(self, coordinator: AppleBleCoordinator, entry_id: str, title: str) -> None:
        self.coordinator = coordinator
        self._entry_id = entry_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name=title,
            manufacturer="Apple",
            model=coordinator.model or "AirPods",
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, signal_updated(self._entry_id), self.async_write_ha_state
            )
        )
