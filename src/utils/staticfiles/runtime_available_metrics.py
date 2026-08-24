# flake8: noqa
# pylint: skip-file
# Métricas de execução exigidas pelas runtime measures do msgram-core 1.5.x
# (response_time, cpu_utilization, memory_utilization). Diferente das demais,
# não vêm do SonarQube nem da API do GitHub: são dados de observabilidade da
# aplicação em execução.
RUNTIME_AVAILABLE_METRICS = [
    {
        "key": "endpoint_calls",
        "metric_type": "INT",
        "name": "number of calls per endpoint",
    },
    {
        "key": "mean_response_time",
        "metric_type": "FLOAT",
        "name": "mean response time per endpoint",
    },
    {
        "key": "cpu_usage",
        "metric_type": "FLOAT",
        "name": "cpu usage per endpoint",
    },
    {
        "key": "memory_usage",
        "metric_type": "FLOAT",
        "name": "memory usage per endpoint",
    },
]
