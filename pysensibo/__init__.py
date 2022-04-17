"""Python API for Sensibo."""
from __future__ import annotations
import asyncio

import json
from typing import Any

from aiohttp import ClientResponse, ClientSession

from .exceptions import AuthenticationError, SensiboError
from .model import MotionSensor, SensiboData, SensiboDevice, Schedules

APIV1 = "https://home.sensibo.com/api/v1"
APIV2 = "https://home.sensibo.com/api/v2"

TIMEOUT = 5 * 60
HTTP_AUTH_FAILED_STATUS_CODES = {401, 403}
MAX_POSSIBLE_STEP = 1000


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
        self.timeout = timeout

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

    async def async_get_devices_data(self) -> SensiboData:
        """Return dataclass with Sensibo Devices."""
        devices = []
        data = await self.async_get_devices()
        for dev in data["result"]:
            devices.append(dev)

        device_data: dict[str, SensiboDevice] = {}
        for dev in devices:
            unique_id = dev["id"]
            mac = dev["macAddress"]
            name = dev["room"]["name"]
            temperature = dev["measurements"].get("temperature")
            humidity = dev["measurements"].get("humidity")
            ac_states = dev["acState"]
            target_temperature = ac_states.get("targetTemperature")
            hvac_mode = ac_states.get("mode")
            running = ac_states.get("on")
            fan_mode = ac_states.get("fanLevel")
            swing_mode = ac_states.get("swing")
            horizontal_swing_mode = ac_states.get("horizontalSwing")
            light_mode = ac_states.get("light")
            available = dev["connectionStatus"].get("isAlive", True)
            capabilities = dev["remoteCapabilities"]
            hvac_modes = list(capabilities["modes"])
            if hvac_modes:
                hvac_modes.append("off")
            current_capabilities = capabilities["modes"][ac_states.get("mode")]
            fan_modes = current_capabilities.get("fanLevels")
            swing_modes = current_capabilities.get("swing")
            horizontal_swing_modes = current_capabilities.get("horizontalSwing")
            light_modes = current_capabilities.get("light")
            temperature_unit_key = dev.get("temperatureUnit") or ac_states.get(
                "temperatureUnit"
            )
            temperatures_list = (
                current_capabilities["temperatures"]
                .get(temperature_unit_key, {})
                .get("values", [0, 1])
            )
            if temperatures_list:
                diff = MAX_POSSIBLE_STEP
                for i in range(len(temperatures_list) - 1):
                    if temperatures_list[i + 1] - temperatures_list[i] < diff:
                        diff = temperatures_list[i + 1] - temperatures_list[i]
                temperature_step = diff

            active_features = list(ac_states)
            full_features = set()
            for mode in capabilities["modes"]:
                if "temperatures" in capabilities["modes"][mode]:
                    full_features.add("targetTemperature")
                if "swing" in capabilities["modes"][mode]:
                    full_features.add("swing")
                if "fanLevels" in capabilities["modes"][mode]:
                    full_features.add("fanLevel")
                if "horizontalSwing" in capabilities["modes"][mode]:
                    full_features.add("horizontalSwing")
                if "light" in capabilities["modes"][mode]:
                    full_features.add("light")

            state = hvac_mode if hvac_mode else "off"

            fw_ver = dev["firmwareVersion"]
            fw_ver_available = dev.get("currentlyAvailableFirmwareVersion")
            fw_type = dev["firmwareType"]
            model = dev["productModel"]

            calibration_temp = dev["sensorsCalibration"].get("temperature")
            calibration_hum = dev["sensorsCalibration"].get("humidity")

            # Sky plus supports functionality to use motion sensor as sensor for temp and humidity
            if main_sensor := dev["mainMeasurementsSensor"]:
                measurements = main_sensor["measurements"]
                temperature = measurements.get("temperature")
                humidity = measurements.get("humidity")

            motion_sensors: dict[str, MotionSensor] = {}
            if dev["motionSensors"]:
                for sensor in dev["motionSensors"]:
                    measurement = sensor["measurements"]
                    motion_sensors[sensor["id"]] = MotionSensor(
                        id=sensor["id"],
                        alive=sensor["connectionStatus"].get("isAlive"),
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
            pure_conf = dev["pureBoostConfig"]
            pure_sensitivity = pure_conf.get("sensitivity") if pure_conf else None
            pure_boost_enabled = pure_conf.get("enabled") if pure_conf else None
            pm25 = dev["measurements"].get("pm25")

            # Binary sensors for main device
            room_occupied = dev["roomIsOccupied"]
            update_available = bool(
                dev["firmwareVersion"] != dev["currentlyAvailableFirmwareVersion"]
            )

            # Filters information
            filters = dev["filtersCleaning"]
            filter_ac_on = (
                filters.get("acOnSecondsSinceLastFiltersClean") if filters else None
            )
            filter_clean_threshold = (
                filters.get("filtersCleanSecondsThreshold") if filters else None
            )
            filter_last_clean = (
                filters.get("lastFiltersCleanTime").get("time") if filters else None
            )
            filter_should_clean = filters.get("shouldCleanFilters") if filters else None

            # Timer information
            timer = dev["timer"]
            timer_id = timer.get("id") if timer else None
            timer_on = timer.get("isEnabled") if timer else None
            timer_state = timer.get("acState").get("on") if timer else None
            timer_time_utc = timer.get("targetTime") if timer else None

            # Smartmode
            smart = dev["smartMode"]
            smart_on = smart.get("enabled") if smart else None
            smart_type = smart.get("temperature") if smart else None
            smart_low = smart.get("lowTemperatureThreshold") if smart else None
            smart_high = smart.get("highTemperatureThreshold") if smart else None
            smart_low_state = smart.get("lowTemperatureState") if smart else None
            smart_high_state = smart.get("highTemperatureState") if smart else None

            # Schedules
            schedule_list = dev["schedules"]
            schedules: dict[str, Schedules] = {}
            if schedule_list:
                for schedule in schedule_list:
                    schedules[schedule["id"]] = Schedules(
                        id=schedule["id"],
                        enabled=schedule["isEnabled"],
                        state_on=schedule["acState"].get("on"),
                        state_full=schedule["acState"],
                        days=schedule["recurringDays"],
                        time=schedule["targetTimeLocal"],
                        next_utc=schedule["nextTime"],
                    )

            device_data[unique_id] = SensiboDevice(
                id=unique_id,
                mac=mac,
                name=name,
                ac_states=ac_states,
                temp=temperature,
                humidity=humidity,
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
                swing_modes=swing_modes,
                horizontal_swing_modes=horizontal_swing_modes,
                light_modes=light_modes,
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
                pure_sensitivity=pure_sensitivity,
                pure_boost_enabled=pure_boost_enabled,
                pm25=pm25,
                room_occupied=room_occupied,
                update_available=update_available,
                filter_ac_on=filter_ac_on,
                filter_clean_threshold=filter_clean_threshold,
                filter_last_clean=filter_last_clean,
                filter_should_clean=filter_should_clean,
                timer_id=timer_id,
                timer_on=timer_on,
                timer_state=timer_state,
                timer_time_utc=timer_time_utc,
                smart_on=smart_on,
                smart_type=smart_type,
                smart_low=smart_low,
                smart_high=smart_high,
                smart_low_state=smart_low_state,
                smart_high_state=smart_high_state,
                schedules=schedules,
            )

        return SensiboData(raw=data, parsed=device_data)

    async def async_get_device(self, uid: str, fields: str = "*") -> dict[str, Any]:
        """Get specific device by UID.

        uid: UID for device
        fields: * for all fields or specific fields
        """
        params = {"apiKey": self.api_key, "fields": fields}
        return await self._get(APIV2 + "/pods/{}".format(uid), params)

    async def async_get_climate_react(self, uid: str) -> dict[str, Any]:
        """Get Climate React on a device.

        uid: UID for device
        """
        params = {"apiKey": self.api_key}
        return await self._get(APIV2 + "/pods/{}/smartmode".format(uid), params)

    async def async_enable_climate_react(
        self, uid: str, data: dict[str, bool]
    ) -> dict[str, Any]:
        """Enable/Disable Climate React on a device.

        uid: UID for device
        data: dict {enabled: boolean}
        """
        params = {"apiKey": self.api_key}
        return await self._put(APIV2 + "/pods/{}/smartmode".format(uid), params, data)

    async def async_get_timer(self, uid: str) -> dict[str, Any]:
        """Get Timer on a device.

        uid: UID for device
        """
        params = {"apiKey": self.api_key}
        return await self._get(APIV1 + "/pods/{}/timer/".format(uid), params)

    async def async_set_timer(self, uid: str, data: dict[str, Any]) -> dict[str, Any]:
        """Set Timer on a device.

        uid: UID for device
        data: dict according to https://sensibo.github.io/#put-/pods/-device_id-/timer/
        """
        params = {"apiKey": self.api_key}
        return await self._put(APIV1 + "/pods/{}/timer/".format(uid), params, data)

    async def async_del_timer(self, uid: str) -> dict[str, Any]:
        """Delete Timer on a device.

        uid: UID for device
        """
        params = {"apiKey": self.api_key}
        return await self._delete(APIV1 + "/pods/{}/timer/".format(uid), params)

    async def async_get_schedules(self, uid: str) -> dict[str, Any]:
        """Get Schedules on a device.

        uid: UID for device
        """
        params = {"apiKey": self.api_key}
        return await self._get(APIV1 + "/pods/{}/schedules/".format(uid), params)

    async def async_get_schedule(self, uid: str, schedule_id: str) -> dict[str, Any]:
        """Get Schedule on a device.

        uid: UID for device
        schedule_id: string value for schedule id
        """
        params = {"apiKey": self.api_key}
        return await self._get(
            APIV1 + "/pods/{}/schedules/{}".format(uid, schedule_id), params
        )

    async def async_set_schedule(
        self, uid: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Set Schedule on a device.

        uid: UID for device
        schedule_id: string value for schedule id
        data: dict according to https://sensibo.github.io/#post-/pods/-device_id-/schedules/
        """
        params = {"apiKey": self.api_key}
        return await self._post(APIV1 + "/pods/{}/schedules/".format(uid), params, data)

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
            APIV1 + "/pods/{}/schedules/{}".format(uid, schedule_id), params, data
        )

    async def async_del_schedule(self, uid: str, schedule_id: str) -> dict[str, Any]:
        """Delete Schedule on a device.

        uid: UID for device
        schedule_id: string value for schedule id
        """
        params = {"apiKey": self.api_key}
        return await self._delete(
            APIV1 + "/pods/{}/schedules/{}".format(uid, schedule_id), params
        )

    async def async_set_calibration(
        self, uid: str, data: dict[str, float]
    ) -> dict[str, Any]:
        """Adjust calibration on a device.

        uid: UID for device
        data: dict temperature or humidity and float as value
        """
        params = {"apiKey": self.api_key}
        return await self._post(
            APIV2 + "/pods/{}/calibration/".format(uid), params, data
        )

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
        return await self._post(APIV2 + "/pods/{}/acStates".format(uid), params, data)

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
        return await self._patch(
            APIV2 + "/pods/{}/acStates/{}".format(uid, name), params, data
        )

    async def _get(
        self, path: str, params: dict[str, Any], retry: bool = False
    ) -> dict[str, Any]:
        """Make GET api call to Sensibo api."""
        async with self._session.get(path, params=params, timeout=self.timeout) as resp:
            try:
                return await self._response(resp)
            except Exception as error:
                if retry is False:
                    asyncio.sleep(5)
                    return self._get(path, params, True)
                raise error

    async def _put(
        self,
        path: str,
        params: dict[str, Any],
        data: dict[str, Any],
        retry: bool = False,
    ) -> dict[str, Any]:
        """Make PUT api call to Sensibo api."""
        async with self._session.put(
            path, params=params, data=json.dumps(data), timeout=self.timeout
        ) as resp:
            try:
                return await self._response(resp)
            except Exception as error:
                if retry is False:
                    asyncio.sleep(5)
                    return self._put(path, params, data, True)
                raise error

    async def _post(
        self,
        path: str,
        params: dict[str, Any],
        data: dict[str, Any],
        retry: bool = False,
    ) -> dict[str, Any]:
        """Make POST api call to Sensibo api."""
        async with self._session.post(
            path, params=params, data=json.dumps(data), timeout=self.timeout
        ) as resp:
            try:
                return await self._response(resp)
            except Exception as error:
                if retry is False:
                    asyncio.sleep(5)
                    return self._post(path, params, data, True)
                raise error

    async def _patch(
        self,
        path: str,
        params: dict[str, Any],
        data: dict[str, Any],
        retry: bool = False,
    ) -> dict[str, Any]:
        """Make PATCH api call to Sensibo api."""
        async with self._session.patch(
            path, params=params, data=json.dumps(data), timeout=self.timeout
        ) as resp:
            try:
                return await self._response(resp)
            except Exception as error:
                if retry is False:
                    asyncio.sleep(5)
                    return self._patch(path, params, data, True)
                raise error

    async def _delete(
        self, path: str, params: dict[str, Any], retry: bool = False
    ) -> dict[str, Any]:
        """Make DELETE api call to Sensibo api."""
        async with self._session.delete(
            path, params=params, timeout=self.timeout
        ) as resp:
            try:
                return await self._response(resp)
            except Exception as error:
                if retry is False:
                    asyncio.sleep(5)
                    return self._delete(path, params, True)
                raise error

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
