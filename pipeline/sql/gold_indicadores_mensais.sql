-- Camada gold: um registro por mês, juntando câmbio, Selic e inflação.
-- Tabelas de entrada (carregadas da silver): dolar, euro, selic_meta, ipca — colunas (data TEXT 'AAAA-MM-DD', valor REAL).
-- LN e EXP são registradas pelo Python (gold.py), porque nem todo SQLite vem com funções matemáticas.

WITH
dolar_mensal AS (
    SELECT substr(data, 1, 7) AS mes, AVG(valor) AS dolar_medio
    FROM dolar
    GROUP BY 1
),
dolar_fechamento AS (
    SELECT mes, valor AS dolar_fechamento
    FROM (
        SELECT substr(data, 1, 7) AS mes,
               valor,
               ROW_NUMBER() OVER (PARTITION BY substr(data, 1, 7) ORDER BY data DESC) AS posicao
        FROM dolar
    )
    WHERE posicao = 1
),
euro_mensal AS (
    SELECT substr(data, 1, 7) AS mes, AVG(valor) AS euro_medio
    FROM euro
    GROUP BY 1
),
selic_fim_mes AS (
    SELECT mes, valor AS selic_meta
    FROM (
        SELECT substr(data, 1, 7) AS mes,
               valor,
               ROW_NUMBER() OVER (PARTITION BY substr(data, 1, 7) ORDER BY data DESC) AS posicao
        FROM selic_meta
    )
    WHERE posicao = 1
),
ipca_mensal AS (
    SELECT substr(data, 1, 7) AS mes, valor AS ipca_mes
    FROM ipca
),
base AS (
    SELECT d.mes,
           d.dolar_medio,
           f.dolar_fechamento,
           e.euro_medio,
           s.selic_meta,
           i.ipca_mes
    FROM dolar_mensal d
    LEFT JOIN dolar_fechamento f USING (mes)
    LEFT JOIN euro_mensal e USING (mes)
    LEFT JOIN selic_fim_mes s USING (mes)
    LEFT JOIN ipca_mensal i USING (mes)
),
acumulado AS (
    SELECT *,
           -- IPCA acumulado em 12 meses = produto de (1 + taxa mensal) - 1.
           -- Produto via soma de logaritmos; só calcula com os 12 meses completos.
           CASE WHEN COUNT(ipca_mes) OVER janela_12m = 12
                THEN (EXP(SUM(LN(1 + ipca_mes / 100.0)) OVER janela_12m) - 1) * 100
           END AS ipca_12m
    FROM base
    WINDOW janela_12m AS (ORDER BY mes ROWS BETWEEN 11 PRECEDING AND CURRENT ROW)
)
SELECT mes,
       ROUND(dolar_medio, 4)      AS dolar_medio,
       ROUND(dolar_fechamento, 4) AS dolar_fechamento,
       ROUND(euro_medio, 4)       AS euro_medio,
       ROUND(selic_meta, 2)       AS selic_meta,
       ROUND(ipca_mes, 2)         AS ipca_mes,
       ROUND(ipca_12m, 2)         AS ipca_12m,
       -- Juro real aproximado: Selic meta descontada do IPCA dos últimos 12 meses (ex-post).
       CASE WHEN selic_meta IS NOT NULL AND ipca_12m IS NOT NULL
            THEN ROUND(((1 + selic_meta / 100.0) / (1 + ipca_12m / 100.0) - 1) * 100, 2)
       END AS juro_real_aprox
FROM acumulado
ORDER BY mes;
