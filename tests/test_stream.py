"""Tests for the event stream."""

from __future__ import annotations

import copy
import zlib
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import patch

import pytest
from aiohttp import ClientSession, web
from aiohttp.test_utils import TestServer

from pysensibo import (
    EVENT_CHANGED,
    EVENT_HELLO,
    EVENT_MEASUREMENTS,
    EVENT_RESYNC,
    SensiboClient,
    update_measurements,
)
from pysensibo.exceptions import (
    AuthenticationError,
    SensiboError,
    StreamUnavailableError,
)
from pysensibo.model import PureAQI, SensiboEvent

API_KEY = "test-key"

STREAM = [
    b'retry: 30000\nevent: hello\ndata: {"version":1,"heartbeatSeconds":120,"pods":2}\n\n',
    b": hb\n\n",
    b'event: measurements\ndata: {"id":"ABC999111","measurements":{"temperature":22.5,'
    b'"humidity":40.1,"feelsLike":22.5,"rssi":-50}}\n\n',
    b'event: changed\r\ndata: {"id":"ABC999111","fields":["acState"]}\r\n\r\n',
    b"event: resync\ndata: {}\n\n",
]

DEVICES: dict[str, Any] = {
    "status": "success",
    "result": [
        {
            "id": "ABC999111",
            "macAddress": "00:02:00:b6:00:00",
            "serial": "1234567890",
            "room": {"name": "Hallway"},
            "measurements": {
                "time": {"time": "2022-04-30T11:22:57.894846Z", "secondsAgo": 32},
                "temperature": 21.2,
                "humidity": 32.9,
                "motion": True,
                "roomIsOccupied": True,
                "feelsLike": 21.2,
                "rssi": -45,
            },
            "location": {"id": "ZZZZZZZZZZZZ", "name": "Home"},
            "autoOffEnabled": False,
            "autoOffMinutes": None,
            "antiMoldConfig": None,
            "acState": {"on": False, "mode": "heat", "targetTemperature": 25},
            "connectionStatus": {"isAlive": True},
            "remoteCapabilities": {"modes": {"heat": {}}},
            "temperatureUnit": "C",
            "firmwareVersion": "SKY30046",
            "currentlyAvailableFirmwareVersion": "SKY30046",
            "firmwareType": "esp8266ex",
            "productModel": "skyv2",
            "sensorsCalibration": {"temperature": 0.1, "humidity": 0.0},
            "mainMeasurementsSensor": {
                "id": "AABBCC",
                "measurements": {
                    "batteryVoltage": 3000,
                    "humidity": 57,
                    "motion": True,
                    "rssi": -72,
                    "temperature": 23.9,
                },
            },
            "motionSensors": [
                {
                    "id": "AABBCC",
                    "connectionStatus": {"isAlive": True},
                    "firmwareVersion": "V17",
                    "firmwareType": "nrf52",
                    "isMainSensor": True,
                    "productModel": "motion_sensor",
                    "measurements": {
                        "batteryVoltage": 3000,
                        "humidity": 57,
                        "motion": True,
                        "rssi": -72,
                        "temperature": 23.9,
                    },
                }
            ],
            "pureBoostConfig": None,
            "roomIsOccupied": True,
            "filtersCleaning": {},
            "timer": None,
            "smartMode": None,
            "schedules": [],
        },
        {
            "id": "AAZZAAZZ",
            "macAddress": "00:01:00:01:00:01",
            "serial": "0987654321",
            "room": {"name": "Kitchen"},
            "measurements": {"rssi": -58, "pm25": 1, "motion": False},
            "location": {"id": "ZZZZZZZZZZZZ", "name": "Home"},
            "autoOffEnabled": False,
            "autoOffMinutes": None,
            "antiMoldConfig": None,
            "acState": {"on": False, "fanLevel": "low"},
            "connectionStatus": {"isAlive": True},
            "remoteCapabilities": {"modes": {"fan": {}}},
            "temperatureUnit": "C",
            "firmwareVersion": "PUR00111",
            "currentlyAvailableFirmwareVersion": "PUR00111",
            "firmwareType": "pure-esp32",
            "productModel": "pure",
            "sensorsCalibration": {"temperature": 0.0, "humidity": 0.0},
            "mainMeasurementsSensor": None,
            "motionSensors": [],
            "pureBoostConfig": {"enabled": False, "sensitivity": "N"},
            "roomIsOccupied": None,
            "filtersCleaning": {},
            "timer": None,
            "smartMode": None,
            "schedules": [],
        },
    ],
}


