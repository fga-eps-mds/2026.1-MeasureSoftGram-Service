-- =====================================================================
-- Seed para Novos Dashboards do Grafana
-- =====================================================================
-- Este script popula dados para os seguintes dashboards:
--   1. Visão Geral de Qualidade (dashboard-visao-geral.json)
--   2. ECG TSQMI - Pulso de Qualidade (dashboard-ecg-tsqmi.json)
--   3. Evolução Temporal (dashboard-evolucao.json)
--   4. Saúde de Qualidade por Repositório (dashboard-saude-qualidade-repositorio.json)
--
-- Popula:
-- 1. Goal com pesos planejados para características
-- 2. Características calculadas (valores realizados) para repositórios
-- 3. GARANTE que TODAS as características sejam criadas para CADA data (evita NULL)
--
-- Como executar:
--   docker exec -i db psql -U postgres -d postgres < grafana/seed_planejado_vs_realizado.sql
-- =====================================================================

-- =====================================================================
-- 1. Criar Goal (Planejado) para o produto MeasureSoftGram
-- =====================================================================

-- Limpar releases antigas primeiro (para evitar violação de foreign key)
DELETE FROM releases WHERE product_id = 3;

-- Limpar goals antigos do produto MeasureSoftGram
DELETE FROM goals_goal WHERE product_id = 3;

-- Inserir Goal com pesos planejados para as 3 características
-- Os valores são em porcentagem (0-100) e representam o peso/importância
INSERT INTO goals_goal (created_at, created_by_id, product_id, data)
VALUES (
  NOW(),
  1, -- admin user
  3, -- MeasureSoftGram product
  jsonb_build_object(
    'reliability', '75',           -- 75% planejado para Reliability
    'maintainability', '80',       -- 80% planejado para Maintainability
    'functional_suitability', '70' -- 70% planejado para Functional Suitability
  )
);

-- =====================================================================
-- 2. Popular Características Calculadas (Realizado) para os 4 repositórios
-- =====================================================================
-- IMPORTANTE: As características devem ser criadas nas MESMAS datas dos TSQMIs
-- para que o dashboard de pulso ECG funcione corretamente (sem valores NULL)
--
-- IDs das características
-- reliability: 1
-- maintainability: 2
-- functional_suitability: 3
--
-- IDs dos repositórios MeasureSoftGram
-- CLI: 9
-- Core: 7
-- Service: 6
-- Front: 8

-- Limpar características e TSQMIs antigos
DELETE FROM tsqmi_tsqmi WHERE repository_id IN (6, 7, 8, 9);
DELETE FROM characteristics_calculatedcharacteristic WHERE repository_id IN (6, 7, 8, 9);

-- =====================================================================
-- CLI (id=9) - Perfil: Bom em Maintainability, Regular em outros
-- =====================================================================
-- IMPORTANTE: Criar TODAS as 3 características para CADA data (10 datas)
-- Isso evita valores NULL no dashboard quando agrupamos por data
-- As mesmas datas serão usadas para criar TSQMIs (pareamento perfeito)
INSERT INTO characteristics_calculatedcharacteristic (characteristic_id, value, created_at, repository_id)
VALUES
  -- Medição 1
  (1, 0.68, NOW() - INTERVAL '180 days', 9),
  (2, 0.82, NOW() - INTERVAL '180 days', 9),
  (3, 0.65, NOW() - INTERVAL '180 days', 9),

  -- Medição 2
  (1, 0.67, NOW() - INTERVAL '162 days', 9),
  (2, 0.81, NOW() - INTERVAL '162 days', 9),
  (3, 0.64, NOW() - INTERVAL '162 days', 9),

  -- Medição 3
  (1, 0.69, NOW() - INTERVAL '144 days', 9),
  (2, 0.83, NOW() - INTERVAL '144 days', 9),
  (3, 0.66, NOW() - INTERVAL '144 days', 9),

  -- Medição 4
  (1, 0.66, NOW() - INTERVAL '126 days', 9),
  (2, 0.80, NOW() - INTERVAL '126 days', 9),
  (3, 0.63, NOW() - INTERVAL '126 days', 9),

  -- Medição 5
  (1, 0.70, NOW() - INTERVAL '108 days', 9),
  (2, 0.84, NOW() - INTERVAL '108 days', 9),
  (3, 0.67, NOW() - INTERVAL '108 days', 9),

  -- Medição 6
  (1, 0.67, NOW() - INTERVAL '90 days', 9),
  (2, 0.81, NOW() - INTERVAL '90 days', 9),
  (3, 0.64, NOW() - INTERVAL '90 days', 9),

  -- Medição 7
  (1, 0.71, NOW() - INTERVAL '72 days', 9),
  (2, 0.85, NOW() - INTERVAL '72 days', 9),
  (3, 0.68, NOW() - INTERVAL '72 days', 9),

  -- Medição 8
  (1, 0.69, NOW() - INTERVAL '54 days', 9),
  (2, 0.83, NOW() - INTERVAL '54 days', 9),
  (3, 0.66, NOW() - INTERVAL '54 days', 9),

  -- Medição 9
  (1, 0.70, NOW() - INTERVAL '36 days', 9),
  (2, 0.84, NOW() - INTERVAL '36 days', 9),
  (3, 0.67, NOW() - INTERVAL '36 days', 9),

  -- Medição 10
  (1, 0.68, NOW() - INTERVAL '18 days', 9),
  (2, 0.82, NOW() - INTERVAL '18 days', 9),
  (3, 0.65, NOW() - INTERVAL '18 days', 9);

