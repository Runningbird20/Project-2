import json
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class OfficeLocationGeocodingError(Exception):
    pass


def _normalize_whitespace(value):
    return re.sub(r"\s+", " ", (value or "").strip())


def _split_state_postal(value):
    cleaned = _normalize_whitespace(value).replace(",", " ")
    match = re.search(r"\b([A-Za-z]{2})\s+(\d{5})(?:-\d{4})?\b", cleaned)
    if match:
        return match.group(1).upper(), match.group(2)
    state_match = re.search(r"\b([A-Za-z]{2})\b", cleaned)
    state = state_match.group(1).upper() if state_match else ""
    zip_match = re.search(r"\b(\d{5})(?:-\d{4})?\b", cleaned)
    postal = zip_match.group(1) if zip_match else ""
    return state, postal


def _candidate_queries(address_query):
    raw = _normalize_whitespace(address_query)
    if not raw:
        return []

    parts = [_normalize_whitespace(part) for part in raw.split(",") if _normalize_whitespace(part)]
    candidates = [raw]

    # If we have something like "line1, line2, city, ST ZIP, country", retry without line2.
    if len(parts) >= 5:
        without_line2 = ", ".join([parts[0]] + parts[2:])
        candidates.append(without_line2)

    # Try with zip5-only normalization.
    state = ""
    postal = ""
    for part in reversed(parts):
        maybe_state, maybe_postal = _split_state_postal(part)
        if maybe_state or maybe_postal:
            state = maybe_state or state
            postal = maybe_postal or postal
            break
    if state or postal:
        replacement = f"{state} {postal}".strip()
        if replacement and parts:
            rebuilt = list(parts)
            for idx in range(len(rebuilt) - 1, -1, -1):
                if any(ch.isdigit() for ch in rebuilt[idx]) or re.search(r"\b[A-Za-z]{2}\b", rebuilt[idx]):
                    rebuilt[idx] = replacement
                    break
            candidates.append(", ".join(rebuilt))

    # Broad fallback: city/state level when street-level lookup fails.
    if len(parts) >= 3:
        candidates.append(", ".join(parts[-3:]))

    unique = []
    seen = set()
    for candidate in candidates:
        normalized = _normalize_whitespace(candidate)
        key = normalized.lower()
        if normalized and key not in seen:
            seen.add(key)
            unique.append(normalized)
    return unique


def geocode_office_address(address_query):
    queries = _candidate_queries(address_query)
    if not queries:
        raise OfficeLocationGeocodingError('Address could not be pinned. Please verify address, city, state, and zip.')

    last_exception = None
    for query in queries:
        params_dict = {
            'q': query,
            'format': 'jsonv2',
            'limit': 1,
            'addressdetails': 0,
        }
        lower_query = query.lower()
        if any(token in lower_query for token in ['united states', ', us', ', usa', ' usa']):
            params_dict['countrycodes'] = 'us'

        params = urlencode(params_dict)
        url = f'https://nominatim.openstreetmap.org/search?{params}'
        request = Request(
            url,
            headers={
                'User-Agent': 'project2-jobposts-map/1.0',
                'Accept-Language': 'en-US,en;q=0.9',
            },
        )

        try:
            with urlopen(request, timeout=8) as response:
                payload = json.loads(response.read().decode('utf-8'))
        except Exception as exc:
            last_exception = exc
            continue

        if payload:
            first_result = payload[0]
            return first_result['lat'], first_result['lon']

    if last_exception is not None:
        raise OfficeLocationGeocodingError('Could not contact map service. Please try again.') from last_exception
    raise OfficeLocationGeocodingError('Address could not be pinned. Please verify address, city, state, and zip.')
