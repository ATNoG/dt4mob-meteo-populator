# Program's execution and main logic

The main program, as implemented currently, will behave as follows:

![Meteo Populator Control Flow Graph](/Users/iavcoelho/IT/DT4MOB/meteo_populator/docs/figs/ctrl_flow_diagram.png)

The program starts by performing OIDC authentication using a password grant to
obtain an access token and a refresh token from the infrastructure's Keycloak
instance. A shared `aiohttp.ClientSession` is then created, pointed at Ditto's
API v2 endpoint with the access token set as a bearer `Authorization` header.

The first data-fetching step retrieves all active meteorologic stations from
IPMA's open API (`api.ipma.pt`). Stations whose last measurement is older than
2 hours are discarded as stale.

The second step uses cursor-based pagination to iterate through all Eclipse
Ditto Things that match a configurable RQL filter. The default filter retrieves
all Things that contain a `location`, `geometry`, or `coordinates` attribute
and whose ThingId does not contain the word `meteo`, so that meteorologic
station Things are not modified.

For each Thing returned, the program extracts a single representative
geographic point from the Thing's location attribute — which may be a single
coordinate, a list of coordinates (whose centroid is computed), or absent
(which causes the Thing to be skipped). It then searches the active IPMA
stations for the 3 closest stations within 100 km of that point, using the
Haversine formula for great-circle distance. If stations are found, a PUT
request is issued to Ditto to set the `closest_meteo_stations` attribute on the
Thing with the station identifiers formatted as
`namespace:subject:<station_id>`.

The token is checked for expiry before each Thing is processed; if expired, a
refresh token grant is performed transparently.

The sequence diagram of the main execution flow is as follows:

![Meteo Populator sequence diagram](/Users/iavcoelho/IT/DT4MOB/meteo_populator/docs/figs/seq_diagram.png)

The program performs a single execution and exits. It is intended to be run
periodically as a Kubernetes CronJob or a system cron task.

# Code Structure

The program is logically structured as follows:

![Meteo Populator dependency graph and code structure](/Users/iavcoelho/IT/DT4MOB/meteo_populator/docs/figs/dependency_diagram.png)

> **_NOTE_**: For ease of understanding this diagram: This uses a `ball and
> socket` notation, where a ball represents providing an interface, and a socket
> represents consuming said interface. It is used to show the dependencies
> between internal components of the system (and interaction with external
> systems). The `App Core` column consists of the `main.py` and `settings.py`
> files. The `Interfaces` column consists of the files contained within the
> `interfaces/` directory and the `Data` column consists of the files contained
> within the `models/` directory. The `Utils` column consists of the `utils/`
> directory.

The program entry point is `main.py`, which imports the shared `settings`
instance from `settings.py` and orchestrates the entire lifecycle. The
`interfaces/` directory contains modules that each handle communication with a
specific external service:

- `interfaces/oidc.py` — Authentication with Keycloak
- `interfaces/ipma.py` — Retrieval of meteorologic stations from IPMA
- `interfaces/ditto.py` — Search and modification of Things in Eclipse Ditto

The `models/` directory contains Pydantic data models used across the
codebase:

- `models/geo.py` — Geographic point representation
- `models/station.py` — Weather station data and distance calculations
- `models/thing.py` — Ditto Thing and related types
- `models/request.py` — Ditto search response with pagination cursor

The `utils/` directory contains pure utility functions for geographic
computations used by the interfaces:

- `utils/geo.py` — Representative point extraction and closest station search

# Data Models

The data models in this project are all created using `Pydantic`'s `BaseModel`,
with Enums being created with Python's stdlib `Enum` class.

