"""Data classes for Sensibo."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum
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
    serial: str
    name: str
    ac_states: dict[str, Any]
    temp: float | None
    feelslike: float | None
    humidity: int | None
    pm25: float | None
    pm25_pure: PureAQI | None
    tvoc: int | None
    co2: int | None
    etoh: float | None
    iaq: int | None
    rcda: float | None
    target_temp: int | None
    hvac_mode: str | None
    device_on: bool | None
    fan_mode: str | None
    swing_mode: str | None
    horizontal_swing_mode: str | None
    light_mode: str | None
    available: bool
    hvac_modes: list[str]

    state: str  # hvac state

    # Translated modes are lowercase to case for matching api
    fan_modes: list[str] | None
    fan_modes_translated: dict[str, str] | None
    swing_modes: list[str] | None
    swing_modes_translated: dict[str, str] | None
    horizontal_swing_modes: list[str] | None
    horizontal_swing_modes_translated: dict[str, str] | None
    light_modes: list[str] | None
    light_modes_translated: dict[str, str] | None

    temp_unit: str | None
    temp_list: list[int]
    temp_step: int

    active_features: list[str]
    full_features: set[str]
    full_capabilities: dict[str, Any]

    fw_ver: str
    fw_ver_available: str | None
    fw_type: str
    update_available: bool
    model: str

    calibration_temp: float | None
    calibration_hum: float | None

    # Motion sensors are their own dataclasses
    motion_sensors: dict[str, MotionSensor] | None
    room_occupied: bool  # Only available if motion sensors are present

    # Schedule data is its own dataclasses
    schedules: dict[str, Schedules] | None

    # Pure only data
    pure_boost_enabled: bool | None
    pure_sensitivity: str | None
    pure_ac_integration: bool | None
    pure_geo_integration: bool | None
    pure_measure_integration: bool | None
    pure_prime_integration: bool | None
    pure_conf: dict[str, Any] | None

    # Timer only data
    timer_on: bool | None
    timer_id: str | None
    timer_state_on: bool | None
    timer_time: datetime | None

    # Climate react only data
    smart_on: bool | None
    smart_type: str | None
    smart_low_temp_threshold: float | None
    smart_high_temp_threshold: float | None
    smart_low_state: dict[str, Any] | None
    smart_high_state: dict[str, Any] | None

    filter_clean: bool
    filter_last_reset: datetime | None

    location_id: str
    location_name: str

    anti_mold_running: bool | None
    anti_mold_enabled: bool | None
    anti_mold_fan_time: int | None
    auto_off: bool
    auto_off_minutes: int | None


@dataclass
class MotionSensor:
    """Dataclass for motionsensors."""

    id: str
    alive: bool | None
    motion: bool | None
    fw_ver: str | None
    fw_type: str | None
    is_main_sensor: bool | None
    battery_voltage: int | None
    humidity: int | None
    temperature: float | None
    model: str | None
    rssi: int | None


@dataclass
class Schedules:
    """Dataclass for schedules."""

    id: str
    enabled: bool
    name: str | None
    state_on: bool | None
    state_full: dict[str, Any]
    days: list[str]
    time: str
    next_utc: datetime


class PureAQI(IntEnum):
    """Pure AQI value.

    PM2.5 values in Pure devices are AQI values.
    """

    GOOD = 1
    MODERATE = 2
    BAD = 3
