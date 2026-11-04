# Meteo Populator

O Meteo Populator é um serviço Python que associa automaticamente Things do
Eclipse Ditto às estações meteorológicas mais próximas da IPMA (Instituto
Português do Mar e da Atmosfera).

O serviço obtém as estações meteorológicas ativas a partir da API da IPMA,
recupera todos os Things do Eclipse Ditto que possuem dados de localização,
geometria ou coordenadas, calcula as estações meteorológicas mais próximas para
cada Thing com base na proximidade geográfica e adiciona um atributo com
referências para as suas estações mais próximas, na forma de Thing IDs do Ditto.
Utiliza OIDC para autenticação com a infraestrutura.

## Pré-requisitos

Antes de utilizar o Meteo Populator, certifique-se de que tem:

| Requisito | Versão/Detalhes |
| ----------- | --------------- |
| Python      | 3.12 ou superior |
| Eclipse Ditto | Instância com uma integração OIDC configurada |
| Ambiente virtual Python | Um ambiente virtual configurado, utilizando `uv` ou qualquer outro sistema compatível com PEP-518 |
| Acesso à API Aberta da IPMA | Ter ligação à internet a `api.ipma.pt` |

## Configuração

O Meteo Populator é configurável através de um ficheiro `config.toml`, que contém
a informação necessária para o programa carregar os módulos esperados.

A estrutura deste ficheiro é a seguinte:

| Definição | Tipo | Predefinição |
| ------- | ---- | ------- |
| `populator` | Objeto | `{ dry_run = false }` |
| `logging` | Objeto | `{ level = "INFO" }` |
| `station` | Objeto | `{ namespace = "internal", subject = "meteo" }` |
| `filter` | Objeto | Ver abaixo |
| `oidc` | Objeto | `{ scope = "openid" }` |

### Objeto Populator

O objeto populator contém um único campo:

| Definição | Tipo | Predefinição | Descrição |
| ------- | ---- | ------- | ----------- |
| `dry_run` | Booleano | `false` | Quando `true`, o Meteo Populator NÃO irá atualizar quaisquer Things no Eclipse Ditto, mas em vez disso registará a operação que normalmente executaria, nomeadamente que Thing seria atualizado e que atributo seria adicionado. |

### Objeto Logging

O objeto logging contém um único campo:

| Definição | Tipo | Predefinição | Descrição |
| ------- | ---- | ------- | ----------- |
| `level` | String | `"INFO"` | O nível de registo (logging) da aplicação. A aplicação apenas mostrará registos cuja severidade seja igual ou superior a esse nível. |

### Objeto Station

O objeto station contém informação sobre os Things que representam as estações
meteorológicas:

| Definição | Tipo | Predefinição | Descrição |
| ------- | ---- | ------- | ----------- |
| `namespace` | String | `"internal"` | Namespace utilizado no ThingId dos Things das estações meteorológicas. |
| `subject` | String | `"meteo"` | Subject utilizado no ThingId dos Things das estações meteorológicas. |

Os ThingIds seguem o padrão `namespace:subject:id`, pelo que os ThingIds das
estações serão formatados como `namespace:subject:<station_id>`, onde
`station_id` é um número fornecido pela API da IPMA.

### Objeto Filter

O objeto filter contém os filtros utilizados na Thing Search API do Eclipse Ditto
para recuperar os Things que precisam de ser atualizados com a informação das
estações meteorológicas mais próximas:

