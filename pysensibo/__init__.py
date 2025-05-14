"""Python API for Sensibo."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

from aiohttp import ClientResponse, ClientSession, ClientTimeout

from .exceptions import AuthenticationError, SensiboError
from .model import MotionSensor, PureAQI, Schedules, SensiboData, SensiboDevice

APIV1 = "https://home.sensibo.com/api/v1"
APIV2 = "https://home.sensibo.com/api/v2"
API_GRAPHQL = "https://home.sensibo.com/graphql/v1"

TIMEOUT = 5 * 60
HTTP_AUTH_FAILED_STATUS_CODES = {401, 403}
MAX_POSSIBLE_STEP = 1000

LOGGER = logging.getLogger(__name__)


class SensiboClient:
    """Sensibo client."""

    def __init__(
        self, api_key: str, session: ClientSession | None = None, timeout: int = TIMEOUT
    ) -> None:
        """Initialize Sensibo Client.

        api_key: Key from https://home.sensibo.com/me/api
        session: aiohttp.ClientSession or None to create a new session.
        """
        self.api_key = api_key
        self._session = session if session else ClientSession()
        self.timeout = ClientTimeout(total=timeout)

    async def async_get_me(self) -> dict[str, Any]:
        """Return info about me."""
        params = {"apiKey": self.api_key}
        return await self._get(APIV1 + "/users/me", params)

    async def async_get_devices(self, fields: str = "*") -> dict[str, Any]:
        """Get all devices.

        fields: * for all fields or specific fields
        """
        params = {"apiKey": self.api_key, "fields": fields}
        return await self._get(APIV2 + "/users/me/pods", params)

    async def async_get_devices_data(self) -> SensiboData:  # noqa: C901
        """Return dataclass with Sensibo Devices."""
        devices: list[dict[str, Any]] = []
        data = await self.async_get_devices()
        if "result" not in data:
            LOGGER.warning("No result in data from devices")
            LOGGER.debug("Data without result: %s", data)
            raise SensiboError("No result in data")
        devices = list(data["result"])

        device_data: dict[str, SensiboDevice] = {}
        dev: dict[str, Any]
        for dev in devices:
            unique_id: str = dev["id"]
            mac: str = dev["macAddress"]
            serial: str = dev["serial"]
            name: str = dev["room"]["name"]

            measure: dict[str, Any] = dev["measurements"]
            temperature: float | None = measure.get("temperature")
            feelslike: float | None = measure.get("feelsLike")
            humidity: float | None = measure.get("humidity")
            # Add in new sensors for AirQ + Element model
            tvoc: int | None = measure.get("tvoc")
            co2: int | None = measure.get("co2")
            # Add information for Element model
            etoh: float | None = measure.get("etoh")
            iaq: int | None = measure.get("iaq")
            rcda: float | None = measure.get("rcda")

            location: str = dev["location"]["id"]
            location_name: str = dev["location"]["name"]
            auto_off: bool = dev["autoOffEnabled"]
            auto_off_minutes: int | None = dev["autoOffMinutes"]

            # Add AntiMold (premium feature)
            anti_mold: dict[str, Any] | None = dev["antiMoldConfig"]
            anti_mold_running: bool | None = (
                anti_mold.get("anti_mold_running") if anti_mold else None
            )
            anti_mold_enabled: bool | None = (
                anti_mold.get("anti_mold_running") if anti_mold else None
            )
            anti_mold_fan_time: int | None = (
                anti_mold.get("fan_time") if anti_mold else None
            )

            ac_states: dict[str, Any] = dev["acState"]
            target_temperature: int | None = ac_states.get("targetTemperature")
            hvac_mode: str | None = ac_states.get("mode")
            running: bool | None = ac_states.get("on")

            available: bool = dev["connectionStatus"].get("isAlive", True)

            capabilities: dict[str, Any] = dev["remoteCapabilities"] or {}
            hvac_modes: list[str] = list(capabilities.get("modes") or {})
            if not hvac_modes:
                LOGGER.warning(
                    "Device %s not correctly registered with remote on Sensibo cloud.",
                    name,
                )
            hvac_modes.append("off")
            state: str = hvac_mode if hvac_mode else "off"

            fan_mode: str | None = ac_states.get("fanLevel")
            if fan_mode:
                fan_mode = fan_mode.lower()
            swing_mode: str | None = ac_states.get("swing")
            if swing_mode:
                swing_mode = swing_mode.lower()
            horizontal_swing_mode: str | None = ac_states.get("horizontalSwing")
            if horizontal_swing_mode:
                horizontal_swing_mode = horizontal_swing_mode.lower()
            light_mode: str | None = ac_states.get("light")
            if light_mode:
                light_mode = light_mode.lower()

            current_capabilities: dict[str, Any] = capabilities.get("modes", {}).get(
                ac_states.get("mode"), {}
            )
            fan_modes: list[str] | None = current_capabilities.get("fanLevels")
            fan_modes_translated: dict[str, str] | None = None
            if fan_modes:
                fan_modes_translated = {
                    _fan_mode.lower(): _fan_mode for _fan_mode in fan_modes
                }
                fan_modes = [_fan_mode.lower() for _fan_mode in fan_modes]
            swing_modes: list[str] | None = current_capabilities.get("swing")
            swing_modes_translated: dict[str, str] | None = None
            if swing_modes:
                swing_modes_translated = {
                    _swing_mode.lower(): _swing_mode for _swing_mode in swing_modes
                }
                swing_modes = [_swing_mode.lower() for _swing_mode in swing_modes]
            horizontal_swing_modes: list[str] | None = current_capabilities.get(
                "horizontalSwing"
            )
            horizontal_swing_modes_translated: dict[str, str] | None = None
            if horizontal_swing_modes:
                horizontal_swing_modes_translated = {
                    _horizontal_mode.lower(): _horizontal_mode
                    for _horizontal_mode in horizontal_swing_modes
                }
                horizontal_swing_modes = [
                    _horizontal_mode.lower()
                    for _horizontal_mode in horizontal_swing_modes
                ]
            light_modes: list[str] | None = current_capabilities.get("light")
            light_modes_translated: dict[str, str] | None = None
            if light_modes:
                light_modes_translated = {
                    _light_mode.lower(): _light_mode for _light_mode in light_modes
                }
                light_modes = [_light_mode.lower() for _light_mode in light_modes]
            temperature_unit_key: str | None = dev.get(
                "temperatureUnit"
            ) or ac_states.get("temperatureUnit")
            temperatures_list: list[int] = (
                current_capabilities.get("temperatures", {})
                .get(temperature_unit_key, {})
                .get("values", [0, 1])
            )
            temperature_step: int = 0
            if temperatures_list:
                diff = MAX_POSSIBLE_STEP
                for i in range(len(temperatures_list) - 1):
                    diff = min(diff, temperatures_list[i + 1] - temperatures_list[i])
                temperature_step = diff

            active_features: list[str] = list(ac_states)
            full_features: set[str] = set()
            if (_capabilities := capabilities.get("modes")) is not None:
                for mode in _capabilities:
                    if "temperatures" in _capabilities[mode]:
                        full_features.add("targetTemperature")
                    if "swing" in _capabilities[mode]:
                        full_features.add("swing")
                    if "fanLevels" in _capabilities[mode]:
                        full_features.add("fanLevel")
                    if "horizontalSwing" in _capabilities[mode]:
                        full_features.add("horizontalSwing")
                    if "light" in _capabilities[mode]:
                        full_features.add("light")

            fw_ver: str = dev["firmwareVersion"]
            fw_ver_available: str | None = dev.get("currentlyAvailableFirmwareVersion")
            fw_type: str = dev["firmwareType"]
            model: str = dev["productModel"]

            # Calibration for temperature and humidity, always available keys
            calibration: dict[str, float] = dev["sensorsCalibration"]
            calibration_temp: float | None = calibration.get("temperature")
            calibration_hum: float | None = calibration.get("humidity")

            # Sky plus supports functionality to use motion sensor as sensor for temp and humidity
            # In that case the user has it as main sensor we will use those temperature and humidity values
            if main_sensor := dev["mainMeasurementsSensor"]:
                measurements = main_sensor["measurements"]
                temperature = measurements.get("temperature")
                humidity = measurements.get("humidity")

            motion_sensors: dict[str, MotionSensor] = {}
            if dev["motionSensors"]:  # Key is always present
                sensor: dict[str, Any]
                for sensor in dev["motionSensors"]:
                    measurement: dict[str, Any] = sensor["measurements"]
                    connection: dict[str, Any] = sensor["connectionStatus"]
                    # All keys should be present
                    motion_sensors[sensor["id"]] = MotionSensor(
                        id=sensor["id"],
                        alive=connection.get("isAlive"),
                        motion=measurement.get("motion"),
                        fw_ver=sensor.get("firmwareVersion"),
                        fw_type=sensor.get("firmwareType"),
                        is_main_sensor=sensor.get("isMainSensor"),
                        battery_voltage=measurement.get("batteryVoltage"),
                        humidity=measurement.get("humidity"),
                        temperature=measurement.get("temperature"),
                        model=sensor.get("productModel"),
                        rssi=measurement.get("rssi"),
                    )

            # Add information for pure devices
            pure_conf: dict[str, Any] = (
                dev["pureBoostConfig"] if dev["pureBoostConfig"] else {}
            )
            pure_boost_enabled: bool | None = None
            pure_sensitivity: str | None = None
            pure_ac_integration: bool | None = None
            pure_geo_integration: bool | None = None
            pure_measure_integration: bool | None = None
            pure_prime_integration: bool | None = None

            # Pure devices has special handling for PM2.5 value
            # as it represents an AQI value
            pm25: float | None = None
            pm25_pure: PureAQI | None = None

            if dev["productModel"] == "pure":
                pure_boost_enabled = pure_conf.get("enabled", False)
                pure_sensitivity = pure_conf.get("sensitivity", "n").lower()
                pure_ac_integration = pure_conf.get("ac_integration", False)
                pure_geo_integration = pure_conf.get("geo_integration", False)
                pure_measure_integration = pure_conf.get(
                    "measurements_integration", False
                )
                pure_prime_integration = pure_conf.get("prime_integration", False)
                if (_pm25 := measure.get("pm25")) is not None:
                    pm25_pure = PureAQI(_pm25)
            else:
                pm25 = measure.get("pm25")

            # Binary sensors for main device
            room_occupied: bool | None = dev["roomIsOccupied"]
            update_available: bool = bool(
                dev["firmwareVersion"] != dev["currentlyAvailableFirmwareVersion"]
            )

            # Filters
            filters: dict[str, Any] = dev.get("filtersCleaning", {})
            filter_clean: bool = filters.get("shouldCleanFilters", False)
            clean_time: dict[str, Any] = filters.get("lastFiltersCleanTime") or {}
            clean_time_str: str | None = clean_time.get("time")
            filter_last_reset: datetime | None = (
                datetime.strptime(clean_time_str, "%Y-%m-%dT%H:%M:%SZ").replace(
                    tzinfo=timezone.utc
                )
                if clean_time_str
                else None
            )

            # Timer
            timer: dict[str, Any] = dev["timer"] if dev["timer"] else {}
            timer_on: bool | None = None
            timer_id: str | None = None
            timer_state_on: bool | None = None
            timer_time: datetime | None = None
            if dev["productModel"] != "pure":  # No timer for Pure devices
                timer_on = timer.get("isEnabled", False)
                timer_id = timer.get("id")
                timer_state: dict[str, Any] | None = timer.get("acState")
                if timer_state:
                    timer_state_on = timer_state.get("on")
                timer_time_str: str | None = timer.get("targetTime")
                timer_time = (
                    datetime.strptime(timer_time_str, "%Y-%m-%dT%H:%M:%S").replace(
                        tzinfo=timezone.utc
                    )
                    if timer_time_str
                    else None
                )

            # Smartmode (climate react)
            smart: dict[str, Any] = dev.get("smartMode") or {}
            smart_on: bool | None = None
            if dev["productModel"] != "pure":  # No smartmode for Pure devices
                smart_on = smart.get("enabled", False)
            smart_type: str | None = smart.get("type")
            if smart_type:
                smart_type = smart_type.lower()
            smart_low_temp_threshold: int | None = smart.get("lowTemperatureThreshold")
            smart_high_temp_threshold: int | None = smart.get(
                "highTemperatureThreshold"
            )
            _smart_low_state: dict[str, Any] = smart.get("lowTemperatureState", {})
            _smart_high_state: dict[str, Any] = smart.get("highTemperatureState", {})
            smart_low_state: dict[str, Any] = {}
            smart_high_state: dict[str, Any] = {}
            if _smart_low_state:
                for key, value in _smart_low_state.items():
                    smart_low_state[key.lower()] = (
                        value.lower() if isinstance(value, str) else value
                    )
            if _smart_high_state:
                for key, value in _smart_high_state.items():
                    smart_high_state[key.lower()] = (
                        value.lower() if isinstance(value, str) else value
                    )

            # Schedules
            schedule_list: list[dict[str, Any]] = dev["schedules"]
            schedules: dict[str, Schedules] = {}
            if schedule_list:
                for schedule in schedule_list:
                    next_utc_str: str = schedule["nextTime"]
                    next_utc = datetime.strptime(
                        next_utc_str, "%Y-%m-%dT%H:%M:%S"
                    ).replace(tzinfo=timezone.utc)
                    _state_full: dict[str, Any] = schedule["acState"]
                    new_state_full = {}
                    for key, value in _state_full.items():
                        new_state_full[key.lower()] = (
                            value.lower() if isinstance(value, str) else value
                        )
                    new_days = [val.lower() for val in schedule["recurringDays"]]
                    schedules[schedule["id"]] = Schedules(
                        id=schedule["id"],
                        enabled=schedule["isEnabled"],
                        name=schedule["name"],
                        state_on=schedule["acState"].get("on"),
                        state_full=new_state_full,
                        days=new_days,
                        time=schedule["targetTimeLocal"],
                        next_utc=next_utc,
                    )

            device_data[unique_id] = SensiboDevice(
                id=unique_id,
                mac=mac,
                serial=serial,
                name=name,
                ac_states=ac_states,
                temp=temperature,
                feelslike=feelslike,
                humidity=humidity,
                tvoc=tvoc,
                co2=co2,
                target_temp=target_temperature,
                hvac_mode=hvac_mode,
                device_on=running,
                fan_mode=fan_mode,
                swing_mode=swing_mode,
                horizontal_swing_mode=horizontal_swing_mode,
                light_mode=light_mode,
                available=available,
                hvac_modes=hvac_modes,
                fan_modes=fan_modes,
                fan_modes_translated=fan_modes_translated,
                swing_modes=swing_modes,
                swing_modes_translated=swing_modes_translated,
                horizontal_swing_modes=horizontal_swing_modes,
                horizontal_swing_modes_translated=horizontal_swing_modes_translated,
                light_modes=light_modes,
                light_modes_translated=light_modes_translated,
                temp_unit=temperature_unit_key,
                temp_list=temperatures_list,
                temp_step=temperature_step,
                active_features=active_features,
                full_features=full_features,
                state=state,
                fw_ver=fw_ver,
                fw_ver_available=fw_ver_available,
                fw_type=fw_type,
                model=model,
                calibration_temp=calibration_temp,
                calibration_hum=calibration_hum,
                full_capabilities=capabilities,
                motion_sensors=motion_sensors,
                pure_boost_enabled=pure_boost_enabled,
                pure_sensitivity=pure_sensitivity,
                pure_ac_integration=pure_ac_integration,
                pure_geo_integration=pure_geo_integration,
                pure_measure_integration=pure_measure_integration,
                pure_prime_integration=pure_prime_integration,
                pure_conf=pure_conf,
                pm25=pm25,
                pm25_pure=pm25_pure,
                room_occupied=room_occupied,
                update_available=update_available,
                filter_clean=filter_clean,
                filter_last_reset=filter_last_reset,
                timer_on=timer_on,
                timer_id=timer_id,
                timer_state_on=timer_state_on,
                timer_time=timer_time,
                smart_on=smart_on,
                smart_type=smart_type,
                smart_low_temp_threshold=smart_low_temp_threshold,
                smart_high_temp_threshold=smart_high_temp_threshold,
                smart_low_state=smart_low_state,
                smart_high_state=smart_high_state,
                schedules=schedules,
                etoh=etoh,
                iaq=iaq,
                rcda=rcda,
                location_id=location,
                location_name=location_name,
                anti_mold_running=anti_mold_running,
                anti_mold_enabled=anti_mold_enabled,
                anti_mold_fan_time=anti_mold_fan_time,
                auto_off=auto_off,
                auto_off_minutes=auto_off_minutes,
            )

        return SensiboData(raw=data, parsed=device_data)

    async def async_get_device(self, uid: str, fields: str = "*") -> dict[str, Any]:
        """Get specific device by UID.

        uid: UID for device
        fields: * for all fields or specific fields
        """
        params = {"apiKey": self.api_key, "fields": fields}
        return await self._get(APIV2 + f"/pods/{uid}", params)

    async def async_reset_filter(self, uid: str) -> dict[str, Any]:
        """Reset filters.

        uid: UID for device
        """
        params = {"apiKey": self.api_key}
        return await self._delete(
            APIV2 + f"/pods/{uid}/cleanFiltersNotification", params
        )

    async def async_get_climate_react(self, uid: str) -> dict[str, Any]:
        """Get Climate React on a device.

        uid: UID for device
        """
        params = {"apiKey": self.api_key}
        return await self._get(APIV2 + f"/pods/{uid}/smartmode", params)

    async def async_enable_climate_react(
        self, uid: str, data: dict[str, bool]
    ) -> dict[str, Any]:
        """Enable/Disable Climate React on a device.

        uid: UID for device
        data: dict {enabled: boolean}
        """
        params = {"apiKey": self.api_key}
        return await self._put(APIV2 + f"/pods/{uid}/smartmode", params, data)

    async def async_set_climate_react(
        self, uid: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Set Climate React on a device.

        uid: UID for device
        data: dict according to dev["smartmode"]
        """
        params = {"apiKey": self.api_key}
        return await self._post(APIV2 + f"/pods/{uid}/smartmode", params, data)

    async def async_get_timer(self, uid: str) -> dict[str, Any]:
        """Get Timer on a device.

        uid: UID for device
        """
        params = {"apiKey": self.api_key}
        return await self._get(APIV1 + f"/pods/{uid}/timer/", params)

    async def async_set_timer(self, uid: str, data: dict[str, Any]) -> dict[str, Any]:
        """Set Timer on a device.

        uid: UID for device
        data: dict according to https://sensibo.github.io/#put-/pods/-device_id-/timer/
        """
        params = {"apiKey": self.api_key}
        return await self._put(APIV1 + f"/pods/{uid}/timer/", params, data)

    async def async_del_timer(self, uid: str) -> dict[str, Any]:
        """Delete Timer on a device.

        uid: UID for device
        """
        params = {"apiKey": self.api_key}
        return await self._delete(APIV1 + f"/pods/{uid}/timer/", params)

    async def async_get_schedules(self, uid: str) -> dict[str, Any]:
        """Get Schedules on a device.

        uid: UID for device
        """
        params = {"apiKey": self.api_key}
        return await self._get(APIV1 + f"/pods/{uid}/schedules/", params)

    async def async_get_schedule(self, uid: str, schedule_id: str) -> dict[str, Any]:
        """Get Schedule on a device.

        uid: UID for device
        schedule_id: string value for schedule id
        """
        params = {"apiKey": self.api_key}
        return await self._get(APIV1 + f"/pods/{uid}/schedules/{schedule_id}", params)

    async def async_set_schedule(
        self, uid: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Set Schedule on a device.

        uid: UID for device
        schedule_id: string value for schedule id
        data: dict according to https://sensibo.github.io/#post-/pods/-device_id-/schedules/
        """
        params = {"apiKey": self.api_key}
        return await self._post(APIV1 + f"/pods/{uid}/schedules/", params, data)

    async def async_enable_schedule(
        self, uid: str, schedule_id: str, data: dict[str, bool]
    ) -> dict[str, Any]:
        """Enable/Disable Schedule on a device.

        uid: UID for device
        schedule_id: string value for schedule id
        data: dict {isEnabled: boolean}
        """
        params = {"apiKey": self.api_key}
        return await self._put(
            APIV1 + f"/pods/{uid}/schedules/{schedule_id}", params, data
        )

    async def async_del_schedule(self, uid: str, schedule_id: str) -> dict[str, Any]:
        """Delete Schedule on a device.

        uid: UID for device
        schedule_id: string value for schedule id
        """
        params = {"apiKey": self.api_key}
        return await self._delete(
            APIV1 + f"/pods/{uid}/schedules/{schedule_id}", params
        )

    async def async_set_calibration(
        self, uid: str, data: dict[str, float]
    ) -> dict[str, Any]:
        """Adjust calibration on a device.

        uid: UID for device
        data: dict temperature or humidity and float as value
        """
        params = {"apiKey": self.api_key}
        return await self._post(APIV2 + f"/pods/{uid}/calibration/", params, data)

    async def async_set_pureboost(
        self, uid: str, data: dict[str, float]
    ) -> dict[str, Any]:
        """Set Pure Boost Settings.

        uid: UID for device
        data: dict as pure_conf
        """
        params = {"apiKey": self.api_key}
        return await self._put(APIV2 + f"/pods/{uid}/pureboost", params, data)

    async def async_set_ac_states(
        self,
        uid: str,
        ac_state: dict[str, Any],
    ) -> dict[str, Any]:
        """Set a specific device property.

        uid: UID for device
        ac_state: dict according to https://sensibo.github.io/#post-/pods/-device_id-/acStates
        """
        params = {"apiKey": self.api_key}
        data = {"acState": ac_state}
        return await self._post(APIV2 + f"/pods/{uid}/acStates", params, data)

    async def async_set_ac_state_property(
        self,
        uid: str,
        name: str,
        value: bool | int | str,
        ac_state: dict[str, Any],
        assumed_state: bool = False,
    ) -> dict[str, Any]:
        """Set a specific device property.

        uid: UID for device
        name: Field name to change
        value: New value of field
        ac_state: dict according to https://sensibo.github.io/#post-/pods/-device_id-/acStates
        assumed_state: bool is state change assumed
        """
        params = {"apiKey": self.api_key}
        data = {"currentAcState": ac_state, "newValue": value}
        if assumed_state:
            data["reason"] = "StateCorrectionByUser"
        return await self._patch(APIV2 + f"/pods/{uid}/acStates/{name}", params, data)

    async def _get(
        self, path: str, params: dict[str, Any], retry: int = 3
    ) -> dict[str, Any]:
        """Make GET api call to Sensibo api."""
        LOGGER.debug("Attempting get with path %s and parameters %s", path, params)
        try:
            async with self._session.get(
                path, params=params, timeout=self.timeout
            ) as resp:
                return await self._response(resp)
        except Exception:
            LOGGER.debug("Retry %d on path %s", 4 - retry, path)
            if retry > 0:
                await asyncio.sleep(7)
                return await self._get(path, params, retry - 1)
            raise

    async def _put(
        self,
        path: str,
        params: dict[str, Any],
        data: dict[str, Any],
        retry: bool = False,
    ) -> dict[str, Any]:
        """Make PUT api call to Sensibo api."""
        try:
            async with self._session.put(
                path, params=params, data=json.dumps(data), timeout=self.timeout
            ) as resp:
                return await self._response(resp)
        except Exception:
            if retry is False:
                await asyncio.sleep(5)
                return await self._put(path, params, data, True)
            raise

    async def _post(
        self,
        path: str,
        params: dict[str, Any],
        data: dict[str, Any],
        retry: bool = False,
    ) -> dict[str, Any]:
        """Make POST api call to Sensibo api."""

        try:
            async with self._session.post(
                path, params=params, data=json.dumps(data), timeout=self.timeout
            ) as resp:
                return await self._response(resp)
        except Exception:
            if retry is False:
                await asyncio.sleep(5)
                return await self._post(path, params, data, True)
            raise

    async def _patch(
        self,
        path: str,
        params: dict[str, Any],
        data: dict[str, Any],
        retry: bool = False,
    ) -> dict[str, Any]:
        """Make PATCH api call to Sensibo api."""

        try:
            async with self._session.patch(
                path, params=params, data=json.dumps(data), timeout=self.timeout
            ) as resp:
                return await self._response(resp)
        except Exception:
            if retry is False:
                await asyncio.sleep(5)
                return await self._patch(path, params, data, True)
            raise

    async def _delete(
        self, path: str, params: dict[str, Any], retry: bool = False
    ) -> dict[str, Any]:
        """Make DELETE api call to Sensibo api."""

        try:
            async with self._session.delete(
                path, params=params, timeout=self.timeout
            ) as resp:
                return await self._response(resp)
        except Exception:
            if retry is False:
                await asyncio.sleep(5)
                return await self._delete(path, params, True)
            raise

    async def _response(self, resp: ClientResponse) -> dict[str, Any]:
        """Return response from call."""
        if resp.status in HTTP_AUTH_FAILED_STATUS_CODES:
            raise AuthenticationError("Invalid API key")
        if resp.status != 200:
            error = await resp.text()
            raise SensiboError(f"API error: {error}")
        try:
            response: dict[str, Any] = await resp.json()
        except Exception as error:
            raise SensiboError(f"Could not return json {error}") from error
        return response
