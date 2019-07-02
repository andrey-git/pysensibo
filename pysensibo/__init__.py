"""asyncio-friendly python API for Sensibo (https://sensibo.com)."""
import asyncio
import json
import aiohttp

_SERVER = 'https://home.sensibo.com/api/v2'


class SensiboError(Exception):
    """Generic error of Sensibo unit."""

    pass


class SensiboClient(object):
    """Sensibo client implementation."""

    def __init__(self, api_key, session=None,
                 timeout=aiohttp.client.DEFAULT_TIMEOUT):
        """Constructor.

        api_key: Key from https://home.sensibo.com/me/api
        session: aiohttp.ClientSession or None to create a new session.
        """
        self._params = {'apiKey': api_key}
        self._timeout = timeout
        if session is not None:
            self._session = session
        else:
            self._session = aiohttp.ClientSession()

    @asyncio.coroutine
    def async_get_devices(self, fields='*'):
        """Get all devices."""
        return (yield from self._get('/users/me/pods', fields=fields))

    @asyncio.coroutine
    def async_get_device(self, uid, fields='*'):
        """Get specific device by ID."""
        return (yield from self._get('/pods/{}'.format(uid),
                                     fields=fields))

    @asyncio.coroutine
    def async_get_measurements(self, uid, fields='*'):
        """Get measurements of a device."""
        return (yield from self._get('/pods/{}/measurements'.format(uid),
                                     fields=fields))[0]

    @asyncio.coroutine
    def async_get_ac_states(self, uid, limit=1, offset=0, fields='*'):
        """Get log entries of a device."""
        return (yield from self._get('/pods/{}/acStates'.format(uid),
                                     limit=limit,
                                     fields=fields,
                                     offset=offset))

    @asyncio.coroutine
    def async_get_ac_state_log(self, uid, log_id, fields='*'):
        """Get a specific log entry."""
        return (
            yield from self._get('/pods/{}/acStates/{}'.format(uid, log_id),
                                 fields=fields))

    @asyncio.coroutine
    def async_set_ac_state_property(
            self, uid, name, value, ac_state=None, assumed_state=False):
        """Set a specific device property."""
        if ac_state is None:
            ac_state = yield from self.async_get_ac_states(uid)
            ac_state = ac_state[0]['acState']
        data = {
            'currentAcState': ac_state,
            'newValue': value
        }
        if assumed_state:
            data['reason'] = "StateCorrectionByUser"
        resp = yield from self._session.patch(
            _SERVER + '/pods/{}/acStates/{}'.format(uid, name),
            data=json.dumps(data),
            params=self._params,
            timeout=self._timeout)
        try:
            return (yield from resp.json())['result']
        except aiohttp.client_exceptions.ContentTypeError:
            pass
        raise SensiboError((yield from resp.text()))

    @asyncio.coroutine
    def async_set_ac_state(self, uid, payload):
        """Set a complete device state"""
        data = {
            'acState': payload
        }

        resp = yield from self._session.post(
            _SERVER + '/pods/{}/acStates'.format(uid),
            data=json.dumps(data),
            params=self._params,
            timeout=self._timeout)
        try:
            return (yield from resp.json())['result']
        except aiohttp.client_exceptions.ContentTypeError:
            pass
        raise SensiboError((yield from resp.text()))

    @asyncio.coroutine
    def _get(self, path, **kwargs):
        resp = yield from self._session.get(
            _SERVER + path, params=dict(self._params, **kwargs),
            timeout=self._timeout)
        try:
            return (yield from resp.json())['result']
        except aiohttp.client_exceptions.ContentTypeError:
            pass
        raise SensiboError((yield from resp.text()))