| Definição | Tipo | Predefinição | Descrição |
| ------- | ---- | ------- | ----------- |
| `filter` | String | `'and(or(exists(attributes/location),exists(attributes/geometry),exists(attributes/coordinates)),not(like(thingId,"*meteo*")))'` | Uma expressão [Resource Query Language](https://github.com/persvr/rql) utilizada na Thing Search API do Eclipse Ditto. A expressão predefinida recupera todos os Things que contêm os atributos `location`, `geometry` ou `coordinates` e cujo ThingId não contém a expressão `meteo`, para evitar adicionar o atributo das estações meteorológicas mais próximas a um Thing que já representa uma estação meteorológica. |
| `fields` | String | `"thingId,attributes(location,geometry,coordinates)"` | Os campos a recuperar do Ditto. Apenas o ThingId e o atributo de localização geográfica são necessários, mas o campo é deixado configurável para preparação para o futuro. |

### Objeto OIDC

O objeto OIDC configura a autenticação com o fornecedor OIDC da infraestrutura:

| Definição | Tipo | Predefinição | Descrição |
| ------- | ---- | ------- | ----------- |
| `base_url` | String | `""` | O URL base da infraestrutura. |
| `realm` | String | `""` | O realm para autenticação OIDC. |
| `username` | String | `""` | O nome de utilizador para autenticação. |
| `password` | String | `""` | A palavra-passe para autenticação. |
| `client_id` | String | `""` | O ID do cliente que identifica o serviço que está a autenticar-se. |
| `scope` | String | `"openid"` | O âmbito do processo de autenticação. |

## Nota sobre geotiles

De acordo com o padrão existente do sistema, este Meteo Populator adiciona um
`expiry_ts` e um `geotile` a todos os Things que cria, onde o primeiro é uma
indicação para o garbage collector sobre se um Thing deve ou não ser eliminado,
enquanto o segundo é um atributo que permite a pesquisa geográfica rápida de
Things dentro de uma determinada área (um geotile). A implementação destes
geotiles pode ser consultada em [docs/geotile.md](geotile.md)

# Guia de implementação

O Meteo Populator é uma aplicação Python. No entanto, pode ser implementada de 3
formas diferentes:

- Instanciação direta da aplicação
- Utilização do contentor Docker fornecido
- Utilização de um Helm chart (para implementação em Kubernetes)

No entanto, é importante notar que a aplicação fornecida executa uma única vez,
uma vez que se destina a funcionar como um processo periódico, ou seja, é
instanciada periodicamente. Como tal, o Helm chart fornecido é o método
recomendado para implementação, pois será automaticamente configurado como um
Kubernetes CronJob. No caso dos outros métodos de implementação, este
comportamento deve ser configurado manualmente usando outras ferramentas (como
cronjobs nativos do Linux).

## Instanciação direta

A aplicação Python foi desenvolvida num ambiente gerido por
[uv](https://docs.astral.sh/uv). No entanto, é compatível com PEP-518, o que
significa que a ferramenta `uv` não é necessária para executar a aplicação, uma
vez que as dependências podem ser geridas e instaladas usando `pip` num ambiente
virtual configurado, ou `venv`.

Utilizar a instanciação direta é tão simples como executar o ficheiro
[main.py](../main.py) no ambiente gerido (usando `uv run main.py` se utilizar
`uv` ou executando `python main.py` no `venv` se utilizar qualquer outra
ferramenta compatível com PEP-518).

Neste caso, o ficheiro de configuração `config.toml` deve ser colocado na raiz
do projeto, que será o diretório onde o ficheiro `main.py` se encontra. O Meteo
Populator carregará automaticamente esse ficheiro e aplicará as configurações
nele contidas. Adicionalmente, dado que este projeto utiliza
`pydantic-settings`, estas também podem ser definidas usando variáveis de
ambiente. Estas são nomeadas exatamente como os campos, utilizando um duplo
underscore (`__`) para objetos aninhados. Por exemplo, o campo `base_url` do
objeto `oidc` é definido como `OIDC__BASE_URL`. Para definir arrays e tipos mais
complexos, pode ser usada uma string codificada em JSON.

## Ficheiro Docker

A utilização do ficheiro Docker é mais simples do que a instanciação direta,
pois a imagem apenas precisa de ser construída (ou usar a imagem pré-construída
em `atnog-harbor.av.it.pt/dt4mob/meteo-populator`), montando o ficheiro
`config.toml` no diretório `/app/config.toml`.

Isto pode ser feito com o comando `docker run -v config.toml:/app/config.toml
atnog-harbor.av.it.pt/dt4mob/meteo-populator`. Recorda-se novamente que isto
executará uma única vez o Meteo Populator, e apenas atualizará os Things uma
vez. O comportamento de execução periódica fica ao encargo do administrador.

Adicionalmente, tal como na instanciação direta, a configuração pode ser feita
com variáveis de ambiente.

## Helm Chart

O Helm chart está disponível no [repositório GitHub
dt4mob-platform](https://github.com/ATNoG/dt4mob-platform) e pode ser instalado
usando o instalador Helm (`helm install meteo-populator <path_to_chart> -f
<path_to_values.yml>`). A configuração neste caso é feita através do ficheiro
`values.yml`, mas segue a mesma estrutura do ficheiro de configuração
`config.toml`.
