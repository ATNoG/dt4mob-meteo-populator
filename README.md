# Meteo Populator

The Meteo Populator is a Python service that automatically associates Eclipse
Ditto things with their closest weather stations from IPMA (Instituto Português
do Mar e da Atmosfera).

The service fetches active weather stations from the IPMA API, retrieves all
"Things" from Eclipse Ditto that have location/geometry data, calculates the
closest weather stations for each thing based on geographic proximity, and adds
an attribute with references to its nearest stations, in the form of Ditto
Thing IDs. It is designed to run as a Kubernetes CronJob.

## Configuration

This section can be found in the [user guide](./docs/user.md)


## Deployment

This section can be found in the [admin guide](./docs/admin.md)
