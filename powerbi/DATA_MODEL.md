# Modelo de dados — Power BI

## Tabelas importadas (Import mode, atualização diária via Airflow)

| Tabela / View | Origem | Chave | Relacionamento |
|---|---|---|---|
| `dim_estado` | `dim_estado` | `id_estado` PK | — |
| `fato_populacao` | `fato_populacao` | `id_estado` FK | `dim_estado[ id_estado ] 1—* fato_populacao[id_estado]` |
| `fato_pib` | `fato_pib` | `id_estado` FK | `dim_estado 1—* fato_pib` |
| `fato_ideb` | `fato_ideb` | `id_estado` FK | `dim_estado 1—* fato_ideb` |
| `vw_ideb_medio_regiao_ano` | view | — | tabela calculada (sem relacionamento direto) |
| `vw_painel_uf_ano` | view | — | tabela calculada |

Todas as relações são **unidirecionais** (`dim_estado` filtra os fatos).

## Colunas calculadas sugeridas (Power Query)

- `dim_estado[UF_Regiao] = [sigla] & " — " & [nome_regiao]`
- `fato_ideb[IDEB_Nulo] = IF(ISBLANK([ideb]), 1, 0)` — para contar municípios sem IDEB

## Hierarquias

- **Geográfica:** `nome_regiao > uf > nome_municipio`
- **Temporal:** `ano` (inteiro, 2005–2025) — usar como eixo contínuo nos gráficos de linha