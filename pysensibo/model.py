"""Data classes for Sensibo."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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
    feelslike: float | None
    humidity: int | None
    tvoc: int | None
    co2: int | None
    target_temp: int | None
    hvac_mode: str | None
    device_on: bool | None
    fan_mode: str | None
    swing_mode: str | None
    horizontal_swing_mode: str | None
    light_mode: str | None
    available: bool
    hvac_modes: list[str] | None
    fan_modes: list[str] | None
    fan_modes_translated: dict | None
    swing_modes: list[str] | None
    swing_modes_translated: dict | None
    horizontal_swing_modes: list[str] | None
    horizontal_swing_modes_translated: dict | None
    light_modes: list[str] | None
    light_modes_translated: dict | None
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
    pm25: float | None
    room_occupied: bool
    update_available: bool
    schedules: dict[str, Schedules] | None
    pure_boost_enabled: bool | None
    pure_sensitivity: str | None
    pure_ac_integration: bool | None
    pure_geo_integration: bool | None
    pure_measure_integration: bool | None
    pure_prime_integration: bool | None
    pure_conf: dict[str, Any] | None
    timer_on: bool | None
    timer_id: str | None
    timer_state_on: bool | None
    timer_time: datetime | None
    smart_on: bool | None
    smart_type: str | None
    smart_low_temp_threshold: float | None
    smart_high_temp_threshold: float | None
    smart_low_state: dict[str, Any] | None
    smart_high_state: dict[str, Any] | None
    filter_clean: bool
    filter_last_reset: datetime | None
    etoh: float | None
    iaq: int | None
    rcda: float | None
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
    name: str | None
    state_on: bool | None
    state_full: dict[str, Any]
    days: list[str]
    time: str
    next_utc: datetime
