# Deployment guide

The Meteo Populator is a Python application. However, it can be deployed in 3 different ways:
- Direct instantiation of the application
- Utilization of the provided Docker container
- Utilization of a Helm chart (for deployment in Kubernetes)

However, it is important to note that the provided application will perform a
single execution, given that it is intended to work as a periodic process,
meaning that it is instantiated periodically. As such, the provided Helm chart
is the recommended method for deployment, as it will automatically be
configured as a Kubernetes CronJob. In the case of the other deployment
methods, this behaviour must be manually configured using other tools (such as
native linux cronjobs)

## Direct instantiation

The python application was developed in a [uv](https://docs.astral.sh/uv)
managed environment. However, it is PEP-518 compliant, meaning that the `uv`
tool is not required to run the application, as the dependencies can be managed
and installed by using `pip` in a configured virtual environment, or `venv`.

Using direct instantiation is as simple as running the [main.py](../main.py)
file in the managed environment (by either using `uv run main.py` if using `uv`
or by running `python main.py` in the `venv` if using any other PEP-518
compliant tool).

In this case, the `config.toml` configuration file must be placed in the root
of the project, which will be the directory where the `main.py` file is
located. The Data Bridge will automatically load that file and apply the
configurations within it. For details on how to configure the Data Bridge,
refer to the [user guide](./user.md). Additionally, given that this project
utilizes `pydantic-settings`, these can also be set using environment
variables. For details on how to do this, please refer  to the
`pydantic-settings` [official
documentation](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/)

## Docker file 

The usage of the docker file is simpler than the direct instantiation, as the
image only needs to be built (or use the pre-built image in
`atnog-harbor.av.it.pt/dt4mob/meteo-populator`), mounting the `config.toml` file in
the directory `/app/config.toml`

This can be done with the command `docker run -v config.toml:/app/config.toml
atnog-harbor.av.it.pt/dt4mob/meteo-populator`. It is once again reminded that this
will perform a single execution of the Meteo Populator, and will only update the
things once. The periodic execution behaviour is left for implementation by the
administrator.

Additionally, like with the direct instantiation, the configuration can be made
with environment variables. For details on how to do this, please refer  to the
`pydantic-settings` [official
documentation](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/)

## Helm Chart

The helm chart is available at the [dt4mob-platform GitHub
repository](https://github.com/ATNoG/dt4mob-platform) and can be installed
using the Helm installer (`helm install meteo-populator <path_to_chart> -f <path_to_values.yml>`)
The configuration in this case is done via the `values.yml` file, but follows
the same structure of the `config.toml` configuration file.
