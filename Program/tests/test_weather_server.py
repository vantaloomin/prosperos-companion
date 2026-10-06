"""The built-in weather server (companion/mcp/servers/weather.py), against recorded Open-Meteo and NWS answers."""
import asyncio
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from companion.mcp import client as mcp
from companion.mcp.servers import weather

PLACES = {'results': [
    {'name': 'Baltimore', 'latitude': 52.0, 'longitude': -9.0, 'country_code': 'IE', 'country': 'Ireland',
     'admin1': 'Munster'},
    {'name': 'Baltimore', 'latitude': 39.29, 'longitude': -76.61, 'country_code': 'US', 'country': 'United States',
     'admin1': 'Maryland'},
]}
FORECAST = {'current': {'temperature_2m': 58.1, 'weather_code': 61},
            'daily': {'weather_code': [61], 'temperature_2m_max': [61.2], 'temperature_2m_min': [52.3],
                      'precipitation_probability_max': [70]}}
POINT = {'properties': {'forecast': 'https://api.weather.gov/gridpoints/LWX/109,91/forecast'}}
PERIODS = {'properties': {'periods': [
    {'temperature': 64, 'temperatureUnit': 'F', 'shortForecast': 'Chance Showers',
     'probabilityOfPrecipitation': {'value': 40}},
    {'temperature': 50, 'temperatureUnit': 'F', 'shortForecast': 'Mostly Cloudy'}]}}


def recorded(answers: dict, seen: list | None = None):
    """A client whose requests get the answer for the first matching path fragment."""
    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        for fragment, answer in answers.items():
            if fragment in str(request.url):
                status, body = answer if isinstance(answer, tuple) else (200, answer)
                return httpx.Response(status, json=body)
        return httpx.Response(404, json={})
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_geocoding_uses_the_region_to_choose():
    client = recorded({'geocoding': PLACES})
    assert weather.geocode(client, 'Baltimore, MD')['label'] == 'Baltimore, Maryland, US'
    assert weather.geocode(client, 'Baltimore, Ireland')['country_code'] == 'IE'
    assert weather.geocode(client, 'Baltimore')['country_code'] == 'IE'  # the service's best match first
    with pytest.raises(weather.WeatherError, match='No place called Atlantis'):
        weather.geocode(recorded({'geocoding': {}}), 'Atlantis')


def test_open_meteo_forecast_and_what_is_sent():
    seen = []
    result = weather.forecast({'location': 'Baltimore, MD'}, recorded({'geocoding': PLACES, 'forecast': FORECAST}, seen))
    assert result['text'] == ('Baltimore, Maryland, US: light rain, high 61°F, low 52°F, 70% chance of precipitation, '
                              'now 58°F. Weather data by Open-Meteo.com (CC BY 4.0).')
    assert result['structured'] == {'location': 'Baltimore, Maryland, US', 'condition': 'light rain', 'high_f': 61,
                                    'low_f': 52, 'precipitation_chance': 70, 'temperature_f': 58,
                                    'source': 'Open-Meteo'}
    assert parse_qs(seen[0].url.query.decode())['name'] == ['Baltimore']
    sent = parse_qs(seen[1].url.query.decode())
    assert (sent['latitude'], sent['longitude'], sent['temperature_unit']) == (['39.29'], ['-76.61'], ['fahrenheit'])


def test_coordinates_skip_geocoding():
    seen = []
    weather.forecast({'location': 'Home', 'latitude': 39.29, 'longitude': -76.61},
                     recorded({'forecast': FORECAST}, seen))
    assert [request.url.host for request in seen] == ['api.open-meteo.com']


def test_national_weather_service_fallback_for_us_places():
    client = recorded({'geocoding': PLACES, 'open-meteo.com/v1/forecast': (502, {}), '/points/': POINT,
                       '/forecast': PERIODS})
    result = weather.forecast({'location': 'Baltimore, MD'}, client)
    assert result['text'] == ('Baltimore, Maryland, US: chance showers, high 64°F, low 50°F, 40% chance of '
                              'precipitation. Forecast from the National Weather Service.')
    assert result['structured']['source'] == 'National Weather Service'
    abroad = recorded({'geocoding': PLACES, 'open-meteo.com/v1/forecast': (502, {})})
    with pytest.raises(weather.WeatherError, match='HTTP 502'):
        weather.forecast({'location': 'Baltimore, Ireland'}, abroad)


