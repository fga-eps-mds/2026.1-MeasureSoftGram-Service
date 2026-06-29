# 📊 Grafana - MeasureSoftGram

Documentação completa para configuração, uso e desenvolvimento de dashboards no Grafana para o projeto MeasureSoftGram.

---

## 📁 Estrutura do Diretório

```
grafana/
├── dashboards/                    # Dashboards em JSON (carregados automaticamente)
│   ├── 1-vis-o-geral-de-qualidade.json
│   ├── 2-evolu-o-temporal.json
│   ├── 3-an-lise-por-entidade.json
│   ├── 4-meta-modelo-e-pesos.json
│   ├── 5-distribui-o-estat-stica.json
│   ├── 6-rela-es-e-correla-es.json
│   └── 7-tsqmi-ecg.json          # ⭐ Dashboard de TSQMI com pulso ECG
│
├── provisioning/                  # Configurações de provisionamento automático
│   ├── dashboards/
│   │   └── measuresoftgram.yml   # Config para carregar dashboards
│   └── datasources/
│       └── measuresoftgram.yml   # Config da conexão PostgreSQL
│
├── seed_tsqmi_10_medicoes.sql    # Script SQL rápido para popular TSQMI
└── README.md                      # 📖 Este arquivo
```

---

## 🔑 Variáveis de Ambiente

### Desenvolvimento (`env-vars/`)

O Grafana usa variáveis de três arquivos diferentes. Os arquivos ficam em `env-vars/` (gitignored — nunca versionados).

#### `env-vars/.postgres.env` — compartilhado com o service

```env
POSTGRES_HOST=db
POSTGRES_DB=postgres
POSTGRES_USER=postgres
POSTGRES_PORT=5432
POSTGRES_PASSWORD=postgres
```

Essas variáveis alimentam automaticamente o datasource do Grafana via `grafana/provisioning/datasources/measuresoftgram.yml`. Não é necessário duplicar — o container Grafana já recebe esse arquivo.

#### `env-vars/.service.env` — adições para o proxy Django

```env
# URL pública do Grafana — usada pelo backend para montar o grafana_url
# retornado pela API e consumido pelo frontend
GRAFANA_PUBLIC_URL=http://localhost:5000       # desenvolvimento
# GRAFANA_PUBLIC_URL=https://<dominio>/grafana  # produção

# Credenciais de admin do Grafana (mesmas do .grafana.env)
# usadas pelo Django para consultar a API interna do Grafana
GRAFANA_USERNAME=admin
GRAFANA_PASSWORD=admin123
```

---

### Produção (`deploy/env-vars/`)

Em produção os arquivos ficam em `deploy/env-vars/` na box. São gitignored e provisionados manualmente.

#### `deploy/env-vars/.grafana.env` — credenciais de admin do Grafana

Deve ser criado na box antes do primeiro `docker compose up`:

```env
GF_SECURITY_ADMIN_USER=admin
GF_SECURITY_ADMIN_PASSWORD=<senha-forte>
```

#### `deploy/env-vars/.service.env` — adições obrigatórias em produção

```env
# URL pública onde o Grafana é acessível pelo navegador
GRAFANA_PUBLIC_URL=https://<dominio>/grafana

# Mesmas credenciais do .grafana.env (o Django usa a API interna do Grafana)
GRAFANA_USERNAME=admin
GRAFANA_PASSWORD=<mesma-senha-forte>
```

#### `deploy/env-vars/.postgres.env` — igual ao de desenvolvimento

```env
POSTGRES_HOST=db
POSTGRES_DB=<nome-do-banco>
POSTGRES_USER=<usuario>
POSTGRES_PORT=5432
POSTGRES_PASSWORD=<senha-forte>
```

Esse arquivo é lido pelo container do Grafana (datasource) **e** pelo container do service (Django ORM).

---

### Referência completa das variáveis do Grafana

| Variável | Onde definir | Descrição |
|---|---|---|
| `POSTGRES_HOST` | `.postgres.env` | Host do banco (interno Docker: `db`) |
| `POSTGRES_DB` | `.postgres.env` | Nome do banco |
| `POSTGRES_USER` | `.postgres.env` | Usuário do banco |
| `POSTGRES_PASSWORD` | `.postgres.env` | Senha do banco |
| `GF_SECURITY_ADMIN_USER` | `.grafana.env` | Login do painel admin do Grafana |
| `GF_SECURITY_ADMIN_PASSWORD` | `.grafana.env` | Senha do painel admin do Grafana |
| `GRAFANA_PUBLIC_URL` | `.service.env` | URL pública do Grafana (usada pelo Django para gerar links do iframe) |
| `GRAFANA_USERNAME` | `.service.env` | Mesmo valor de `GF_SECURITY_ADMIN_USER` |
| `GRAFANA_PASSWORD` | `.service.env` | Mesmo valor de `GF_SECURITY_ADMIN_PASSWORD` |