-- =====================================================================
-- Core (id=7) - Perfil: Excelente em Reliability, Bom geral
-- =====================================================================
INSERT INTO characteristics_calculatedcharacteristic (characteristic_id, value, created_at, repository_id)
VALUES
  -- 10 medições espaçadas uniformemente (180 dias / 10 = 18 dias cada)
  (1, 0.78, NOW() - INTERVAL '180 days', 7),
  (2, 0.75, NOW() - INTERVAL '180 days', 7),
  (3, 0.72, NOW() - INTERVAL '180 days', 7),

  (1, 0.77, NOW() - INTERVAL '162 days', 7),
  (2, 0.74, NOW() - INTERVAL '162 days', 7),
  (3, 0.71, NOW() - INTERVAL '162 days', 7),

  (1, 0.79, NOW() - INTERVAL '144 days', 7),
  (2, 0.76, NOW() - INTERVAL '144 days', 7),
  (3, 0.73, NOW() - INTERVAL '144 days', 7),

  (1, 0.76, NOW() - INTERVAL '126 days', 7),
  (2, 0.73, NOW() - INTERVAL '126 days', 7),
  (3, 0.70, NOW() - INTERVAL '126 days', 7),

  (1, 0.80, NOW() - INTERVAL '108 days', 7),
  (2, 0.77, NOW() - INTERVAL '108 days', 7),
  (3, 0.74, NOW() - INTERVAL '108 days', 7),

  (1, 0.77, NOW() - INTERVAL '90 days', 7),
  (2, 0.74, NOW() - INTERVAL '90 days', 7),
  (3, 0.71, NOW() - INTERVAL '90 days', 7),

  (1, 0.81, NOW() - INTERVAL '72 days', 7),
  (2, 0.78, NOW() - INTERVAL '72 days', 7),
  (3, 0.75, NOW() - INTERVAL '72 days', 7),

  (1, 0.79, NOW() - INTERVAL '54 days', 7),
  (2, 0.76, NOW() - INTERVAL '54 days', 7),
  (3, 0.73, NOW() - INTERVAL '54 days', 7),

  (1, 0.80, NOW() - INTERVAL '36 days', 7),
  (2, 0.77, NOW() - INTERVAL '36 days', 7),
  (3, 0.74, NOW() - INTERVAL '36 days', 7),

  (1, 0.78, NOW() - INTERVAL '18 days', 7),
  (2, 0.75, NOW() - INTERVAL '18 days', 7),
  (3, 0.72, NOW() - INTERVAL '18 days', 7);

