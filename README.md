[![size_badge](https://img.shields.io/github/repo-size/andrey-git/pysensibo?style=for-the-badge&cacheSeconds=3600)](https://github.com/andrey-git/pysensibo)
[![version_badge](https://img.shields.io/github/v/release/andrey-git/pysensibo?label=Latest%20release&style=for-the-badge&cacheSeconds=3600)](https://github.com/andrey-git/pysensibo/releases/latest)
[![download_badge](https://img.shields.io/pypi/dm/pysensibo?style=for-the-badge&cacheSeconds=3600)](https://github.com/andrey-git/pysensibo/releases/latest)
![GitHub Repo stars](https://img.shields.io/github/stars/andrey-git/pysensibo?style=for-the-badge&cacheSeconds=3600)
![GitHub Issues or Pull Requests](https://img.shields.io/github/issues/andrey-git/pysensibo?style=for-the-badge&cacheSeconds=3600)
![GitHub License](https://img.shields.io/github/license/andrey-git/pysensibo?style=for-the-badge&cacheSeconds=3600)

[![Made for Home Assistant](https://img.shields.io/badge/Made_for-Home%20Assistant-blue?style=for-the-badge&logo=homeassistant)](https://github.com/home-assistant)

[![Sponsor me](https://img.shields.io/badge/Sponsor-Me-blue?style=for-the-badge&logo=github)](https://github.com/sponsors/gjohansson-ST)
[![Discord](https://img.shields.io/discord/872446427664625664?style=for-the-badge&label=Discord&cacheSeconds=3600)](https://discord.gg/EG7cWFQMGW)

# pysensibo
asyncio-friendly python API for Sensibo (https://sensibo.com). Supported on Python 3.11+

Package has been made specifically for [Home Assistant](https://www.home-assistant.io/)

For example usage see test-files

## Event stream

The Sensibo API has an event stream (Server-Sent Events) that tells when a device
changes. With an open stream there is no need to poll the devices frequently:

```python
from pysensibo import (
    EVENT_CHANGED,
    EVENT_HELLO,
    EVENT_MEASUREMENTS,
    SensiboClient,
    update_measurements,
)

data = await client.async_get_devices_data()
async for event in client.async_stream_events():
    if event.name == EVENT_MEASUREMENTS and update_measurements(data, event):
        continue  # data has the new measurements
    if event.name in (EVENT_HELLO, EVENT_CHANGED, EVENT_MEASUREMENTS):
        data = await client.async_get_devices_data()
```

- `hello`: the stream is open, get the devices now.
- `measurements`: new measurements of a device or a motion sensor.
  `update_measurements` puts them into the data.
- `changed`: something else changed on the device (the AC state, a timer, the
  connection...), get the devices again.
- `resync`: the API closes the stream, open it again.

The iteration stops when the API closes the stream (at least one time in some
hours). Open it again after a delay with a random part, and make the delay longer
after each failure. `StreamUnavailableError` means that the API does not accept the
stream now: wait at least its `retry_after` seconds. While the stream is not open,
poll as before. While it is open, a slow poll (15 minutes or more) is still
necessary, because not every field has an event.
