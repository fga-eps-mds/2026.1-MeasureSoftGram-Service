# 2024-1 MeasureSoftGram-Service

## Badges

[![Code Smells](https://sonarcloud.io/api/project_badges/measure?project=fga-eps-mds_2023-1-MeasureSoftGram-Service&metric=code_smells)](https://sonarcloud.io/summary/new_code?id=fga-eps-mds_2023-1-MeasureSoftGram-Service)
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=fga-eps-mds_2023-1-MeasureSoftGram-Service&metric=sqale_rating)](https://sonarcloud.io/summary/new_code?id=fga-eps-mds_2023-1-MeasureSoftGram-Service)
[![Security Rating](https://sonarcloud.io/api/project_badges/measure?project=fga-eps-mds_2023-1-MeasureSoftGram-Service&metric=security_rating)](https://sonarcloud.io/summary/new_code?id=fga-eps-mds_2023-1-MeasureSoftGram-Service)
[![Bugs](https://sonarcloud.io/api/project_badges/measure?project=fga-eps-mds_2023-1-MeasureSoftGram-Service&metric=bugs)](https://sonarcloud.io/summary/new_code?id=fga-eps-mds_2023-1-MeasureSoftGram-Service)
[![Vulnerabilities](https://sonarcloud.io/api/project_badges/measure?project=fga-eps-mds_2023-1-MeasureSoftGram-Service&metric=vulnerabilities)](https://sonarcloud.io/summary/new_code?id=fga-eps-mds_2023-1-MeasureSoftGram-Service)
[![Duplicated Lines (%)](https://sonarcloud.io/api/project_badges/measure?project=fga-eps-mds_2023-1-MeasureSoftGram-Service&metric=duplicated_lines_density)](https://sonarcloud.io/summary/new_code?id=fga-eps-mds_2023-1-MeasureSoftGram-Service)
[![Reliability Rating](https://sonarcloud.io/api/project_badges/measure?project=fga-eps-mds_2023-1-MeasureSoftGram-Service&metric=reliability_rating)](https://sonarcloud.io/summary/new_code?id=fga-eps-mds_2023-1-MeasureSoftGram-Service)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=fga-eps-mds_2023-1-MeasureSoftGram-Service&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=fga-eps-mds_2023-1-MeasureSoftGram-Service)
[![Technical Debt](https://sonarcloud.io/api/project_badges/measure?project=fga-eps-mds_2023-1-MeasureSoftGram-Service&metric=sqale_index)](https://sonarcloud.io/summary/new_code?id=fga-eps-mds_2023-1-MeasureSoftGram-Service)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=fga-eps-mds_2023-1-MeasureSoftGram-Service&metric=coverage)](https://sonarcloud.io/summary/new_code?id=fga-eps-mds_2023-1-MeasureSoftGram-Service)
[![Lines of Code](https://sonarcloud.io/api/project_badges/measure?project=fga-eps-mds_2023-1-MeasureSoftGram-Service&metric=ncloc)](https://sonarcloud.io/summary/new_code?id=fga-eps-mds_2023-1-MeasureSoftGram-Service)


## O que é

The MeasureSoftGram-Service is responsible for containing and manipulating MeasureSoftGram data: metrics, configuration goals, analyzes performed, etc. It uses the MVC layer pattern for building and organizing the service.

## How to use Service
-[How to use](https://fga-eps-mds.github.io/2021-2-MeasureSoftGram-Doc/docs/artifact/how_to_use)

## How to run Service

Make the container with :

```
docker-compose up
```


## Endpoints

Swagger fica na rota `link/swagger/`


## Acessa o painel administrativo do MeasureSoftGram
- GET: https://epsmsg.shop/admin/
- Converse com os membros da equipe para socilitar uma credencial de acesso

## How to run tests
Install this dependencies

```
pip install -r requirements.txt
```

We are using tox for the tests, so it is good to install the tox:

```
pip install tox
```

Then you can run the tests using

```
 tox
```

if you want to especify the file use:
```
 tox <PACKAGE OR FILE>
```

If it does not work, you can try to run before:
```
pip install pytest-mock
```

## Another informations

Our services are available on [Docker Hub](https://hub.docker.com/):
- [Core](https://hub.docker.com/r/measuresoftgram/core)
- [Service](https://hub.docker.com/r/measuresoftgram/service)

### Wiki

For more informations, you can see our wiki:
- [Wiki](https://fga-eps-mds.github.io/2024.1-MeasureSoftGram-DOC/).

## Contribute

Do you want to contribute with our project? Access our [contribution guide](https://github.com/fga-eps-mds/2024-1-MeasureSoftGram-Service/blob/develop/CONTRIBUTING.md) where we explain how you do it.

## License

AGPL-3.0 License

## Documentation

The documentation of this project can be accessed at this website: [Documentation](https://github.com/fga-eps-mds/2023-1-MeasureSoftGram-Doc).
