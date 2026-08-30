-- sql/views.sql
-- Views analíticas para o Power BI (camada semântica sobre o star schema).
-- Todas as views são recriáveis (CREATE OR REPLACE) e filtram NULLs onde faz sentido.

-- 1) IDEB médio por região e ano (rede pública) — gráfico de linhas
CREATE OR REPLACE VIEW vw_ideb_medio_regiao_ano AS
SELECT
    d.nome_regiao,
    d.sigla_regiao,
    f.ano,
    COUNT(*)                         AS municipios_avaliados,
    COUNT(*) FILTER (WHERE f.ideb IS NOT NULL) AS municipios_com_ideb,
    ROUND(AVG(f.ideb)::numeric, 2)   AS ideb_medio,
    ROUND(MIN(f.ideb)::numeric, 1)   AS ideb_min,
    ROUND(MAX(f.ideb)::numeric, 1)   AS ideb_max
FROM fato_ideb f
JOIN dim_estado d ON d.id_estado = f.id_estado
WHERE f.rede = 'Pública'
GROUP BY d.nome_regiao, d.sigla_regiao, f.ano
ORDER BY f.ano, d.nome_regiao;

-- 2) Ranking de municípios por IDEB (ano mais recente) — tabela / barras
CREATE OR REPLACE VIEW vw_ideb_ranking_municipios AS
SELECT
    f.codigo_municipio,
    f.nome_municipio,
    f.uf,
    d.nome_regiao,
    f.rede,
    f.ano,
    f.ideb,
    RANK() OVER (PARTITION BY f.ano, f.rede ORDER BY f.ideb DESC) AS posicao
FROM fato_ideb f
JOIN dim_estado d ON d.id_estado = f.id_estado
WHERE f.ideb IS NOT NULL;

-- 3) PIB por UF e ano — barras / série temporal
CREATE OR REPLACE VIEW vw_pib_por_uf_ano AS
SELECT
    d.sigla      AS uf,
    d.nome       AS nome_uf,
    d.nome_regiao,
    f.ano,
    f.variavel,
    f.valor,
    f.unidade
FROM fato_pib f
JOIN dim_estado d ON d.id_estado = f.id_estado
WHERE f.valor IS NOT NULL;

-- 4) População por UF e ano — complemento do PIB
CREATE OR REPLACE VIEW vw_populacao_por_uf_ano AS
SELECT
    d.sigla      AS uf,
    d.nome       AS nome_uf,
    d.nome_regiao,
    f.ano,
    f.populacao
FROM fato_populacao f
JOIN dim_estado d ON d.id_estado = f.id_estado;

-- 5) Painel combinado: PIB + população + IDEB médio por UF/ano — dispersão
CREATE OR REPLACE VIEW vw_painel_uf_ano AS
WITH pib AS (
    SELECT id_estado, ano, SUM(valor) FILTER (WHERE variavel LIKE 'Produto Interno Bruto%') AS pib_total
    FROM fato_pib GROUP BY id_estado, ano
),
pop AS (
    SELECT id_estado, ano, populacao FROM fato_populacao
),
ideb AS (
    SELECT id_estado, ano, ROUND(AVG(ideb)::numeric, 2) AS ideb_medio
    FROM fato_ideb WHERE rede = 'Pública' AND ideb IS NOT NULL
    GROUP BY id_estado, ano
)
SELECT
    d.id_estado,
    d.sigla AS uf,
    d.nome  AS nome_uf,
    d.nome_regiao,
    COALESCE(pib.ano, pop.ano, ideb.ano) AS ano,
    pop.populacao,
    pib.pib_total,
    CASE WHEN pop.populacao > 0 THEN ROUND((pib.pib_total * 1000 / pop.populacao)::numeric, 2) END AS pib_per_capita,
    ideb.ideb_medio
FROM dim_estado d
LEFT JOIN pib  ON pib.id_estado  = d.id_estado
LEFT JOIN pop  ON pop.id_estado  = d.id_estado AND pop.ano = pib.ano
LEFT JOIN ideb ON ideb.id_estado = d.id_estado AND ideb.ano = COALESCE(pib.ano, pop.ano);