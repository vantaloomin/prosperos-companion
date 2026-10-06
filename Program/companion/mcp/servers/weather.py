"""The built-in weather server: a read-only MCP server on stdio, needing no key (PRD X1-X3).

Run as `python companion/mcp/servers/weather.py`; the app starts it for each lookup. One tool,
`get_forecast`, finds a place with Open-Meteo's geocoding (unless coordinates are given) and
returns today's conditions from Open-Meteo. When Open-Meteo fails for a US place, it asks the
National Weather Service instead. Only the place name or coordinates leave the computer.

Open-Meteo is free for non-commercial use with attribution (CC BY 4.0); the National Weather
Service asks for an identifying User-Agent. `PROSPERO_WEATHER_ENDPOINTS` (JSON) overrides the
service addresses, for tests.
"""
import json
import os
import sys

import httpx

PROTOCOL_VERSIONS = ('2025-11-25', '2025-06-18', '2025-03-26')
VERSION = '1.0'
USER_AGENT = 'ProsperoCompanion/1.0 (built-in weather server)'
ENDPOINTS = {'geocoding': 'https://geocoding-api.open-meteo.com/v1/search',
             'forecast': 'https://api.open-meteo.com/v1/forecast',
             'nws': 'https://api.weather.gov'}
TIMEOUT = 8
ATTRIBUTION = 'Weather data by Open-Meteo.com (CC BY 4.0).'

TOOL = {
    'name': 'get_forecast',
    'description': "Today's weather for a city or region: conditions, high, low and chance of rain.",
    'inputSchema': {'type': 'object', 'properties': {
        'location': {'type': 'string', 'description': 'City or region, such as "Baltimore, MD".'},
        'latitude': {'type': 'number', 'description': 'Optional; used instead of looking up the place.'},
        'longitude': {'type': 'number', 'description': 'Optional; used with latitude.'}},
        'required': ['location']},
    'annotations': {'readOnlyHint': True, 'openWorldHint': True},
}

# WMO weather interpretation codes, as Open-Meteo reports them.
CODES = {0: 'clear', 1: 'mainly clear', 2: 'partly cloudy', 3: 'overcast', 45: 'fog', 48: 'freezing fog',
         51: 'light drizzle', 53: 'drizzle', 55: 'heavy drizzle', 56: 'freezing drizzle', 57: 'freezing drizzle',
         61: 'light rain', 63: 'rain', 65: 'heavy rain', 66: 'freezing rain', 67: 'freezing rain',
         71: 'light snow', 73: 'snow', 75: 'heavy snow', 77: 'snow grains', 80: 'light showers', 81: 'showers',
         82: 'heavy showers', 85: 'snow showers', 86: 'heavy snow showers', 95: 'thunderstorms',
         96: 'thunderstorms with hail', 99: 'thunderstorms with hail'}


class WeatherError(Exception):
    pass


def endpoints() -> dict:
    return ENDPOINTS | json.loads(os.environ.get('PROSPERO_WEATHER_ENDPOINTS') or '{}')


def get_json(client, url, params=None) -> dict:
    try:
        response = client.get(url, params=params)
    except httpx.HTTPError as error:
        raise WeatherError('The weather service could not be reached.') from error
    if response.status_code != 200:
        raise WeatherError(f'The weather service answered with HTTP {response.status_code}.')
    try:
        return response.json()
    except ValueError as error:
        raise WeatherError('The weather service sent an unreadable answer.') from error


def geocode(client, location: str) -> dict:
    """The best match for "City, Region" (the city searched, the region used to choose among results)."""
    name, _, qualifier = location.partition(',')
    found = get_json(client, endpoints()['geocoding'], {'name': name.strip(), 'count': 10, 'format': 'json'})
    results = found.get('results') or []
    if not results:
        raise WeatherError(f'No place called {name.strip()} was found.')
    wanted = qualifier.strip().lower()

    def matches(item) -> bool:
        fields = [str(item.get(key) or '').lower() for key in ('admin1', 'country', 'country_code')]
        return any(wanted and (wanted == field or wanted in field) for field in fields) or \
            (len(wanted) == 2 and item.get('country_code') == 'US' and US_STATES.get(wanted.upper()) ==
             str(item.get('admin1') or ''))

    chosen = next((item for item in results if matches(item)), results[0]) if wanted else results[0]
    label = ', '.join(str(part) for part in (chosen.get('name'), chosen.get('admin1'), chosen.get('country_code'))
                      if part)
    return {'label': label, 'latitude': chosen['latitude'], 'longitude': chosen['longitude'],
            'country_code': chosen.get('country_code')}


def open_meteo(client, place: dict) -> dict:
    data = get_json(client, endpoints()['forecast'], {
        'latitude': place['latitude'], 'longitude': place['longitude'], 'timezone': 'auto', 'forecast_days': 1,
        'temperature_unit': 'fahrenheit', 'current': 'temperature_2m,weather_code',
        'daily': 'weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max'})
    daily, now = data.get('daily') or {}, data.get('current') or {}
    try:
        high, low = round(daily['temperature_2m_max'][0]), round(daily['temperature_2m_min'][0])
    except (KeyError, IndexError, TypeError) as error:
        raise WeatherError('The weather service sent no forecast for today.') from error
    code = (daily.get('weather_code') or [None])[0]
    chance = (daily.get('precipitation_probability_max') or [None])[0]
    current = now.get('temperature_2m')
    return {'condition': CODES.get(code, 'mixed conditions'), 'high_f': high, 'low_f': low,
            'precipitation_chance': chance, 'temperature_f': round(current) if current is not None else None,
            'source': 'Open-Meteo'}


