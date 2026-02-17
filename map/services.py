import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class OfficeLocationGeocodingError(Exception):
    pass


def geocode_office_address(address_query):
    params = urlencode(
        {
            'q': address_query,
            'format': 'jsonv2',
            'limit': 1,
        }
    )
    url = f'https://nominatim.openstreetmap.org/search?{params}'
    request = Request(
        url,
        headers={
            'User-Agent': 'project2-jobposts-map/1.0',
        },
    )

    try:
        with urlopen(request, timeout=8) as response:
            payload = json.loads(response.read().decode('utf-8'))
    except Exception as exc:
        raise OfficeLocationGeocodingError('Could not contact map service. Please try again.') from exc

    if not payload:
        raise OfficeLocationGeocodingError('Address could not be pinned. Please verify address, city, state, and zip.')

    first_result = payload[0]
    return first_result['lat'], first_result['lon']
