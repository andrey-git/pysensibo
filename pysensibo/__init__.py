"""Python API for Sensibo."""
from __future__ import annotations
import json

from typing import Any
from aiohttp import ClientSession

from .exceptions import SensiboError, AuthenticationError

APIV1 = "https://home.sensibo.com/api/v1"
APIV2 = "https://home.sensibo.com/api/v2"

TIMEOUT = 5 * 60


class SensiboClient(object):
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

    async def async_get_devices(self, fields: str = "*") -> dict[str, Any]:
        """Get all devices.

        fields: * for all fields or specific fields
        """
        params = {"apiKey": self.api_key, "fields": fields}
        return await self._get(APIV2 + "/users/me/pods", params)

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

    async def async_get_timer(self, uid: str):
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

    async def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        """Make GET api call to Sensibo api."""
        async with self._session.get(path, params=params, timeout=self.timeout) as resp:
            if resp.status == 401:
                raise AuthenticationError("Invalid API key")
            if resp.status != 200:
                error = await resp.text()
                raise SensiboError(f"API error: {error}")
            try:
                response = await resp.json()
            except Exception as error:
                raise SensiboError(f"Could not return json {error}")
        return response["result"]

    async def _put(
        self, path: str, params: dict[str, Any], data: dict[str, Any]
    ) -> dict[str, Any]:
        """Make PUT api call to Sensibo api."""
        async with self._session.put(
            path, params=params, data=json.dumps(data), timeout=self.timeout
        ) as resp:
            if resp.status == 401:
                raise AuthenticationError("Invalid API key")
            if resp.status != 200:
                error = await resp.text()
                raise SensiboError(f"API error: {error}")
            try:
                response = await resp.json()
            except Exception as error:
                raise SensiboError(f"Could not return json {error}")
        return response["result"]

    async def _post(
        self, path: str, params: dict[str, Any], data: dict[str, Any]
    ) -> dict[str, Any]:
        """Make POST api call to Sensibo api."""
        async with self._session.post(
            path, params=params, data=json.dumps(data), timeout=self.timeout
        ) as resp:
            if resp.status == 401:
                raise AuthenticationError("Invalid API key")
            if resp.status != 200:
                error = await resp.text()
                raise SensiboError(f"API error: {error}")
            try:
                response = await resp.json()
            except Exception as error:
                raise SensiboError(f"Could not return json {error}")
        return response["result"]

    async def _patch(
        self, path: str, params: dict[str, Any], data: dict[str, Any]
    ) -> dict[str, Any]:
        """Make PATCH api call to Sensibo api."""
        async with self._session.patch(
            path, params=params, data=json.dumps(data), timeout=self.timeout
        ) as resp:
            if resp.status == 401:
                raise AuthenticationError("Invalid API key")
            if resp.status != 200:
                error = await resp.text()
                raise SensiboError(f"API error: {error}")
            try:
                response = await resp.json()
            except Exception as error:
                raise SensiboError(f"Could not return json {error}")
        return response["result"]

    async def _delete(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        """Make DELETE api call to Sensibo api."""
        async with self._session.delete(
            path, params=params, timeout=self.timeout
        ) as resp:
            if resp.status == 401:
                raise AuthenticationError("Invalid API key")
            if resp.status != 200:
                error = await resp.text()
                raise SensiboError(f"API error: {error}")
            try:
                response = await resp.json()
            except Exception as error:
                raise SensiboError(f"Could not return json {error}")
        return response["result"]