-- =====================================================================
-- Service (id=6) - Perfil: Precisa melhorar
-- =====================================================================
INSERT INTO characteristics_calculatedcharacteristic (characteristic_id, value, created_at, repository_id)
VALUES
  -- 10 medições espaçadas uniformemente
  (1, 0.58, NOW() - INTERVAL '180 days', 6),
  (2, 0.62, NOW() - INTERVAL '180 days', 6),
  (3, 0.55, NOW() - INTERVAL '180 days', 6),

  (1, 0.57, NOW() - INTERVAL '162 days', 6),
  (2, 0.61, NOW() - INTERVAL '162 days', 6),
  (3, 0.54, NOW() - INTERVAL '162 days', 6),

  (1, 0.59, NOW() - INTERVAL '144 days', 6),
  (2, 0.63, NOW() - INTERVAL '144 days', 6),
  (3, 0.56, NOW() - INTERVAL '144 days', 6),

  (1, 0.56, NOW() - INTERVAL '126 days', 6),
  (2, 0.60, NOW() - INTERVAL '126 days', 6),
  (3, 0.53, NOW() - INTERVAL '126 days', 6),

  (1, 0.60, NOW() - INTERVAL '108 days', 6),
  (2, 0.64, NOW() - INTERVAL '108 days', 6),
  (3, 0.57, NOW() - INTERVAL '108 days', 6),

  (1, 0.57, NOW() - INTERVAL '90 days', 6),
  (2, 0.61, NOW() - INTERVAL '90 days', 6),
  (3, 0.54, NOW() - INTERVAL '90 days', 6),

  (1, 0.61, NOW() - INTERVAL '72 days', 6),
  (2, 0.65, NOW() - INTERVAL '72 days', 6),
  (3, 0.58, NOW() - INTERVAL '72 days', 6),

  (1, 0.59, NOW() - INTERVAL '54 days', 6),
  (2, 0.63, NOW() - INTERVAL '54 days', 6),
  (3, 0.56, NOW() - INTERVAL '54 days', 6),

  (1, 0.60, NOW() - INTERVAL '36 days', 6),
  (2, 0.64, NOW() - INTERVAL '36 days', 6),
  (3, 0.57, NOW() - INTERVAL '36 days', 6),

  (1, 0.58, NOW() - INTERVAL '18 days', 6),
  (2, 0.62, NOW() - INTERVAL '18 days', 6),
  (3, 0.55, NOW() - INTERVAL '18 days', 6);

-- =====================================================================
-- Front (id=8) - Perfil: Equilibrado
-- =====================================================================
INSERT INTO characteristics_calculatedcharacteristic (characteristic_id, value, created_at, repository_id)
VALUES
  -- 10 medições espaçadas uniformemente
  (1, 0.73, NOW() - INTERVAL '180 days', 8),
  (2, 0.78, NOW() - INTERVAL '180 days', 8),
  (3, 0.68, NOW() - INTERVAL '180 days', 8),

  (1, 0.72, NOW() - INTERVAL '162 days', 8),
  (2, 0.77, NOW() - INTERVAL '162 days', 8),
  (3, 0.67, NOW() - INTERVAL '162 days', 8),

  (1, 0.74, NOW() - INTERVAL '144 days', 8),
  (2, 0.79, NOW() - INTERVAL '144 days', 8),
  (3, 0.69, NOW() - INTERVAL '144 days', 8),

  (1, 0.71, NOW() - INTERVAL '126 days', 8),
  (2, 0.76, NOW() - INTERVAL '126 days', 8),
  (3, 0.66, NOW() - INTERVAL '126 days', 8),

  (1, 0.75, NOW() - INTERVAL '108 days', 8),
  (2, 0.80, NOW() - INTERVAL '108 days', 8),
  (3, 0.70, NOW() - INTERVAL '108 days', 8),

  (1, 0.72, NOW() - INTERVAL '90 days', 8),
  (2, 0.77, NOW() - INTERVAL '90 days', 8),
  (3, 0.67, NOW() - INTERVAL '90 days', 8),

  (1, 0.76, NOW() - INTERVAL '72 days', 8),
  (2, 0.81, NOW() - INTERVAL '72 days', 8),
  (3, 0.71, NOW() - INTERVAL '72 days', 8),

  (1, 0.74, NOW() - INTERVAL '54 days', 8),
  (2, 0.79, NOW() - INTERVAL '54 days', 8),
  (3, 0.69, NOW() - INTERVAL '54 days', 8),

  (1, 0.75, NOW() - INTERVAL '36 days', 8),
  (2, 0.80, NOW() - INTERVAL '36 days', 8),
  (3, 0.70, NOW() - INTERVAL '36 days', 8),

  (1, 0.73, NOW() - INTERVAL '18 days', 8),
  (2, 0.78, NOW() - INTERVAL '18 days', 8),
  (3, 0.68, NOW() - INTERVAL '18 days', 8);