async def _stream(request: web.Request) -> web.StreamResponse:
    """Send the events as the API does: one gzip stream, a flush for each event."""
    if request.headers.get("X-Api-Key") != API_KEY:
        return web.json_response({"status": "error"}, status=401)
    response = web.StreamResponse(
        headers={"Content-Type": "text/event-stream", "Content-Encoding": "gzip"}
    )
    await response.prepare(request)
    compressor = zlib.compressobj(wbits=31)
    for event in STREAM:
        compressed = compressor.compress(event) + compressor.flush(zlib.Z_SYNC_FLUSH)
        # Events do not arrive in one piece each.
        await response.write(compressed[:7])
        await response.write(compressed[7:])
    await response.write(compressor.flush())
    return response


@dataclass
class FakeApi:
    """A local server in the place of the Sensibo API."""

    handler: Callable[[web.Request], Awaitable[web.StreamResponse]] = _stream
    requests: list[web.Request] = field(default_factory=list)

    async def handle(self, request: web.Request) -> web.StreamResponse:
        """Answer a request for the event stream."""
        self.requests.append(request)
        return await self.handler(request)


@pytest.fixture(name="api")
async def api_fixture() -> AsyncIterator[FakeApi]:
    """Run a local server in the place of the Sensibo API."""
    api = FakeApi()
    app = web.Application()
    app.router.add_get("/api/v2/stream", api.handle)
    server = TestServer(app)
    await server.start_server()
    with patch("pysensibo.APIV2", str(server.make_url("/api/v2"))):
        yield api
    await server.close()


@pytest.fixture(name="client")
async def client_fixture() -> AsyncIterator[SensiboClient]:
    """Return a client with its own session."""
    async with ClientSession() as session:
        yield SensiboClient(API_KEY, session)


@pytest.mark.usefixtures("api")
async def test_stream_gives_the_events(client: SensiboClient) -> None:
    """The events arrive in sequence and the iteration stops at the close."""
    events = [event async for event in client.async_stream_events()]

    assert [event.name for event in events] == [
        EVENT_HELLO,
        EVENT_MEASUREMENTS,
        EVENT_CHANGED,
        EVENT_RESYNC,
    ]
    assert events[0].data == {"version": 1, "heartbeatSeconds": 120, "pods": 2}
    assert events[1].id == "ABC999111"
    assert events[1].data["measurements"]["temperature"] == 22.5
    assert events[2].data["fields"] == ["acState"]
    assert events[3].data == {}


async def test_stream_keeps_the_api_key_out_of_the_url(
    api: FakeApi, client: SensiboClient
) -> None:
    """The API key is in a header."""
    _ = [event async for event in client.async_stream_events()]

    request = api.requests[0]
    assert request.query_string == ""
    assert request.headers["Accept"] == "text/event-stream"


@pytest.mark.usefixtures("api")
async def test_stream_authentication_error() -> None:
    """A wrong API key raises AuthenticationError."""
    async with ClientSession() as session:
        client = SensiboClient("wrong", session)
        with pytest.raises(AuthenticationError):
            _ = [event async for event in client.async_stream_events()]


@pytest.mark.parametrize(
    ("status", "headers", "retry_after"),
    [
        (429, {"Retry-After": "300"}, 300),
        (503, {"Retry-After": "soon"}, None),
        (503, {}, None),
    ],
)
async def test_stream_unavailable(
    api: FakeApi,
    client: SensiboClient,
    status: int,
    headers: dict[str, str],
    retry_after: float | None,
) -> None:
    """The API does not accept the stream now."""

    async def refuse(_: web.Request) -> web.StreamResponse:
        return web.json_response({"status": "error"}, status=status, headers=headers)

    api.handler = refuse
    with pytest.raises(StreamUnavailableError) as error:
        _ = [event async for event in client.async_stream_events()]
    assert error.value.retry_after == retry_after
    assert isinstance(error.value, SensiboError)