---

## 🚀 Guia Rápido - Primeiros Passos

### 1. Iniciar o Ambiente

```bash
# No diretório raiz do projeto
docker compose up -d

# Verificar se os containers estão rodando
docker compose ps
```

**Containers esperados:**
- ✅ `db` - PostgreSQL (porta 5432)
- ✅ `service` - Django backend (porta 8080)
- ✅ `grafana` - Grafana (porta **5000** no host)

### 2. Acessar o Grafana

Abra no navegador: **http://localhost:5000**

**Credenciais:**
- Usuário: `admin`
- Senha: `admin123`

### 3. Popular Dados de Teste

**IMPORTANTE:** Para visualizar os gráficos, especialmente o Dashboard 7 (TSQMI ECG), você precisa popular o banco com dados.

```bash
# Entra no container do service
docker exec -it service bash

# Executa o seed (gera 10 medições de TSQMI + métricas completas)
python manage.py seed_grafana --days 180 --clean-tsqmi

# Sair do container
exit
```

---

## 🗄️ Conectar ao Banco de Dados PostgreSQL

### Credenciais

```
Host:     localhost (ou 127.0.0.1)
Porta:    5432
Database: postgres
Usuário:  postgres
Senha:    postgres
```

### Via psql (Terminal)

```bash
# Dentro do container
docker exec -it db psql -U postgres -d postgres

# Do host (se tiver psql instalado)
psql -h localhost -p 5432 -U postgres -d postgres
```

### Via Cliente Gráfico (DBeaver, pgAdmin, etc.)

Configure uma nova conexão PostgreSQL com as credenciais acima.

---

## 📊 Dashboard 7 - TSQMI com Pulso ECG

Este é o dashboard principal para visualização de qualidade com comportamento de eletrocardiograma (ECG).

### Como Funciona

O dashboard detecta **transições** (mudanças de valor) no TSQMI e aplica um **pulso ECG** apenas nesses pontos.

#### Função msgPulse

```javascript
function msgPulse(valueA, valueB, timeA, timeB) {
  const SPS = 12; // 12 pontos interpolados por transição
  const delta = valueB - valueA;
  const peakAmplitude = delta * 2.2; // Pico 2.2x maior que a variação

  // 5 fases do pulso ECG:
  // 1. Base inicial (30%) - mantém valueA
  // 2. Subida (12%) - sobe ao pico usando seno
  // 3. Descida (14%) - desce do pico
  // 4. Onda de retorno (12%) - pequena oscilação
  // 5. Nova base (32%) - estabiliza em valueB
}
```

### Cores dos Repositórios

- 🟢 **CLI**: Verde `#1D9E75`
- 🔵 **Core**: Azul `#378ADD`
- 🟠 **Service**: Laranja `#D85A30`
- 🔴 **Front**: Rosa `#D4537E`

### Dados Necessários

Para visualizar corretamente, cada repositório precisa ter **10 medições de TSQMI** com valores variados. Isso gera **9 transições** = **9 pulsos ECG** visíveis.

---

## 🔧 Popular Dados de Teste - Detalhado

### Comando Django (`seed_grafana`)

**O que faz:**
- ✅ Popula métricas coletadas (CollectedMetric)
- ✅ Popula medidas calculadas (CalculatedMeasure)
- ✅ Popula subcaracterísticas (CalculatedSubCharacteristic)
- ✅ Popula características (CalculatedCharacteristic)
- ✅ Popula **10 medições de TSQMI** por repositório
- ✅ Cria Goals e Releases
- ✅ Atualiza painéis via API do Grafana

**Como executar:**

```bash
# 1. Entrar no container do service
docker exec -it service bash

# 2. Executar o seed
python manage.py seed_grafana --days 180 --clean-tsqmi

# 3. Sair do container
exit
```

**Parâmetros disponíveis:**

```bash
# Especificar número de dias de histórico (padrão: 180)
python manage.py seed_grafana --days 365

# Popular apenas repositórios específicos
python manage.py seed_grafana --repos "MeasureSoftGram-CLI,MeasureSoftGram-Core"

# Limpar TSQMI antigo antes de recriar
python manage.py seed_grafana --clean-tsqmi

# URL personalizada do Grafana
python manage.py seed_grafana --grafana-url http://localhost:3000
```

**Localização do script:**
```
src/organizations/management/commands/seed_grafana.py
```

---

## 📥 Como Importar Dashboards dos Arquivos JSON