def test_failures_are_tool_errors():
    def unreachable(request):
        raise httpx.ConnectError('down')
    down = httpx.Client(transport=httpx.MockTransport(unreachable))
    result = weather.call('get_forecast', {'location': 'Baltimore'}, down)
    assert result == {'content': [{'type': 'text', 'text': 'The weather service could not be reached.'}],
                      'isError': True}
    assert weather.call('get_forecast', {}, down)['isError'] is True
    assert weather.call('send_email', {}, down)['isError'] is True
    unknown = weather.handle({'jsonrpc': '2.0', 'id': 1, 'method': 'resources/list'}, down)
    assert unknown['error']['code'] == -32601
    assert weather.handle({'jsonrpc': '2.0', 'method': 'notifications/initialized'}, down) is None


class Recorded(BaseHTTPRequestHandler):
    """Open-Meteo and the NWS on 127.0.0.1, for the server run as a real program."""
    requests: list = []

    def do_GET(self):
        url = urlparse(self.path)
        Recorded.requests.append(url.path)
        body = PLACES if url.path == '/geocoding' else FORECAST if url.path == '/forecast' else None
        self.send_response(200 if body else 404)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(body or {}).encode())

    def log_message(self, *args):
        pass


@pytest.fixture
def services(monkeypatch):
    server = ThreadingHTTPServer(('127.0.0.1', 0), Recorded)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}'
    monkeypatch.setenv('PROSPERO_WEATHER_ENDPOINTS', json.dumps(
        {'geocoding': f'{base}/geocoding', 'forecast': f'{base}/forecast', 'nws': f'{base}/nws'}))
    monkeypatch.setenv('NO_PROXY', '127.0.0.1')
    Recorded.requests = []
    yield Recorded.requests
    server.shutdown()


def test_runs_as_a_program_over_stdio(services):
    env = {key: os.environ[key] for key in ('PROSPERO_WEATHER_ENDPOINTS', 'NO_PROXY')}

    async def scenario():
        transport = mcp.StdioTransport([sys.executable, '-I', weather.__file__], env)
        async with mcp.open_session(transport) as session:
            return session.server, await session.list_tools(), await session.call_tool(
                'get_forecast', {'location': 'Baltimore, MD'})

    server, tools, result = asyncio.run(scenario())
    assert server['name'] == 'prospero-weather' and server['protocol'] in weather.PROTOCOL_VERSIONS
    assert [(tool['name'], tool['read_only']) for tool in tools] == [('get_forecast', True)]
    assert result['text'].startswith('Baltimore, Maryland, US: light rain, high 61°F')
    assert services == ['/geocoding', '/forecast']


def test_built_in_service_in_the_app(client, companion, services):
    client.put('/api/context/location', json={'user_place': 'Baltimore, MD'})
    created = client.post('/api/context/services/builtin', json={'kind': 'weather'})
    assert created.status_code == 200, created.text
    service = created.json()
    assert (service['name'], service['builtin'], service['transport']) == ('Built-in weather', 'weather', 'stdio')
    assert client.post('/api/context/services/builtin', json={'kind': 'weather'}).status_code == 409
    checked = client.post(f"/api/context/services/{service['id']}/check").json()
    assert checked['check_error'] is None
    suggestion = checked['suggestions']['weather']
    assert suggestion == {'tool': 'get_forecast', 'arguments': {'location': {'source': 'place'}}, 'missing': []}
    saved = client.put(f"/api/context/services/{service['id']}/tools/weather",
                       json={'tool': 'get_forecast', 'arguments': suggestion['arguments'],
                             'run_in': ['conversation', 'companion_city']}).json()
    disclosure = saved['mappings'][0]['disclosure']
    assert 'Open-Meteo' in disclosure['destination'] and 'National Weather Service' in disclosure['destination']
    enabled = client.post(f"/api/context/services/{service['id']}/tools/weather/enable",
                          json={'digest': disclosure['digest']})
    assert enabled.status_code == 200, enabled.text
    found = client.post('/api/context/lookup', json={'category': 'weather'}).json()['observations']
    assert found[0]['status'] == 'ok'
    assert found[0]['arguments'] == {'location': 'Baltimore, MD'}
    assert found[0]['structured']['high_f'] == 61
    assert 'Open-Meteo.com (CC BY 4.0)' in found[0]['content']
