# Execução do programa e lógica principal

O programa principal, conforme atualmente implementado, comportar-se-á da
seguinte forma:

![Meteo Populator Control Flow Graph](/Users/iavcoelho/IT/DT4MOB/meteo_populator/docs/figs/ctrl_flow_diagram.png)

O programa começa por realizar a autenticação OIDC utilizando um password grant
para obter um token de acesso e um refresh token da instância Keycloak da
infraestrutura. É então criada uma `aiohttp.ClientSession` partilhada, apontada
para o endpoint da API v2 do Ditto com o token de acesso definido como um
cabeçalho `Authorization` do tipo bearer.

O primeiro passo de obtenção de dados recupera todas as estações meteorológicas
ativas da API aberta da IPMA (`api.ipma.pt`). As estações cuja última medição
seja anterior a 2 horas são descartadas como desatualizadas.

O segundo passo utiliza paginação baseada em cursor para iterar por todos os
Things do Eclipse Ditto que correspondem a um filtro RQL configurável. O filtro
predefinido recupera todos os Things que contêm um atributo `location`,
`geometry` ou `coordinates` e cujo ThingId não contém a palavra `meteo`, para
que os Things das estações meteorológicas não sejam modificados.

Para cada Thing devolvido, o programa extrai um único ponto geográfico
representativo do atributo de localização do Thing — que pode ser uma
coordenada única, uma lista de coordenadas (cujo centroide é calculado) ou estar
ausente (o que faz com que o Thing seja ignorado). De seguida, procura nas
estações IPMA ativas as 3 estações mais próximas num raio de 100 km desse ponto,
utilizando a fórmula de Haversine para distância de grande círculo. Se forem
encontradas estações, é feito um pedido PUT ao Ditto para definir o atributo
`closest_meteo_stations` no Thing com os identificadores das estações formatados
como `namespace:subject:<station_id>`.

O token é verificado quanto à expiração antes de cada Thing ser processado; se
expirado, é realizado um refresh token grant de forma transparente.

O diagrama de sequência do fluxo de execução principal é o seguinte:

![Meteo Populator sequence diagram](/Users/iavcoelho/IT/DT4MOB/meteo_populator/docs/figs/seq_diagram.png)

O programa executa uma única vez e termina. Foi concebido para ser executado
periodicamente como um Kubernetes CronJob ou uma tarefa cron do sistema.

# Estrutura do Código

O programa está estruturado logicamente da seguinte forma:

![Meteo Populator dependency graph and code structure](/Users/iavcoelho/IT/DT4MOB/meteo_populator/docs/figs/dependency_diagram.png)

> **_NOTA_**: Para facilitar a compreensão deste diagrama: É utilizada uma
> notação `ball and socket`, onde uma bola representa o fornecimento de uma
> interface, e uma tomada representa o consumo dessa interface. É utilizada para
> mostrar as dependências entre componentes internos do sistema (e interação com
> sistemas externos). A coluna `App Core` consiste nos ficheiros `main.py` e
> `settings.py`. A coluna `Interfaces` consiste nos ficheiros contidos no
> diretório `interfaces/` e a coluna `Data` consiste nos ficheiros contidos no
> diretório `models/`. A coluna `Utils` consiste no diretório `utils/`.

O ponto de entrada do programa é o `main.py`, que importa a instância partilhada
`settings` do `settings.py` e orquestra todo o ciclo de vida. O diretório
`interfaces/` contém módulos que lidam cada um com a comunicação com um serviço
externo específico:

- `interfaces/oidc.py` — Autenticação com Keycloak
- `interfaces/ipma.py` — Obtenção de estações meteorológicas da IPMA
- `interfaces/ditto.py` — Pesquisa e modificação de Things no Eclipse Ditto

O diretório `models/` contém modelos de dados Pydantic utilizados em toda a base
de código:

- `models/geo.py` — Representação de ponto geográfico
- `models/station.py` — Dados de estação meteorológica e cálculos de distância
- `models/thing.py` — Thing do Ditto e tipos relacionados
- `models/request.py` — Resposta de pesquisa do Ditto com cursor de paginação

O diretório `utils/` contém funções utilitárias puras para cálculos geográficos
utilizados pelas interfaces:

- `utils/geo.py` — Extração de ponto representativo e pesquisa de estação mais
  próxima

# Modelos de Dados

Os modelos de dados neste projeto são todos criados usando o `BaseModel` do
`Pydantic`, com Enums a serem criados com a classe `Enum` da stdlib de Python.

