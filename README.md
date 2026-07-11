# 2026.1 MeasureSoftGram-Service

## Badges

[![Code Smells](https://sonarcloud.io/api/project_badges/measure?project=fga-eps-mds_2026.1-MeasureSoftGram-Service&metric=code_smells)](https://sonarcloud.io/summary/new_code?id=fga-eps-mds_2026.1-MeasureSoftGram-Service)
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=fga-eps-mds_2026.1-MeasureSoftGram-Service&metric=sqale_rating)](https://sonarcloud.io/summary/new_code?id=fga-eps-mds_2026.1-MeasureSoftGram-Service)
[![Security Rating](https://sonarcloud.io/api/project_badges/measure?project=fga-eps-mds_2026.1-MeasureSoftGram-Service&metric=security_rating)](https://sonarcloud.io/summary/new_code?id=fga-eps-mds_2026.1-MeasureSoftGram-Service)
[![Bugs](https://sonarcloud.io/api/project_badges/measure?project=fga-eps-mds_2026.1-MeasureSoftGram-Service&metric=bugs)](https://sonarcloud.io/summary/new_code?id=fga-eps-mds_2026.1-MeasureSoftGram-Service)
[![Vulnerabilities](https://sonarcloud.io/api/project_badges/measure?project=fga-eps-mds_2026.1-MeasureSoftGram-Service&metric=vulnerabilities)](https://sonarcloud.io/summary/new_code?id=fga-eps-mds_2026.1-MeasureSoftGram-Service)
[![Duplicated Lines (%)](https://sonarcloud.io/api/project_badges/measure?project=fga-eps-mds_2026.1-MeasureSoftGram-Service&metric=duplicated_lines_density)](https://sonarcloud.io/summary/new_code?id=fga-eps-mds_2026.1-MeasureSoftGram-Service)
[![Reliability Rating](https://sonarcloud.io/api/project_badges/measure?project=fga-eps-mds_2026.1-MeasureSoftGram-Service&metric=reliability_rating)](https://sonarcloud.io/summary/new_code?id=fga-eps-mds_2026.1-MeasureSoftGram-Service)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=fga-eps-mds_2026.1-MeasureSoftGram-Service&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=fga-eps-mds_2026.1-MeasureSoftGram-Service)
[![Technical Debt](https://sonarcloud.io/api/project_badges/measure?project=fga-eps-mds_2026.1-MeasureSoftGram-Service&metric=sqale_index)](https://sonarcloud.io/summary/new_code?id=fga-eps-mds_2026.1-MeasureSoftGram-Service)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=fga-eps-mds_2026.1-MeasureSoftGram-Service&metric=coverage)](https://sonarcloud.io/summary/new_code?id=fga-eps-mds_2026.1-MeasureSoftGram-Service)
[![Lines of Code](https://sonarcloud.io/api/project_badges/measure?project=fga-eps-mds_2026.1-MeasureSoftGram-Service&metric=ncloc)](https://sonarcloud.io/summary/new_code?id=fga-eps-mds_2026.1-MeasureSoftGram-Service)


## O que é

The MeasureSoftGram-Service is responsible for containing and manipulating MeasureSoftGram data: metrics, configuration goals, analyzes performed, etc. It uses the MVC layer pattern for building and organizing the service.

## How to use Service
- [How to use](https://fga-eps-mds.github.io/2021-2-MeasureSoftGram-Doc/docs/artifact/how_to_use)

## How to run Service

### 1. Configure as variáveis de ambiente

A pasta `env-vars/` é **gitignored** (contém credenciais). O repositório traz uma pasta `env-vars-example/` com os templates dos arquivos de ambiente. Antes do primeiro `docker compose up`, copie o exemplo:

```bash
cp -R env-vars-example env-vars
```

Os arquivos esperados em `env-vars/` são:

- `.postgres.env` — credenciais do Postgres (host, db, user, port, password)
- `.service.env` — `DEBUG`, `SECRET_KEY`, `GITHUB_CLIENT_ID`, `GITHUB_SECRET`, etc.

Edite os valores que precisar (em desenvolvimento, os defaults do `env-vars-example` já funcionam).

> **Nota:** em semestres anteriores o `docker-compose` lia `env-vars-example/` diretamente. A partir desta release a separação `example/` × `env-vars/` é obrigatória — o caminho `./env-vars/.postgres.env` está fixado em `docker-compose.yml`.

> Atalho: `make env` faz o `cp -R env-vars-example env-vars` (e `make setup` já copia antes de subir). Mantemos a pasta `env-vars/` em vez de um único `.env` na raiz porque os caminhos `./env-vars/.service.env` e `./env-vars/.postgres.env` estão fixados no `docker-compose.yml`.

### 1.1. Configurar o GitHub OAuth App (login com GitHub em dev)

Os defaults de `GITHUB_CLIENT_ID` / `GITHUB_SECRET` no `env-vars-example/.service.env` são placeholders (`CL13NT1D` / `S3CR3T`): a API sobe, mas o **login real com GitHub** só funciona com um OAuth App próprio. Para habilitá-lo em desenvolvimento:

1. Acesse **GitHub → Settings → Developer settings → OAuth Apps → New OAuth App** (<https://github.com/settings/developers>).
2. Preencha:
   - **Application name**: livre (ex: `MeasureSoftGram (dev)`).
   - **Homepage URL**: `http://127.0.0.1:3000`
   - **Authorization callback URL**: `http://127.0.0.1:3000` — precisa **bater com o `LOGIN_REDIRECT_URL`**. O backend usa esse valor como `callback_url` na troca do `code` (`src/accounts/views.py`); em dev o callback é o próprio frontend, que recebe o `?code=` do GitHub e o repassa ao backend.
3. Clique em **Register application** e gere um **client secret**.
4. Cole os valores em `env-vars/.service.env`:

   ```env
   GITHUB_CLIENT_ID=<client id do OAuth App>
   GITHUB_SECRET=<client secret gerado>
   LOGIN_REDIRECT_URL=http://127.0.0.1:3000
   ```

5. Suba ou reinicie o service (`make up` / `docker compose up`).

Os **scopes** (`read:user`, `user:email`, `read:project`, `read:org`, `repo`) já estão definidos no backend (`SOCIALACCOUNT_PROVIDERS` em `config/settings/base.py`); não precisam ser configurados no OAuth App.

> **Produção:** use um OAuth App separado, com a *Authorization callback URL* apontando pro domínio real (ex: `http://msgram.lappis.rocks`) e as credenciais no `env-vars/.service.env` do servidor. Os placeholders de PROD estão comentados no `env-vars-example/.service.env`.

### 2. Suba os containers

```bash
docker compose up
```

Em segundo plano:

```bash
docker compose up -d
```

### 3. Hot-reload em desenvolvimento

Esta release adiciona `develop.watch` no `docker-compose.yml`. Em vez de reconstruir manualmente a cada mudança, rode:

```bash
docker compose watch
```

Isso sincroniza automaticamente alterações em `src/` e refaz a instalação de dependências quando `pyproject.toml` muda.

### 4. Verifique

API disponível em [http://localhost:8080/](http://localhost:8080/).


## Endpoints

Swagger fica na rota `link/swagger/`


## Acessa o painel administrativo do MeasureSoftGram
- GET: https://epsmsg.shop/admin/
- Converse com os membros da equipe para solicitar uma credencial de acesso

## How to run tests

A partir desta release, o gerenciamento de dependências usa [`uv`](https://github.com/astral-sh/uv) com `pyproject.toml` + `uv.lock` (substituindo o antigo `requirements.txt`).

Instale o `uv` (caso ainda não tenha):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Sincronize as dependências:

```bash
uv sync
```

Rode os testes via `tox`:

```bash
uv run tox
```

Para testar um pacote ou arquivo específico:

```bash
uv run tox <PACKAGE OR FILE>
```


## Another informations

Our services are available on [Docker Hub](https://hub.docker.com/):
- [Core](https://hub.docker.com/r/measuresoftgram/core)
- [Service](https://hub.docker.com/r/measuresoftgram/service)

### Wiki

For more informations, you can see our wiki:
- [Wiki](https://fga-eps-mds.github.io/2026.1-MeasureSoftGram-DOC/).

## Contribute

Do you want to contribute with our project? Access our [contribution guide](https://github.com/fga-eps-mds/2026.1-MeasureSoftGram-Service/blob/develop/CONTRIBUTING.md) where we explain how you do it.

## License

AGPL-3.0 License

## Documentation

The documentation of this project can be accessed at this website: [Documentation](https://github.com/fga-eps-mds/2026.1-MeasureSoftGram-DOC).