To see more about how to create a `Pydantic` model, consultation of their
[official
documentation](https://pydantic.dev/docs/validation/2.11/get-started/) is recommended.
However, the important concepts are that a new class has to be created that
extends the `BaseModel` class, and fields are defined within this new class,
along with their types. `Pydantic` is then responsible for the serialization
and deserialization of the model. Custom validators can be created with the
`@model_validator` function decorator.

For a matter of organization, it is expected that these models are created
within a new file in the `models/` directory, with a name that allows for the
ease of recognition on what the purpose of the models is.

The following models are defined in this project:

- `models/geo.py` — `Point`: a simple geographic coordinate with `latitude`
  and `longitude` fields. This model is used throughout the codebase wherever a
  geographic location needs to be represented.

- `models/station.py` — `Station`: represents an IPMA meteorologic station with
  fields `id`, `name`, `latitude`, and `longitude`. It contains a
  `distance_to(point)` method that returns the great-circle distance in
  kilometers to a given `Point`, computed by the internal `_haversine`
  function. The Haversine formula implemented here is:

```python
def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
```

- `models/thing.py` — `Thing`: represents a Ditto Thing with `thingId` and
  `attributes` fields. The `Attributes` model uses `AliasChoices` to accept
  `location`, `geometry`, or `coordinates` fields from the JSON API response,
  mapping them all to the same `location` attribute. The `location` field can
  be a single `Point`, a `list[Point]` (for polygon geometries), or `None`.
  This file also defines `PopulateResult`, a string enum with values
  `SUCCESS`, `NO_STATIONS`, `NO_LOCATION`, and `ERR`, used for the
  `match`/`case` dispatch in the main loop.

- `models/request.py` — `SearchResponse`: models the paginated response from
  Ditto's `search/things` endpoint, containing `items: list[Thing]` and an
  optional `cursor` string for the next page.

- `interfaces/oidc.py` — `Tokens`: a model with fields `access` (the access
  token string), `refresh` (the refresh token string), and `expiry` (a
  `datetime` indicating when the access token expires). This model is defined
  inside the interface module rather than the `models/` directory because it is
  tightly coupled to the authentication logic.

# Configuration

Configuration is handled through `settings.py`, which uses
`pydantic-settings` to load settings from a `config.toml` file. The `Settings`
class is a `BaseSettings` subclass with the following nested sections:

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(toml_file="config.toml")

    populator: PopulatorSettings = PopulatorSettings()
    logging: LoggingSettings = LoggingSettings()
    oidc: OidcSettings = OidcSettings()
    station: StationSettings = StationSettings()
    filter: DittoFilter = DittoFilter()
```

A module-level singleton is created at import time:

```python
settings = Settings()
```

This singleton is imported throughout the codebase as `from settings import
settings`. All components access configuration through this single instance,
avoiding the need to pass configuration objects through function parameters.

The settings can also be provided via environment variables using a double
underscore (`__`) separator for nested fields. For example, the OIDC base URL
can be set with `OIDC__BASE_URL`.

The `settings_customise_sources` class method is overridden to exclusively use
a TOML file source, ignoring environment variables, `.env` files, and other
default sources that `pydantic-settings` provides.

The file also configures the `loguru` logger with a custom formatter that
renders structured `extra` dictionaries as indented magenta text below the log
message, improving readability of the debug output.

# Interfaces

The concept of a `interface` in this program is not one of a standard
interface that defines the mandatory functions that need to be implemented. It
is just the definition of the contact with the outside world. Each interface is
a Python module containing async functions that use `aiohttp` to communicate
with a specific external service. As such, the definition of this interface is
left completely to the programmer. However, some recommendations are left,
namely the usage of `aiohttp`'s `ClientSession` for all HTTP requests and
ensuring that functions return typed Pydantic models.

Additionally, the guideline that all utility functions defined within the file
should be prefixed with an underscore (`_`) was followed.

## OIDC Interface

The OIDC interface, defined in `interfaces/oidc.py`, is responsible for
interacting with the infrastructure's Keycloak instance to obtain and refresh
OIDC tokens.

Two functions are provided:

- `get_tokens()` — Uses the password grant type
  (`grant_type=password`) to authenticate with the configured username,
  password, client ID, realm, and scope. Returns a `Tokens` model containing
  the access token, refresh token, and a computed expiry datetime. Each call
  creates its own short-lived `ClientSession`. Returns `None` on HTTP error.

- `refresh_token(refresh_token)` — Uses the refresh token grant to obtain a new
  access token before the current one expires. Follows the same pattern as
  `get_tokens()` but uses the provided refresh token instead of credentials.

Both functions POST to the
`{base_url}/auth/realms/{realm}/protocol/openid-connect/token` endpoint with
URL-encoded form data.

## IPMA Interface

The IPMA interface, defined in `interfaces/ipma.py`, is responsible for
fetching active meteorologic stations from IPMA's public API.

It provides a single function:

- `fetch_active_stations()` — Makes a GET request to
  `https://api.ipma.pt/open-data/observation/meteorology/stations/obs-surface.geojson`
  and parses the returned GeoJSON. Stations are filtered to only keep those
  whose last measurement was taken less than 2 hours ago. For each active
  station, a `Station` object is created with the station's ID
  (`idEstacao`), name (`localEstacao`), and geographic coordinates (extracted
  from `geometry.coordinates` in `[lon, lat]` order, converted to `lat, lon`).

The function creates its own `ClientSession` as the IPMA API is public and
requires no authentication.

## Ditto Interface

The Ditto interface, defined in `interfaces/ditto.py`, is responsible for
searching and modifying Things in Eclipse Ditto. Unlike the other interfaces,
it receives a pre-authenticated `ClientSession` from `main.py` (which has the
bearer token header already set).

Three functions are provided:

- `fetch_all_things(session)` — Performs cursor-based pagination on Ditto's
  `search/things` endpoint. Each request retrieves 200 Things at a time,
  passing the cursor from the previous response as an option parameter. The
  filter and fields are read from the shared `settings` singleton. Pagination
  stops when the server returns a `null` cursor.

- `patch_closest_stations(session, thing_id, stations)` — Sends a PUT request
  to `things/{thing_id}/attributes/closest_meteo_stations` with a JSON body
  containing a list of station ThingIds formatted as
  `namespace:subject:<station_id>`. In dry-run mode, the request is skipped
  and only logged. SSL verification is disabled (`ssl=False`).

- `populate_closest_stations(session, thing, stations)` — Orchestrates the
  per-Thing population logic. It calls `representative_point()` from
  `utils/geo.py` to extract a single geographic point from the Thing's
  attributes, then calls `closest_stations()` to find the nearest stations. If
  successful, it delegates to `patch_closest_stations()`. Returns a
  `PopulateResult` enum value for the main loop to log.

# Utilities

The utility module, `utils/geo.py`, contains pure functions for geographic
computations that are used by the Ditto interface. These functions have no
side effects and no dependencies on external services.

Two functions are provided:

- `representative_point(location)` — Accepts a `Point`, a `list[Point]`, or
  `None`. If it is a list of points (e.g., polygon vertices), the geometric
  centroid is computed as the mean of the latitudes and mean of the
  longitudes. If it is a single `Point`, it is returned as-is. If `None`,
  `None` is returned, indicating that the Thing has no usable location data.

- `closest_stations(point, stations, max_distance=100.0, n=3)` — Given a
  `Point` and a list of `Station` objects, sorts all stations by their
  great-circle distance to the point (using `Station.distance_to()` which
  implements the Haversine formula). Returns the top `n` stations that are
  within `max_distance` kilometers. The default configuration returns up to
  3 stations within 100 km.