Os dashboards JSON estão na pasta `grafana/dashboards/`. Para importá-los no Grafana:

### Método 1: Provisionamento Automático (Recomendado)

Os dashboards são carregados **automaticamente** quando o Grafana inicia. Basta:

```bash
# 1. Colocar o arquivo JSON na pasta dashboards
cp seu-dashboard.json grafana/dashboards/8-meu-novo-dashboard.json

# 2. Reiniciar o Grafana
docker restart grafana

# 3. Aguardar ~15 segundos
sleep 15

# 4. Verificar se foi carregado
docker logs grafana 2>&1 | grep "provisioning.dashboard"
```

O dashboard aparecerá automaticamente em **Dashboards → Browse**.

---

### Método 2: Importação Manual via UI

Se preferir importar manualmente um dashboard JSON:

1. Acesse **http://localhost:3000**
2. No menu lateral, vá em **Dashboards** → **Import**
3. Clique em **Upload JSON file**
4. Selecione o arquivo da pasta `grafana/dashboards/`
5. Configure:
   - **Name:** (nome do dashboard)
   - **Folder:** General
   - **UID:** (deixe vazio ou use o UID do JSON)
6. Clique em **Import**

---

### Método 3: Copiar e Colar JSON

1. Acesse **http://localhost:3000**
2. Vá em **Dashboards** → **Import**
3. Clique em **Import via panel json**
4. Abra o arquivo JSON:
   ```bash
   cat grafana/dashboards/7-tsqmi-ecg.json
   ```
5. Copie todo o conteúdo
6. Cole no campo de texto do Grafana
7. Clique em **Load**
8. Configure nome e pasta
9. Clique em **Import**

---

## 📝 Como Adicionar Novos Dashboards

Se você criou um novo dashboard no Grafana e quer versioná-lo:

### Passo 1: Exportar o Dashboard

1. No Grafana, abra o dashboard criado
2. Clique no ícone ⚙️ **Dashboard settings** (canto superior direito)
3. Vá em **JSON Model** no menu lateral
4. Clique em **Copy to Clipboard**

### Passo 2: Salvar como Arquivo JSON

```bash
# Criar novo arquivo na pasta dashboards
nano grafana/dashboards/8-meu-novo-dashboard.json

# Cole o JSON copiado e salve (Ctrl+O, Enter, Ctrl+X)
```

### Passo 3: Validar e Versionar

```bash
# Validar se o JSON está correto
python3 -m json.tool grafana/dashboards/8-meu-novo-dashboard.json > /dev/null

# Adicionar ao git
git add grafana/dashboards/8-meu-novo-dashboard.json
git commit -m "feat: adiciona Dashboard 8 - Meu Novo Dashboard"
git push
```

Agora outros colaboradores poderão carregar seu dashboard automaticamente!

---

## 🔍 Queries SQL Úteis

### Ver Repositórios

```sql
SELECT id, name
FROM organizations_repository
ORDER BY name;
```

### Ver Dados TSQMI

```sql
SELECT
  r.name as repositorio,
  to_char(t.created_at, 'DD/MM/YYYY HH24:MI') as data,
  t.value as tsqmi
FROM tsqmi_tsqmi t
JOIN organizations_repository r ON r.id = t.repository_id
WHERE r.name LIKE '%MeasureSoftGram%'
ORDER BY r.name, t.created_at;
```

### Contar Medições por Repositório

```sql
SELECT
  r.name,
  COUNT(*) as total_medicoes,
  to_char(MIN(t.created_at), 'DD/MM/YYYY') as primeira,
  to_char(MAX(t.created_at), 'DD/MM/YYYY') as ultima
FROM tsqmi_tsqmi t
JOIN organizations_repository r ON r.id = t.repository_id
WHERE r.name LIKE '%MeasureSoftGram%'
GROUP BY r.name
ORDER BY r.name;
```

### Verificar Transições (para pulso ECG)

```sql
SELECT
  r.name,
  to_char(t1.created_at, 'DD/MM/YYYY') as data,
  t1.value as valor_anterior,
  t2.value as valor_novo,
  (t2.value - t1.value) as variacao
FROM tsqmi_tsqmi t1
JOIN tsqmi_tsqmi t2 ON t2.id = (
  SELECT id FROM tsqmi_tsqmi
  WHERE repository_id = t1.repository_id
  AND created_at > t1.created_at
  ORDER BY created_at
  LIMIT 1
)
JOIN organizations_repository r ON r.id = t1.repository_id
WHERE r.name LIKE '%MeasureSoftGram%'
  AND t1.value != t2.value  -- Apenas transições
ORDER BY r.name, t1.created_at;
```

---

## 🐛 Resolução de Problemas

