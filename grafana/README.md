# Grafana - MeasureSoftGram

Dashboards de qualidade provisionados automaticamente via arquivos JSON.

---

## Execução

```bash
docker compose up -d
```

Acesse em **http://localhost:5000** com as credenciais definidas em `env-vars/.grafana.env`.

Para recarregar dashboards sem reiniciar tudo:

```bash
docker restart grafana
```

---

## Popular dados de teste

```bash
docker exec -it service python manage.py seed_grafana --days 180 --clean-tsqmi
```

---

## Adicionar ou atualizar dashboards

Coloque o arquivo JSON em `grafana/dashboards/` e reinicie o container. O provisionamento é automático.

---

## Variáveis de ambiente

### Desenvolvimento (`env-vars/`)

**`.postgres.env`** — compartilhado com o service, alimenta o datasource do Grafana:

```env
POSTGRES_HOST=db
POSTGRES_DB=postgres
POSTGRES_USER=postgres
POSTGRES_PORT=5432
POSTGRES_PASSWORD=postgres
```

**`.grafana.env`** — credenciais do painel admin:

```env
GF_SECURITY_ADMIN_USER=admin
GF_SECURITY_ADMIN_PASSWORD=admin123
```

**`.service.env`** — adições para o proxy Django:

```env
GRAFANA_PUBLIC_URL=http://localhost:5000
GRAFANA_USERNAME=admin
GRAFANA_PASSWORD=admin123
```

---

### Produção (`deploy/env-vars/`)

**`.grafana.env`**:

```env
GF_SECURITY_ADMIN_USER=admin
GF_SECURITY_ADMIN_PASSWORD=<senha-forte>
```

**`.service.env`** — adições obrigatórias:

```env
GRAFANA_PUBLIC_URL=https://<dominio>/grafana
GRAFANA_USERNAME=admin
GRAFANA_PASSWORD=<mesma-senha-forte>
```

**`.postgres.env`** — mesmo formato do desenvolvimento, com credenciais de produção.

---

### Referência das variáveis

| Variável | Arquivo | Descrição |
|---|---|---|
| `POSTGRES_HOST` | `.postgres.env` | Host do banco (interno Docker: `db`) |
| `POSTGRES_DB` | `.postgres.env` | Nome do banco |
| `POSTGRES_USER` | `.postgres.env` | Usuário do banco |
| `POSTGRES_PASSWORD` | `.postgres.env` | Senha do banco |
| `GF_SECURITY_ADMIN_USER` | `.grafana.env` | Login do painel admin |
| `GF_SECURITY_ADMIN_PASSWORD` | `.grafana.env` | Senha do painel admin |
| `GRAFANA_PUBLIC_URL` | `.service.env` | URL pública usada pelo backend para gerar links do iframe |
| `GRAFANA_USERNAME` | `.service.env` | Mesmo valor de `GF_SECURITY_ADMIN_USER` |
| `GRAFANA_PASSWORD` | `.service.env` | Mesmo valor de `GF_SECURITY_ADMIN_PASSWORD` |