def national_weather_service(client, place: dict) -> dict:
    point = get_json(client, f"{endpoints()['nws']}/points/{place['latitude']:.4f},{place['longitude']:.4f}")
    url = (point.get('properties') or {}).get('forecast')
    if not url:
        raise WeatherError('The National Weather Service has no forecast for this place.')
    periods = (get_json(client, url).get('properties') or {}).get('periods') or []
    if not periods:
        raise WeatherError('The National Weather Service sent no forecast periods.')
    temperatures = [fahrenheit(item) for item in periods[:2] if item.get('temperature') is not None]
    first = periods[0]
    chance = (first.get('probabilityOfPrecipitation') or {}).get('value')
    return {'condition': str(first.get('shortForecast') or 'mixed conditions').lower(), 'high_f': max(temperatures),
            'low_f': min(temperatures), 'precipitation_chance': chance, 'temperature_f': None,
            'source': 'National Weather Service'}


def fahrenheit(period: dict) -> int:
    value = period['temperature']
    return round(value * 9 / 5 + 32) if period.get('temperatureUnit') == 'C' else round(value)


def forecast(arguments: dict, client) -> dict:
    location = str(arguments.get('location') or '').strip()[:120]
    latitude, longitude = arguments.get('latitude'), arguments.get('longitude')
    if isinstance(latitude, (int, float)) and isinstance(longitude, (int, float)):
        place = {'label': location or f'{latitude}, {longitude}', 'latitude': float(latitude),
                 'longitude': float(longitude), 'country_code': None}
    elif location:
        place = geocode(client, location)
    else:
        raise WeatherError('Give a location.')
    try:
        found = open_meteo(client, place)
    except WeatherError:
        if place['country_code'] not in {'US', None}:
            raise
        found = national_weather_service(client, place)
    parts = [f"{place['label']}: {found['condition']}, high {found['high_f']}°F, low {found['low_f']}°F"]
    if found['precipitation_chance'] is not None:
        parts.append(f"{found['precipitation_chance']}% chance of precipitation")
    if found['temperature_f'] is not None:
        parts.append(f"now {found['temperature_f']}°F")
    credit = ATTRIBUTION if found['source'] == 'Open-Meteo' else 'Forecast from the National Weather Service.'
    return {'text': ', '.join(parts) + f'. {credit}',
            'structured': {'location': place['label'], **found}}


def call(name: str, arguments: dict, client) -> dict:
    if name != TOOL['name']:
        return {'content': [{'type': 'text', 'text': f'Unknown tool {name}.'}], 'isError': True}
    try:
        result = forecast(arguments, client)
    except WeatherError as error:
        return {'content': [{'type': 'text', 'text': str(error)}], 'isError': True}
    return {'content': [{'type': 'text', 'text': result['text']}], 'structuredContent': result['structured']}


def handle(message: dict, client) -> dict | None:
    if 'id' not in message or 'method' not in message:
        return None
    method, params = message['method'], message.get('params') or {}
    if method == 'initialize':
        asked = params.get('protocolVersion')
        result = {'protocolVersion': asked if asked in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[0],
                  'capabilities': {'tools': {}}, 'serverInfo': {'name': 'prospero-weather', 'version': VERSION}}
    elif method == 'ping':
        result = {}
    elif method == 'tools/list':
        result = {'tools': [TOOL]}
    elif method == 'tools/call':
        result = call(params.get('name'), params.get('arguments') or {}, client)
    else:
        return {'jsonrpc': '2.0', 'id': message['id'], 'error': {'code': -32601, 'message': 'Method not found'}}
    return {'jsonrpc': '2.0', 'id': message['id'], 'result': result}


def main():
    with httpx.Client(timeout=TIMEOUT, headers={'User-Agent': USER_AGENT}, follow_redirects=False) as client:
        for line in sys.stdin:
            if not line.strip():
                continue
            try:
                message = json.loads(line)
            except ValueError:
                continue
            response = handle(message, client) if isinstance(message, dict) else None
            if response is not None:
                sys.stdout.write(json.dumps(response) + '\n')
                sys.stdout.flush()


US_STATES = {'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas', 'CA': 'California',
             'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware', 'DC': 'District of Columbia', 'FL': 'Florida',
             'GA': 'Georgia', 'HI': 'Hawaii', 'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa',
             'KS': 'Kansas', 'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
             'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi', 'MO': 'Missouri',
             'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada', 'NH': 'New Hampshire', 'NJ': 'New Jersey',
             'NM': 'New Mexico', 'NY': 'New York', 'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio',
             'OK': 'Oklahoma', 'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
             'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont',
             'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming'}


if __name__ == '__main__':
    main()