Para saber mais sobre como criar um modelo `Pydantic`, é recomendada a consulta
da sua [documentação
oficial](https://pydantic.dev/docs/validation/2.11/get-started/). No entanto, os
conceitos importantes são que uma nova classe tem de ser criada que estende a
classe `BaseModel`, e os campos são definidos dentro desta nova classe,
juntamente com os seus tipos. O `Pydantic` é então responsável pela
criados com o decorador de função `@model_validator`.

Por uma questão de organização, espera-se que estes modelos sejam criados dentro
de um novo ficheiro no diretório `models/`, com um nome que permita o fácil
reconhecimento da finalidade dos modelos.

Os seguintes modelos estão definidos neste projeto:

- `models/geo.py` — `Point`: uma coordenada geográfica simples com os campos
  `latitude` e `longitude`. Este modelo é utilizado em toda a base de código
  sempre que é necessário representar uma localização geográfica.

- `models/station.py` — `Station`: representa uma estação meteorológica da IPMA
  com os campos `id`, `name`, `latitude` e `longitude`. Contém um método
  `distance_to(point)` que devolve a distância de grande círculo em quilómetros
  para um dado `Point`, calculada pela função interna `_haversine`. A fórmula de
  Haversine aqui implementada é:

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

- `models/thing.py` — `Thing`: representa um Thing do Ditto com os campos
  `thingId` e `attributes`. O modelo `Attributes` utiliza `AliasChoices` para
  aceitar os campos `location`, `geometry` ou `coordinates` da resposta JSON da
  API, mapeando-os todos para o mesmo atributo `location`. O campo `location`
  pode ser um único `Point`, um `list[Point]` (para geometrias de polígono) ou
  `None`. Este ficheiro também define `PopulateResult`, um enum de string com os
  valores `SUCCESS`, `NO_STATIONS`, `NO_LOCATION` e `ERR`, utilizado para o
  dispatch `match`/`case` no ciclo principal.

- `models/request.py` — `SearchResponse`: modela a resposta paginada do endpoint
  `search/things` do Ditto, contendo `items: list[Thing]` e uma string opcional
  `cursor` para a página seguinte.

- `interfaces/oidc.py` — `Tokens`: um modelo com os campos `access` (a string do
  token de acesso), `refresh` (a string do refresh token) e `expiry` (um
  `datetime` que indica quando o token de acesso expira). Este modelo está
  definido dentro do módulo de interface em vez do diretório `models/` porque
  está fortemente acoplado à lógica de autenticação.

# Configuração

A configuração é tratada através do `settings.py`, que utiliza
`pydantic-settings` para carregar as definições de um ficheiro `config.toml`. A
classe `Settings` é uma subclasse de `BaseSettings` com as seguintes secções
aninhadas:

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(toml_file="config.toml")

    populator: PopulatorSettings = PopulatorSettings()
    logging: LoggingSettings = LoggingSettings()
    oidc: OidcSettings = OidcSettings()
    station: StationSettings = StationSettings()
    filter: DittoFilter = DittoFilter()
```

Um singleton ao nível do módulo é criado no momento da importação:

```python
settings = Settings()
```

Este singleton é importado em todo o código como `from settings import
settings`. Todos os componentes acedem à configuração através desta única
instância, evitando a necessidade de passar objetos de configuração através de
parâmetros de funções.

As definições também podem ser fornecidas através de variáveis de ambiente
utilizando um separador de duplo underscore (`__`) para campos aninhados. Por
exemplo, o URL base do OIDC pode ser definido com `OIDC__BASE_URL`.

O método de classe `settings_customise_sources` é sobreposto para utilizar
exclusivamente uma fonte de ficheiro TOML, ignorando variáveis de ambiente,
ficheiros `.env` e outras fontes predefinidas que o `pydantic-settings` fornece.

O ficheiro também configura o logger `loguru` com um formatador customizado 
que renderiza dicionários `extra` estruturados como texto magenta indentado
abaixo da mensagem de log, melhorando a legibilidade da saída de depuração.

# Interfaces

O conceito de `interface` neste programa não é o de uma interface padrão que
define as funções obrigatórias que precisam de ser implementadas. É apenas a
definição do contacto com o mundo exterior. Cada interface é um módulo Python
que contém funções assíncronas que utilizam `aiohttp` para comunicar com um
serviço externo específico. Como tal, a definição desta interface fica
completamente ao critério do programador. No entanto, algumas recomendações são
deixadas, nomeadamente a utilização do `ClientSession` do `aiohttp` para todos
os pedidos HTTP e garantir que as funções retornam modelos Pydantic tipados.

Adicionalmente, foi seguida a diretriz de que todas as funções utilitárias
definidas dentro do ficheiro devem ser prefixadas com um underscore (`_`).

## OIDC Interface

A interface OIDC, definida em `interfaces/oidc.py`, é responsável por interagir
com a instância Keycloak da infraestrutura para obter e renovar tokens OIDC.

Duas funções são fornecidas:

- `get_tokens()` — Utiliza o tipo password grant (`grant_type=password`) para
  autenticar com o nome de utilizador, palavra-passe, client ID, realm e scope
  configurados. Devolve um modelo `Tokens` contendo o token de acesso, o refresh
  token e um datetime de expiração calculado. Cada chamada cria o seu próprio
  `ClientSession` de curta duração. Devolve `None` em caso de erro HTTP.

- `refresh_token(refresh_token)` — Utiliza o refresh token grant para obter um
  novo token de acesso antes de o atual expirar. Segue o mesmo padrão que
  `get_tokens()` mas utiliza o refresh token fornecido em vez das credenciais.

Ambas as funções fazem POST para o endpoint
`{base_url}/auth/realms/{realm}/protocol/openid-connect/token` com dados de
formulário codificados no URL.

## IPMA Interface

A interface IPMA, definida em `interfaces/ipma.py`, é responsável por obter as
estações meteorológicas ativas da API pública da IPMA.

Fornece uma única função:

- `fetch_active_stations()` — Faz um pedido GET a
  `https://api.ipma.pt/open-data/observation/meteorology/stations/obs-surface.geojson`
  e interpreta o GeoJSON devolvido. As estações são filtradas para manter apenas
  aquelas cuja última medição foi feita há menos de 2 horas. Para cada estação
  ativa, é criado um objeto `Station` com o ID da estação (`idEstacao`), nome
  (`localEstacao`) e coordenadas geográficas (extraídas de
  `geometry.coordinates` na ordem `[lon, lat]`, convertidas para `lat, lon`).

A função cria o seu próprio `ClientSession` uma vez que a API da IPMA é pública
e não requer autenticação.

## Ditto Interface

A interface Ditto, definida em `interfaces/ditto.py`, é responsável por
pesquisar e modificar Things no Eclipse Ditto. Ao contrário das outras
interfaces, recebe um `ClientSession` pré-autenticado do `main.py` (que já tem o
cabeçalho do bearer token definido).

Três funções são fornecidas:

- `fetch_all_things(session)` — Realiza paginação baseada em cursor no endpoint
  `search/things` do Ditto. Cada pedido recupera 200 Things de cada vez,
  passando o cursor da resposta anterior como parâmetro opcional. O filtro e os
  campos são lidos do singleton partilhado `settings`. A paginação para quando o
  servidor devolve um cursor `null`.

- `patch_closest_stations(session, thing_id, stations)` — Envia um pedido PUT
  para `things/{thing_id}/attributes/closest_meteo_stations` com um corpo JSON
  contendo uma lista de ThingIds das estações formatados como
  `namespace:subject:<station_id>`. Em modo dry-run, o pedido é ignorado e
  apenas registado. A verificação SSL está desativada (`ssl=False`).

- `populate_closest_stations(session, thing, stations)` — Orquestra a lógica de
  população por Thing. Chama `representative_point()` de `utils/geo.py` para
  extrair um único ponto geográfico dos atributos do Thing, depois chama
  `closest_stations()` para encontrar as estações mais próximas. Se for
  bem-sucedido, delega para `patch_closest_stations()`. Devolve um valor do enum
  `PopulateResult` para o ciclo principal registar.

# Utilitários

O módulo utilitário, `utils/geo.py`, contém funções puras para cálculos
geográficos que são utilizadas pela interface Ditto. Estas funções não têm
efeitos secundários nem dependências de serviços externos.

Duas funções são fornecidas:

- `representative_point(location)` — Aceita um `Point`, um `list[Point]` ou
  `None`. Se for uma lista de pontos (por exemplo, vértices de um polígono), o
  centroide geométrico é calculado como a média das latitudes e a média das
  longitudes. Se for um único `Point`, é devolvido tal como está. Se for `None`,
  é devolvido `None`, indicando que o Thing não tem dados de localização
  utilizáveis.

- `closest_stations(point, stations, max_distance=100.0, n=3)` — Dado um `Point`
  e uma lista de objetos `Station`, ordena todas as estações pela sua distância
  de grande círculo ao ponto (usando `Station.distance_to()` que implementa a
  fórmula de Haversine). Devolve as `n` estações principais que estão dentro de
  `max_distance` quilómetros. A configuração predefinida devolve até 3 estações
  num raio de 100 km.
