"""Data classes for Sensibo."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class SensiboData:
    """Dataclass for Sensibo data."""

    raw: dict[str, Any]
    parsed: dict[str, SensiboDevice]


@dataclass
class SensiboDevice:
    """Dataclass for Sensibo Device."""

    id: str
    mac: str
    name: str
    ac_states: dict[str, Any]
    temp: float | None
    humidity: int | None
    target_temp: int | None
    hvac_mode: str | None
    device_on: bool | None
    fan_mode: str | None
    swing_mode: str | None
    horizontal_swing_mode: str | None
    light_mode: str | None
    available: bool
    hvac_modes: list[str | None]
    fan_modes: list[str | None] | None
    swing_modes: list[str | None] | None
    horizontal_swing_modes: list[str | None] | None
    light_modes: list[str | None] | None
    temp_unit: str | None
    temp_list: list[int]
    temp_step: int
    active_features: list[str]
    full_features: set[str]
    state: str
    fw_ver: str
    fw_ver_available: str | None
    fw_type: str
    model: str
    calibration_temp: float | None
    calibration_hum: float | None
    full_capabilities: dict[str, Any]
    motion_sensors: dict[str, MotionSensor] | None
    pm25: int | None
    room_occupied: bool
    update_available: bool
    schedules: dict[str, Schedules] | None
    pure_boost_enabled: bool | None
    pure_boost_attr: dict
    timer_on: bool
    timer_attr: dict
    smart_on: bool
    smart_attr: dict
    filters_clean: bool
    filters_attr: dict


@dataclass
class MotionSensor:
    """Dataclass for motionsensors."""

    id: str
    alive: bool | None = None
    motion: bool | None = None
    fw_ver: str | None = None
    fw_type: str | None = None
    is_main_sensor: bool | None = None
    battery_voltage: int | None = None
    humidity: int | None = None
    temperature: float | None = None
    model: str | None = None
    rssi: int | None = None


@dataclass
class Schedules:
    """Dataclass for schedules."""

    id: str
    enabled: bool
    state_on: bool | None
    state_full: dict
    days: list
    time: str
    next_utc: str
