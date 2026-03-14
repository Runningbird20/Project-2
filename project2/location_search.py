import re


US_STATE_TO_ABBR = {
    "Alabama": "AL",
    "Alaska": "AK",
    "Arizona": "AZ",
    "Arkansas": "AR",
    "California": "CA",
    "Colorado": "CO",
    "Connecticut": "CT",
    "Delaware": "DE",
    "District of Columbia": "DC",
    "Florida": "FL",
    "Georgia": "GA",
    "Hawaii": "HI",
    "Idaho": "ID",
    "Illinois": "IL",
    "Indiana": "IN",
    "Iowa": "IA",
    "Kansas": "KS",
    "Kentucky": "KY",
    "Louisiana": "LA",
    "Maine": "ME",
    "Maryland": "MD",
    "Massachusetts": "MA",
    "Michigan": "MI",
    "Minnesota": "MN",
    "Mississippi": "MS",
    "Missouri": "MO",
    "Montana": "MT",
    "Nebraska": "NE",
    "Nevada": "NV",
    "New Hampshire": "NH",
    "New Jersey": "NJ",
    "New Mexico": "NM",
    "New York": "NY",
    "North Carolina": "NC",
    "North Dakota": "ND",
    "Ohio": "OH",
    "Oklahoma": "OK",
    "Oregon": "OR",
    "Pennsylvania": "PA",
    "Rhode Island": "RI",
    "South Carolina": "SC",
    "South Dakota": "SD",
    "Tennessee": "TN",
    "Texas": "TX",
    "Utah": "UT",
    "Vermont": "VT",
    "Virginia": "VA",
    "Washington": "WA",
    "West Virginia": "WV",
    "Wisconsin": "WI",
    "Wyoming": "WY",
}

_CANONICAL_STATE_NAMES = {name.lower(): name for name in US_STATE_TO_ABBR}
_STATE_NAME_TO_ABBR = {name.lower(): abbr for name, abbr in US_STATE_TO_ABBR.items()}
_STATE_ABBR_TO_NAME = {abbr: name for name, abbr in US_STATE_TO_ABBR.items()}
_ORDERED_STATE_NAMES = sorted(US_STATE_TO_ABBR.keys(), key=len, reverse=True)
_MULTISPACE_RE = re.compile(r"\s+")


def _normalize_spaces(raw_value):
    return _MULTISPACE_RE.sub(" ", (raw_value or "").strip())


def _recognized_state_terms(raw_phrase):
    phrase = _normalize_spaces(raw_phrase)
    if not phrase:
        return set()

    state_abbr = _STATE_NAME_TO_ABBR.get(phrase.lower())
    if state_abbr:
        return {_CANONICAL_STATE_NAMES[phrase.lower()], state_abbr}

    state_name = _STATE_ABBR_TO_NAME.get(phrase.upper())
    if state_name:
        return {phrase.upper(), state_name}

    return set()


def _alternate_state_phrase(raw_phrase):
    phrase = _normalize_spaces(raw_phrase)
    if not phrase:
        return ""

    state_abbr = _STATE_NAME_TO_ABBR.get(phrase.lower())
    if state_abbr:
        return state_abbr

    return _STATE_ABBR_TO_NAME.get(phrase.upper(), "")


def _extract_trailing_city_and_state(query):
    normalized = _normalize_spaces(query)
    if not normalized:
        return "", set()

    comma_parts = [_normalize_spaces(part) for part in normalized.split(",") if _normalize_spaces(part)]
    if len(comma_parts) >= 2:
        city_term = ", ".join(comma_parts[:-1])
        state_terms = _recognized_state_terms(comma_parts[-1])
        if city_term and state_terms:
            return city_term, state_terms

    lowered_query = normalized.lower()
    for state_name in _ORDERED_STATE_NAMES:
        state_suffix = f" {state_name.lower()}"
        if lowered_query.endswith(state_suffix):
            city_term = normalized[:-len(state_suffix)].strip(" ,")
            if city_term:
                return city_term, {state_name, US_STATE_TO_ABBR[state_name]}

    if " " in normalized:
        city_term, state_candidate = normalized.rsplit(" ", 1)
        state_terms = _recognized_state_terms(state_candidate)
        if city_term and state_terms:
            return city_term.strip(" ,"), state_terms

    return "", set()


def location_search_terms(raw_query):
    normalized_query = _normalize_spaces(raw_query)
    if not normalized_query:
        return {"normalized_query": "", "full_terms": set(), "state_terms": set(), "city_term": ""}

    full_terms = {normalized_query}
    state_terms = _recognized_state_terms(normalized_query)
    city_term = ""

    alternate_state = _alternate_state_phrase(normalized_query)
    if alternate_state:
        full_terms.add(alternate_state)

    parsed_city_term, parsed_state_terms = _extract_trailing_city_and_state(normalized_query)
    if parsed_city_term and parsed_state_terms:
        city_term = parsed_city_term
        state_terms = parsed_state_terms
        for state_term in parsed_state_terms:
            full_terms.add(f"{parsed_city_term} {state_term}")
            full_terms.add(f"{parsed_city_term}, {state_term}")
    elif state_terms:
        full_terms.update(state_terms)

    return {
        "normalized_query": normalized_query,
        "full_terms": full_terms,
        "state_terms": state_terms,
        "city_term": city_term,
    }