async def test_stream_other_error(api: FakeApi, client: SensiboClient) -> None:
    """Another status raises SensiboError."""

    async def fail(_: web.Request) -> web.StreamResponse:
        return web.Response(text="not here", status=404)

    api.handler = fail
    with pytest.raises(SensiboError, match="not here"):
        _ = [event async for event in client.async_stream_events()]


async def test_stream_ignores_events_without_a_json_object(
    api: FakeApi, client: SensiboClient
) -> None:
    """Data that is not a JSON object gives no event."""

    async def odd(_: web.Request) -> web.StreamResponse:
        return web.Response(
            body=b"event: changed\ndata: not json\n\n"
            b"event: changed\ndata: [1]\n\n"
            b'data: {"id":\ndata: "ABC999111"}\n\n'
            b'event: changed\ndata: {"id":"lost"}',
            content_type="text/event-stream",
        )

    api.handler = odd
    events = [event async for event in client.async_stream_events()]

    assert events == [SensiboEvent(name="message", data={"id": "ABC999111"})]


async def _devices_data(client: SensiboClient, devices: dict[str, Any]) -> Any:
    with patch.object(client, "async_get_devices", return_value=devices):
        return await client.async_get_devices_data()


async def test_update_measurements_is_the_same_as_a_new_fetch(
    client: SensiboClient,
) -> None:
    """An event gives the same data as a fetch after the change."""
    data = await _devices_data(client, copy.deepcopy(DEVICES))
    sky = {"temperature": 25.5, "humidity": 45.5, "feelsLike": 25.7, "motion": False}
    pure = {"pm25": 2, "motion": True, "rssi": -60}
    sensor = {"temperature": 19.5, "humidity": 60, "motion": False, "rssi": -70}

    assert update_measurements(
        data, SensiboEvent(EVENT_MEASUREMENTS, {"id": "ABC999111", "measurements": sky})
    )
    assert update_measurements(
        data, SensiboEvent(EVENT_MEASUREMENTS, {"id": "AAZZAAZZ", "measurements": pure})
    )
    assert update_measurements(
        data,
        SensiboEvent(
            EVENT_MEASUREMENTS,
            {"id": "AABBCC", "podId": "ABC999111", "measurements": sensor},
        ),
    )

    changed = copy.deepcopy(DEVICES)
    changed["result"][0]["measurements"].update(sky)
    changed["result"][0]["motionSensors"][0]["measurements"].update(sensor)
    changed["result"][0]["mainMeasurementsSensor"]["measurements"].update(sensor)
    changed["result"][1]["measurements"].update(pure)
    expected = await _devices_data(client, changed)
    assert data.parsed == expected.parsed
    assert data.raw == expected.raw
    # the motion sensor is the main sensor of the device
    assert data.parsed["ABC999111"].temp == 19.5
    assert data.parsed["ABC999111"].feelslike == 25.7
    assert data.parsed["AAZZAAZZ"].pm25_pure is PureAQI.MODERATE
    # the event has no roomIsOccupied: the value stays
    assert data.raw["result"][0]["measurements"]["roomIsOccupied"] is True


@pytest.mark.parametrize(
    "event_data",
    [
        {"id": "UNKNOWN", "measurements": {"temperature": 20}},
        {"id": "UNKNOWN", "podId": "ABC999111", "measurements": {"temperature": 20}},
        {"id": "AABBCC", "podId": "UNKNOWN", "measurements": {"temperature": 20}},
        {"id": "ABC999111"},
        {"measurements": {"temperature": 20}},
    ],
)
async def test_update_measurements_of_an_unknown_device(
    client: SensiboClient, event_data: dict[str, Any]
) -> None:
    """The caller must get the devices again."""
    data = await _devices_data(client, copy.deepcopy(DEVICES))
    before = copy.deepcopy(data)

    assert not update_measurements(data, SensiboEvent(EVENT_MEASUREMENTS, event_data))
    assert data == before
