# Relatório Power BI — GovData

## Conexão

1. Power BI Desktop → Obter Dados → PostgreSQL.
2. Servidor: `localhost:5432`, Banco: `govdata`, Credenciais do `.env` (`postgres` / `suasenha`).
3. Importe as 4 tabelas + as 5 views de `sql/views.sql` (Import, atualização via Airflow).

## Página 1 — Visão Geral

| Visual | Tabela/Campos | Medida |
|---|---|---|
| **KPI** População total | `fato_populacao` | `Populacao Total` |
| **KPI** PIB total | `fato_pib` | `PIB Total (R$ mil)` |
| **KPI** IDEB médio nacional | `fato_ideb` | `IDEB Medio Nacional` |
| **Mapa coroplético** UF por IDEB médio 2025 | `dim_estado` + `fato_ideb` | `IDEB Medio` (filtro ano=2025, rede=Pública) |
| **Gráfico de linhas** IDEB médio por região (2005–2025) | `vw_ideb_medio_regiao_ano` | `ideb_medio` por `ano`, legenda `nome_regiao` |
| **Barras** PIB por UF (ano selecionado via segmentação) | `vw_pib_por_uf_ano` | `valor` filtrado `variavel = Produto Interno Bruto%` |

Filtros da página: segmentação `ano` (2005–2025) e `rede` (Pública/Estadual/Municipal).

## Página 2 — IDEB Detalhado

- **Tabela** `vw_ideb_ranking_municipios` (top 20 por IDEB) com classificação `posicao`.
- **Dispersão** IDEB vs PIB per capita por município (usar `vw_painel_uf_ano` agregado por UF).
- **Cartão** `% Sem IDEB` para evidenciar municípios sem avaliação.

## Página 3 — Painel UF/Ano

- **Matriz** `vw_painel_uf_ano`: linhas `nome_regiao > uf`, colunas `ano`, valores `populacao`, `pib_total`, `ideb_medio`.
- **Filtros cruzados** com a página 1.

## Interações

- Clique no mapa filtra as demais páginas por UF/região.
- Segmentação de ano sincronizada entre páginas 1 e 3.

## Como publicar (opcional)

- Arquivo `.pbix` fica em `powerbi/` (ignorado pelo git por ser binário; versione via `powerbi/*.pbir` se usar o formato PBIP).
- Para portfólio, exporte um `.pdf` do relatório e anexe ao `docs/`.