-- =====================================================================
-- 3. Popular TSQMIs nas MESMAS datas das características calculadas
-- =====================================================================
-- IMPORTANTE: TSQMIs devem estar exatamente nas mesmas datas das características
-- para que o dashboard de pulso ECG funcione corretamente

-- CLI (id=9) - TSQMIs
INSERT INTO tsqmi_tsqmi (value, created_at, repository_id)
VALUES
  (0.72, NOW() - INTERVAL '180 days', 9),
  (0.71, NOW() - INTERVAL '162 days', 9),
  (0.73, NOW() - INTERVAL '144 days', 9),
  (0.70, NOW() - INTERVAL '126 days', 9),
  (0.74, NOW() - INTERVAL '108 days', 9),
  (0.71, NOW() - INTERVAL '90 days', 9),
  (0.75, NOW() - INTERVAL '72 days', 9),
  (0.73, NOW() - INTERVAL '54 days', 9),
  (0.74, NOW() - INTERVAL '36 days', 9),
  (0.72, NOW() - INTERVAL '18 days', 9);

-- Core (id=7) - TSQMIs
INSERT INTO tsqmi_tsqmi (value, created_at, repository_id)
VALUES
  (0.75, NOW() - INTERVAL '180 days', 7),
  (0.74, NOW() - INTERVAL '162 days', 7),
  (0.76, NOW() - INTERVAL '144 days', 7),
  (0.73, NOW() - INTERVAL '126 days', 7),
  (0.77, NOW() - INTERVAL '108 days', 7),
  (0.74, NOW() - INTERVAL '90 days', 7),
  (0.78, NOW() - INTERVAL '72 days', 7),
  (0.76, NOW() - INTERVAL '54 days', 7),
  (0.77, NOW() - INTERVAL '36 days', 7),
  (0.75, NOW() - INTERVAL '18 days', 7);

-- Service (id=6) - TSQMIs
INSERT INTO tsqmi_tsqmi (value, created_at, repository_id)
VALUES
  (0.58, NOW() - INTERVAL '180 days', 6),
  (0.57, NOW() - INTERVAL '162 days', 6),
  (0.59, NOW() - INTERVAL '144 days', 6),
  (0.56, NOW() - INTERVAL '126 days', 6),
  (0.60, NOW() - INTERVAL '108 days', 6),
  (0.57, NOW() - INTERVAL '90 days', 6),
  (0.61, NOW() - INTERVAL '72 days', 6),
  (0.59, NOW() - INTERVAL '54 days', 6),
  (0.60, NOW() - INTERVAL '36 days', 6),
  (0.58, NOW() - INTERVAL '18 days', 6);

-- Front (id=8) - TSQMIs
INSERT INTO tsqmi_tsqmi (value, created_at, repository_id)
VALUES
  (0.73, NOW() - INTERVAL '180 days', 8),
  (0.72, NOW() - INTERVAL '162 days', 8),
  (0.74, NOW() - INTERVAL '144 days', 8),
  (0.71, NOW() - INTERVAL '126 days', 8),
  (0.75, NOW() - INTERVAL '108 days', 8),
  (0.72, NOW() - INTERVAL '90 days', 8),
  (0.76, NOW() - INTERVAL '72 days', 8),
  (0.74, NOW() - INTERVAL '54 days', 8),
  (0.75, NOW() - INTERVAL '36 days', 8),
  (0.73, NOW() - INTERVAL '18 days', 8);

-- =====================================================================
-- Verificação dos Dados Inseridos
-- =====================================================================

-- Ver Goal criado (Planejado)
SELECT
  'GOAL PLANEJADO' as tipo,
  p.name as produto,
  g.data as pesos_planejados,
  to_char(g.created_at, 'DD/MM/YYYY HH24:MI') as criado_em
FROM goals_goal g
JOIN organizations_product p ON p.id = g.product_id
WHERE p.id = 3;

-- Ver média das características calculadas (Realizado) por repositório
SELECT
  'CARACTERÍSTICAS REALIZADAS' as tipo,
  r.name as repositorio,
  sc.name as caracteristica,
  ROUND(AVG(cc.value)::numeric, 3) as media_realizada,
  ROUND(STDDEV(cc.value)::numeric, 3) as dispersao,
  COUNT(*) as total_medicoes
