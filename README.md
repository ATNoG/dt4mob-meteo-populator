# Meteo Populator

A Python service that automatically associates Eclipse Ditto things with their
closest weather stations from IPMA (Instituto Português do Mar e da Atmosfera).

The service fetches active weather stations from the IPMA API, retrieves all
"Things" from Eclipse Ditto that have location/geometry data, calculates the
closest weather stations for each thing based on geographic proximity, and adds
an attribute with references to its nearest stations, in the form of Ditto
Thing IDs. It is designed to run as a Kubernetes CronJob.

## Configuration

Configuration is stored in `config.toml`:

```toml
[ditto]
base_url = "https://dt4mob-staging.av.it.pt/api/2"
username = "ditto"
password = "..."

[populator]
dry_run = false          # set to true to skip actual patches

[logging]
level = "DEBUG"
```

## Usage

```bash
# Install dependencies (using uv)
uv sync

# Run the service
uv run main.py
```

## Dry Run Mode

Set `dry_run = true` in `config.toml` to simulate the population cycle without making any changes to Ditto.

## Development

```bash
# Install pre-commit hooks
pre-commit install

# Run linting
ruff check .
ruff format .
```