### Dashboard não aparece

```bash
# 1. Verificar logs de provisionamento
docker logs grafana 2>&1 | grep -i "dashboard"

# 2. Validar JSON
cat grafana/dashboards/7-tsqmi-ecg.json | python3 -m json.tool > /dev/null

# 3. Verificar permissões
ls -la grafana/dashboards/

# 4. Reiniciar Grafana
docker restart grafana
```

### Erro "data is not defined" no ECharts

Certifique-se de validar os dados no início do código JavaScript:

```javascript
// SEMPRE começar com esta validação
if (!data || !data.series || data.series.length === 0) {
  return {
    title: {
      text: 'Aguardando dados...',
      left: 'center',
      top: 'center',
      textStyle: { fontSize: 14, color: '#888' }
    }
  };
}
```

### Gráfico não mostra pulsos ECG

**Diagnóstico:**

```bash
# 1. Verificar se há dados TSQMI no banco
docker exec db psql -U postgres -d postgres -c \
  "SELECT COUNT(*) FROM tsqmi_tsqmi WHERE repository_id IN (6,7,8,9);"

# 2. Verificar se há transições (mudanças de valor)
docker exec db psql -U postgres -d postgres -c \
  "SELECT r.name, COUNT(DISTINCT t.value) as valores_unicos
   FROM tsqmi_tsqmi t
   JOIN organizations_repository r ON r.id = t.repository_id
   WHERE r.name LIKE '%MeasureSoftGram%'
   GROUP BY r.name;"
```

**Solução:**

```bash
# Repopular dados com o seed
docker exec -it service python manage.py seed_grafana --days 180 --clean-tsqmi
```

### Time Range incorreto

No Grafana, configure o Time Range (canto superior direito):
- **From:** `2025-01-01`
- **To:** `2025-12-31`

Ou use o seletor: **Last 1 year**

### Banco de dados não conecta

```bash
# Verificar se o PostgreSQL está rodando
docker ps | grep db

# Ver logs do PostgreSQL
docker logs db --tail 50

# Reiniciar o banco
docker restart db

# Testar conexão
docker exec db psql -U postgres -c "SELECT version();"
```

---

## 👥 Guia para Colaboradores

Se você vai criar novos dashboards para o projeto:

### 1. Ambiente de Desenvolvimento

```bash
# 1. Clone o repositório
git clone <repo-url>
cd 2026.1-MeasureSoftGram-Service

# 2. Suba o ambiente
docker compose up -d

# 3. Popular dados de teste
docker exec -it service python manage.py seed_grafana --days 180 --clean-tsqmi
```

### 2. Exportar e Versionar Dashboard Criado

```bash
# 1. No Grafana: Settings → JSON Model → Copiar
# 2. Salvar em arquivo
cat > grafana/dashboards/X-nome-dashboard.json
# Cole o JSON e pressione Ctrl+D

# 3. Validar JSON
python3 -m json.tool grafana/dashboards/X-nome-dashboard.json > /dev/null

# 4. Commit
git add grafana/dashboards/X-nome-dashboard.json
git commit -m "feat: adiciona Dashboard X - Nome do Dashboard"
git push
```

### 3. Documentar

Documente o dashboard:
- Adicione comentários no código JavaScript (se usar ECharts)
- Descreva as queries SQL importantes
- Explique a lógica de cálculos customizados

---

## 📚 Referências e Recursos

### Documentação Oficial

- [Grafana Docs](https://grafana.com/docs/grafana/latest/)
- [PostgreSQL Data Source](https://grafana.com/docs/grafana/latest/datasources/postgres/)
- [Apache ECharts Plugin](https://echarts.volkovlabs.io/)
- [ECharts Documentation](https://echarts.apache.org/en/index.html)

### Arquivos de Configuração

- `docker-compose.yml` - Orquestração dos containers
- `env-vars/.postgres.env` - Credenciais do banco
- `grafana/provisioning/datasources/measuresoftgram.yml` - Config do datasource
- `grafana/provisioning/dashboards/measuresoftgram.yml` - Config de dashboards

### Plugins Instalados

- `volkovlabs-echarts-panel` - Para gráficos customizados com Apache ECharts

---

## 📞 Suporte

**Em caso de problemas:**

1. ✅ Consulte a seção **Resolução de Problemas** acima
2. ✅ Verifique os logs: `docker logs grafana` e `docker logs db`
3. ✅ Valide o JSON dos dashboards
4. ✅ Reexecute o seed de dados
5. ✅ Abra uma issue no repositório

---

**Última atualização:** Junho 2026
**Versão do Grafana:** latest
**Plugin ECharts:** volkovlabs-echarts-panel
