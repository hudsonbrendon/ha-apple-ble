"""Battery and diagnostic sensors for Apple BLE."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import AppleBleCoordinator
from .entity import AppleBleEntity

if TYPE_CHECKING:
    from . import AppleBleConfigEntry

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class AppleBleSensorDescription(SensorEntityDescription):
    """Sensor description with a value extractor."""

    value_fn: Callable[[AppleBleCoordinator], int | str | None]


def _battery(field: str) -> Callable[[AppleBleCoordinator], int | None]:
    def _get(coord: AppleBleCoordinator) -> int | None:
        return coord.value(field)  # type: ignore[return-value]

    return _get


def _host(coord: AppleBleCoordinator) -> str | None:
    return coord.decrypted.host_suffix if coord.decrypted is not None else None


SENSORS: tuple[AppleBleSensorDescription, ...] = (
    AppleBleSensorDescription(
        key="left_battery",
        translation_key="left_battery",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=_battery("left_battery"),
    ),
    AppleBleSensorDescription(
        key="right_battery",
        translation_key="right_battery",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=_battery("right_battery"),
    ),
    AppleBleSensorDescription(
        key="case_battery",
        translation_key="case_battery",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=_battery("case_battery"),
    ),
    AppleBleSensorDescription(
        key="pods_in_case",
        translation_key="pods_in_case",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_battery("pods_in_case"),
    ),
    AppleBleSensorDescription(
        key="connected_host",
        translation_key="connected_host",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_host,
    ),
    AppleBleSensorDescription(
        key="rssi",
        translation_key="rssi",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda coord: coord.best_rssi,
    ),
    AppleBleSensorDescription(
        key="apple_devices_nearby",
        translation_key="apple_devices_nearby",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda coord: coord.apple_devices_nearby,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AppleBleConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Apple BLE sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        AppleBleSensor(coordinator, entry.entry_id, entry.title, desc)
        for desc in SENSORS
    )


class AppleBleSensor(AppleBleEntity, SensorEntity):
    """A single Apple BLE sensor."""

    entity_description: AppleBleSensorDescription

    def __init__(
        self,
        coordinator: AppleBleCoordinator,
        entry_id: str,
        title: str,
        description: AppleBleSensorDescription,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator, entry_id, title)
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_{description.key}"

    @property
    def native_value(self) -> int | str | None:
        """Return the value from the latest advert."""
        return self.entity_description.value_fn(self.coordinator)
