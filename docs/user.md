# Configuration

The Meteo Populator is configurable through a `config.toml` file, which contains the
needed information for the program to load the expected modules.

The structure of this file is as follows:

- populator (Object) - Optional
- logging (Object) - Optional
- station (Object)
- filter (Object) - Optional
- oidc (Object)

## Populator Object

The populator object contains only a single field, `dry_run`, and
defaults to `False`. When set to `True`, the Meteo Populator will NOT update any
Things in Eclipse Ditto, but will instead just log the operation it would
normally execute, namely what Thing would be updated, and what attribute would
be added.

## Logging Object

The logging object also contains a single field, `level`, and defaults to
`"INFO"`. This field defined the logging level of the application, meaning that
the application will only show logs whose severity is of that level or above.
By default, it will only show logs whose severity level is `INFO` or higher,
meaning that debug logs are not shown.

## Station Object

The station object is responsible for holding information about the Things
representing the meteorologic stations, namely their `namespace` and `subject`,
which are the fields of the object.

The namespace defaults to `internal` and the subject to `meteo`, as that is the
structure of the ThingId used currently in the system, but may be altered
according to the user's needs.

## Filter Object

This object is responsible for holding the filters that will be used against
Eclipse Ditto for getting the Things that need to be updated with the
information of the closest meteorologic stations. It is comprised of the following fields:

- `filter`: The field to utilize on Eclipse Ditto's Thing Search API, expressed
  as a [Resource Query Language](https://github.com/persvr/rql) expression. It defaults to the following expression:
  `'and(or(exists(attributes/location),exists(attributes/geometry),exists(attributes/coordinates)),not(like(thingId,"*meteo*")))'`
  Which will retrieve all of the Things that contain the attributes `location`,
  `geometry` or `coordinates` and whose ThingId does not contain the expression
  `meteo`. This is done to avoid adding the attribute of closest meteorologic stations to a Thing already representing a meteorologic station.

- `fields`: The fields to be retrieved from Ditto. The only fields required to
  be retrieved are the ThingId and the geographic location attribute, where the
  first will be used for creating the modification command, and the latter will
  be used for acquiring the closest meteorologic stations. No other fields are
  required, but it was still left as configurable for future-proofing reasons.
  The default (and recommended) value is
  `"thingId,attributes(location,geometry,coordinates)"`.


## OIDC Object

The OIDC object is responsible for configuring all the information needed to
perform authentication with the infrastructure's OIDC. It contains the
following fields:


-`base_url`: The base url for the infrastructure.
-`realm`: The realm of OIDC authentication
-`username`: The username that will be used for authentication
-`password`: The password that will be used for authentication
-`client_id`: The provided `client_id` for identifying the service that is
authenticating
-`scope`: The scope of the auth process. Defaults to `"oidc"`
