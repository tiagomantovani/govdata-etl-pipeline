# Dicionário de dados

## dim_estado (27 linhas)

| Coluna | Tipo | Descrição |
|---|---|---|
| `id_estado` | INTEGER PK | Código IBGE da UF (11–53) |
| `sigla` | VARCHAR(2) | Sigla (SP, RJ…) |
| `nome` | VARCHAR(100) | Nome (São Paulo…) |
| `sigla_regiao` | VARCHAR(2) | SE, S, NE, N, CO |
| `nome_regiao` | VARCHAR(50) | Sudeste, Sul… |

Origem: `api/v1/localidades/estados`.

## fato_populacao (27 linhas)

| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | SERIAL PK | Surrogate |
| `id_estado` | INTEGER FK | → dim_estado |
| `ano` | INTEGER | Ex.: 2022 (SIDRA 4714) |
| `populacao` | NUMERIC | Habitantes (V=93) |

Regra: `V rlike ^\d+$`, senão `NULL`.

## fato_pib (54 linhas)

| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | SERIAL PK |  |
| `id_estado` | INTEGER FK |  |
| `ano` | INTEGER | `last` da SIDRA 5938 |
| `variavel` | VARCHAR(200) | Ex.: Produto Interno Bruto a preços correntes |
| `valor` | NUMERIC | Em **Mil Reais** (`V`), `NULL` se ausente |
| `unidade` | VARCHAR(50) | Mil Reais |

## fato_ideb (159.687 linhas)

| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | SERIAL PK |  |
| `codigo_municipio` | VARCHAR(7) | IBGE 7 dígitos |
| `nome_municipio` | VARCHAR(120) |  |
| `uf` | VARCHAR(2) |  |
| `rede` | VARCHAR(20) | Pública, Estadual, Municipal, Federal |
| `ano` | INTEGER | 2005–2025 (melt das colunas `VL_OBSERVADO_*`) |
| `ideb` | NUMERIC(4,1) | 0.0–10.0, `NULL` quando não divulgado (`"-"` no xlsx) |
| `id_estado` | INTEGER FK | 2 primeiros dígitos do código |

15% dos registros têm `ideb IS NULL` (municípios sem avaliação).

## Views (`sql/views.sql`)

- `vw_ideb_medio_regiao_ano` — média por região/ano (rede pública)
- `vw_ideb_ranking_municipios` — ranking com `RANK()`
- `vw_pib_por_uf_ano`, `vw_populacao_por_uf_ano`
- `vw_painel_uf_ano` — junção PIB + população + IDEB + `pib_per_capita`
