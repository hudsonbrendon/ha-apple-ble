"""Charging binary sensors for Apple BLE."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

if TYPE_CHECKING:
    from apple_ble import AirPodsData

from .const import DOMAIN
from .coordinator import AppleBleCoordinator
from .entity import AppleBleEntity


@dataclass(frozen=True, kw_only=True)
class AppleBleBinaryDescription(BinarySensorEntityDescription):
    """Binary sensor description with a value extractor."""

    value_fn: Callable[[AppleBleCoordinator], bool | None]


def _flag(field: str) -> Callable[[AppleBleCoordinator], bool | None]:
    def _get(coord: AppleBleCoordinator) -> bool | None:
        data: AirPodsData | None = coord.data
        return getattr(data, field) if data is not None else None

    return _get


BINARY_SENSORS: tuple[AppleBleBinaryDescription, ...] = (
    AppleBleBinaryDescription(
        key="left_charging",
        translation_key="left_charging",
        name="Left charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        value_fn=_flag("left_charging"),
    ),
    AppleBleBinaryDescription(
        key="right_charging",
        translation_key="right_charging",
        name="Right charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        value_fn=_flag("right_charging"),
    ),
    AppleBleBinaryDescription(
        key="case_charging",
        translation_key="case_charging",
        name="Case charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        value_fn=_flag("case_charging"),
    ),
    AppleBleBinaryDescription(
        key="apple_nearby",
        translation_key="apple_nearby",
        name="Apple device nearby",
        device_class=BinarySensorDeviceClass.PRESENCE,
        value_fn=lambda coord: coord.any_apple_nearby,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Apple BLE binary sensors."""
    coordinator: AppleBleCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        AppleBleBinarySensor(coordinator, entry.entry_id, entry.title, desc)
        for desc in BINARY_SENSORS
    )


class AppleBleBinarySensor(AppleBleEntity, BinarySensorEntity):
    """A single Apple BLE charging binary sensor."""

    entity_description: AppleBleBinaryDescription

    def __init__(
        self,
        coordinator: AppleBleCoordinator,
        entry_id: str,
        title: str,
        description: AppleBleBinaryDescription,
    ) -> None:
        super().__init__(coordinator, entry_id, title)
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_{description.key}"

    @property
    def is_on(self) -> bool | None:
        return self.entity_description.value_fn(self.coordinator)
