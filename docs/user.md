# Meteo Populator

The Meteo Populator is a Python service that automatically associates Eclipse
Ditto Things with their closest weather stations from IPMA (Instituto Português
do Mar e da Atmosfera).

The service fetches active weather stations from the IPMA API, retrieves all
Things from Eclipse Ditto that have location, geometry, or coordinate data,
calculates the closest weather stations for each Thing based on geographic
proximity, and adds an attribute with references to its nearest stations, in
the form of Ditto Thing IDs. It uses OIDC for authentication with the
infrastructure.

## Prerequisites

Before using the Meteo Populator, ensure you have:

| Requirement | Version/Details |
| ----------- | --------------- |
| Python      | 3.12 or higher |
| Eclipse Ditto | Instance with a configured OIDC integration |
| Python virtual environment | A configured virtual environment, either using `uv` or any other PEP-518 compliant system |
| IPMA Open API access | Have internet connection to `api.ipma.pt` |

## Configuration

The Meteo Populator is configurable through a `config.toml` file, which contains the
needed information for the program to load the expected modules.

The structure of this file is as follows:

| Setting | Type | Default |
| ------- | ---- | ------- |
| `populator` | Object | `{ dry_run = false }` |
| `logging` | Object | `{ level = "INFO" }` |
| `station` | Object | `{ namespace = "internal", subject = "meteo" }` |
| `filter` | Object | See below |
| `oidc` | Object | `{ scope = "openid" }` |

### Populator Object

The populator object contains a single field:

| Setting | Type | Default | Description |
| ------- | ---- | ------- | ----------- |
| `dry_run` | Boolean | `false` | When `true`, the Meteo Populator will NOT update any Things in Eclipse Ditto, but will instead log the operation it would normally execute, namely what Thing would be updated and what attribute would be added. |

### Logging Object

The logging object contains a single field:

| Setting | Type | Default | Description |
| ------- | ---- | ------- | ----------- |
| `level` | String | `"INFO"` | The logging level of the application. The application will only show logs whose severity is of that level or above. |

### Station Object

The station object holds information about the Things representing the
meteorologic stations:

| Setting | Type | Default | Description |
| ------- | ---- | ------- | ----------- |
| `namespace` | String | `"internal"` | Namespace used in the ThingId of meteorologic station Things. |
| `subject` | String | `"meteo"` | Subject used in the ThingId of meteorologic station Things. |

The ThingIds follow the `namespace:subject:id` pattern, so station ThingIds
will be formatted as `namespace:subject:<station_id>`, where `station_id` is a
number given by IPMA's API.

### Filter Object

The filter object holds the filters used against Eclipse Ditto's Thing Search
API for retrieving the Things that need to be updated with the information of
the closest meteorologic stations:

| Setting | Type | Default | Description |
| ------- | ---- | ------- | ----------- |
| `filter` | String | `'and(or(exists(attributes/location),exists(attributes/geometry),exists(attributes/coordinates)),not(like(thingId,"*meteo*")))'` | A [Resource Query Language](https://github.com/persvr/rql) expression used on Eclipse Ditto's Thing Search API. The default expression retrieves all Things that contain the attributes `location`, `geometry` or `coordinates` and whose ThingId does not contain the expression `meteo`, to avoid adding the attribute of closest meteorologic stations to a Thing already representing a meteorologic station. |
| `fields` | String | `"thingId,attributes(location,geometry,coordinates)"` | The fields to retrieve from Ditto. Only the ThingId and the geographic location attribute are required, but the field is left configurable for future-proofing. |

### OIDC Object

The OIDC object configures authentication with the infrastructure's OIDC
provider:

| Setting | Type | Default | Description |
| ------- | ---- | ------- | ----------- |
| `base_url` | String | `""` | The base URL of the infrastructure. |
| `realm` | String | `""` | The realm for OIDC authentication. |
| `username` | String | `""` | The username for authentication. |
| `password` | String | `""` | The password for authentication. |
| `client_id` | String | `""` | The client ID identifying the service that is authenticating. |
| `scope` | String | `"openid"` | The scope of the authentication process. |

## A note on geotiles

As per the system's existing standard, this Meteo Populator adds a `expiry_ts`
and a `geotile` to all the Things it creates, where the first is a hint to the
garbage collector of whether a Thing is or not to be deleted, while the second
is an attribute that allows for the quick geographical search of Things within
a given area (a geotile). The implementation of these geotiles can be seen in
[docs/geotile.md](geotile.md)

# Deployment guide

The Meteo Populator is a Python application. However, it can be deployed in 3
different ways:

- Direct instantiation of the application
- Utilization of the provided Docker container
- Utilization of a Helm chart (for deployment in Kubernetes)

However, it is important to note that the provided application will perform a
single execution, given that it is intended to work as a periodic process,
meaning that it is instantiated periodically. As such, the provided Helm chart
is the recommended method for deployment, as it will automatically be
configured as a Kubernetes CronJob. In the case of the other deployment
methods, this behavior must be manually configured using other tools (such as
native Linux cronjobs).

## Direct instantiation

The Python application was developed in a [uv](https://docs.astral.sh/uv)
managed environment. However, it is PEP-518 compliant, meaning that the `uv`
tool is not required to run the application, as the dependencies can be managed
and installed by using `pip` in a configured virtual environment, or `venv`.

Using direct instantiation is as simple as running the [main.py](../main.py)
file in the managed environment (by either using `uv run main.py` if using `uv`
or by running `python main.py` in the `venv` if using any other PEP-518
compliant tool).

In this case, the `config.toml` configuration file must be placed in the root
of the project, which will be the directory where the `main.py` file is
located. The Meteo Populator will automatically load that file and apply the
configurations within it. Additionally, given that this project utilizes
`pydantic-settings`, these can also be set using environment variables. These
are named just like the fields, using a double underscore (`__`) for nested
objects. For example, the `oidc` object's `base_url` field is defined as
`OIDC__BASE_URL`. For defining arrays and more complex types, a JSON encoded
string can be used.

## Docker file

The usage of the Docker file is simpler than the direct instantiation, as the
image only needs to be built (or use the pre-built image in
`atnog-harbor.av.it.pt/dt4mob/meteo-populator`), mounting the `config.toml`
file in the directory `/app/config.toml`.

This can be done with the command `docker run -v config.toml:/app/config.toml
atnog-harbor.av.it.pt/dt4mob/meteo-populator`. It is once again reminded that
this will perform a single execution of the Meteo Populator, and will only
update the Things once. The periodic execution behavior is left for
implementation by the administrator.

Additionally, like with the direct instantiation, the configuration can be made
with environment variables.

## Helm Chart

The Helm chart is available at the [dt4mob-platform GitHub
repository](https://github.com/ATNoG/dt4mob-platform) and can be installed
using the Helm installer (`helm install meteo-populator <path_to_chart> -f
<path_to_values.yml>`). The configuration in this case is done via the
`values.yml` file, but follows the same structure of the `config.toml`
configuration file.