FROM characteristics_calculatedcharacteristic cc
JOIN characteristics_supportedcharacteristic sc ON sc.id = cc.characteristic_id
JOIN organizations_repository r ON r.id = cc.repository_id
WHERE r.name LIKE '%MeasureSoftGram%'
  AND cc.created_at >= NOW() - INTERVAL '14 days'
GROUP BY r.name, sc.name
ORDER BY r.name, sc.name;

-- Verificar se há datas com características incompletas (valores NULL)
SELECT
  r.name as repositorio,
  cc.created_at::date AS data,
  COUNT(DISTINCT cc.characteristic_id) as chars_no_dia,
  CASE
    WHEN COUNT(DISTINCT cc.characteristic_id) = 3 THEN '✓ OK'
    ELSE '✗ INCOMPLETO - Causará NULL no dashboard!'
  END as status
FROM organizations_repository r
JOIN characteristics_calculatedcharacteristic cc ON cc.repository_id = r.id
WHERE r.name LIKE '%MeasureSoftGram%'
  AND cc.created_at >= NOW() - INTERVAL '180 days'
GROUP BY r.name, cc.created_at::date
HAVING COUNT(DISTINCT cc.characteristic_id) < 3
ORDER BY r.name, data;

-- Verificar pareamento entre TSQMIs e Características (CRÍTICO para pulso ECG)
SELECT
  r.name as repositorio,
  t.created_at::date as tsqmi_date,
  ROUND(t.value::numeric, 3) as tsqmi_value,
  COUNT(DISTINCT cc.characteristic_id) as chars_nessa_data,
  CASE
    WHEN COUNT(DISTINCT cc.characteristic_id) = 3 THEN '✓ PAREADO - Pulso ECG funcionará'
    ELSE '✗ DESPAREADO - Pulso ECG com erro!'
  END as status
FROM organizations_repository r
JOIN tsqmi_tsqmi t ON t.repository_id = r.id
LEFT JOIN characteristics_calculatedcharacteristic cc ON cc.repository_id = r.id
    AND cc.created_at::date = t.created_at::date
WHERE r.name LIKE '%MeasureSoftGram%'
GROUP BY r.name, t.created_at, t.value
ORDER BY r.name, t.created_at;

-- Comparação Planejado vs Realizado
WITH planejado AS (
  SELECT
    elem.key as char_key,
    ROUND((elem.value::numeric / 100), 3) as valor_planejado
  FROM goals_goal g
  CROSS JOIN LATERAL jsonb_each_text(g.data::jsonb) AS elem(key, value)
  WHERE g.product_id = 3
  ORDER BY g.created_at DESC
  LIMIT 3
),
realizado AS (
  SELECT
    sc.key as char_key,
    sc.name as char_name,
    ROUND(AVG(cc.value)::numeric, 3) as valor_realizado
  FROM characteristics_calculatedcharacteristic cc
  JOIN characteristics_supportedcharacteristic sc ON sc.id = cc.characteristic_id
  WHERE cc.created_at >= NOW() - INTERVAL '7 days'
    AND cc.repository_id IN (6, 7, 8, 9)
  GROUP BY sc.key, sc.name
)
SELECT
  'COMPARAÇÃO' as tipo,
  r.char_name as caracteristica,
  COALESCE(p.valor_planejado, 0) as planejado,
  r.valor_realizado as realizado,
  ROUND((r.valor_realizado - COALESCE(p.valor_planejado, 0))::numeric, 3) as diferenca,
  CASE
    WHEN r.valor_realizado >= COALESCE(p.valor_planejado, 0) THEN '✓ Atingiu'
    ELSE '✗ Abaixo'
  END as status
FROM realizado r
LEFT JOIN planejado p ON p.char_key = r.char_key
ORDER BY r.char_name;

-- =====================================================================
-- Resultado Esperado:
-- =====================================================================
-- Planejado:
-- - Reliability: 0.75 (75%)
-- - Maintainability: 0.80 (80%)
-- - Functional Suitability: 0.70 (70%)
--
-- Realizado (médias):
-- - Reliability: ~0.69 (69%)
-- - Maintainability: ~0.74 (74%)
-- - Functional Suitability: ~0.65 (65%)
--
-- Status:
-- - Reliability: ✗ Abaixo (-6%)
-- - Maintainability: ✗ Abaixo (-6%)
-- - Functional Suitability: ✗ Abaixo (-5%)
-- =====================================================================
