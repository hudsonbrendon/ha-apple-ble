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
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import AppleBleCoordinator
from .entity import AppleBleEntity

if TYPE_CHECKING:
    from . import AppleBleConfigEntry

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class AppleBleBinaryDescription(BinarySensorEntityDescription):
    """Binary sensor description with a value extractor."""

    value_fn: Callable[[AppleBleCoordinator], bool | None]


def _flag(field: str) -> Callable[[AppleBleCoordinator], bool | None]:
    def _get(coord: AppleBleCoordinator) -> bool | None:
        return coord.value(field)  # type: ignore[return-value]

    return _get


BINARY_SENSORS: tuple[AppleBleBinaryDescription, ...] = (
    AppleBleBinaryDescription(
        key="left_charging",
        translation_key="left_charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        value_fn=_flag("left_charging"),
    ),
    AppleBleBinaryDescription(
        key="right_charging",
        translation_key="right_charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        value_fn=_flag("right_charging"),
    ),
    AppleBleBinaryDescription(
        key="case_charging",
        translation_key="case_charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        value_fn=_flag("case_charging"),
    ),
    AppleBleBinaryDescription(
        key="left_in_ear",
        translation_key="left_in_ear",
        device_class=BinarySensorDeviceClass.OCCUPANCY,
        value_fn=_flag("left_in_ear"),
    ),
    AppleBleBinaryDescription(
        key="right_in_ear",
        translation_key="right_in_ear",
        device_class=BinarySensorDeviceClass.OCCUPANCY,
        value_fn=_flag("right_in_ear"),
    ),
    AppleBleBinaryDescription(
        key="lid_open",
        translation_key="lid_open",
        device_class=BinarySensorDeviceClass.OPENING,
        value_fn=_flag("lid_open"),
    ),
    AppleBleBinaryDescription(
        key="apple_nearby",
        translation_key="apple_nearby",
        device_class=BinarySensorDeviceClass.PRESENCE,
        value_fn=lambda coord: coord.any_apple_nearby,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AppleBleConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Apple BLE binary sensors."""
    coordinator = entry.runtime_data
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
        """Initialize the entity."""
        super().__init__(coordinator, entry_id, title)
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_{description.key}"

    @property
    def is_on(self) -> bool | None:
        """Return the flag from the latest advert."""
        return self.entity_description.value_fn(self.coordinator)
