from staticfiles import SUPPORTED_MEASURES

from utils.staticfiles import RUNTIME_AVAILABLE_METRICS


def _derive_runtime_measure_keys():
    """Deriva do catálogo do msgram-core quais medidas são runtime measures.

    Runtime measure é toda medida suportada que depende de pelo menos uma
    métrica de observabilidade (RUNTIME_AVAILABLE_METRICS). Derivar em vez de
    listar na mão faz o Service acompanhar sozinho quando o core adicionar
    uma medida nova desse tipo.
    """
    runtime_metric_keys = {metric["key"] for metric in RUNTIME_AVAILABLE_METRICS}

    keys = set()
    for measure_data in SUPPORTED_MEASURES:
        measure_key = next(iter(measure_data))
        required_metrics = set(measure_data[measure_key]["metrics"])
        if required_metrics & runtime_metric_keys:
            keys.add(measure_key)

    return frozenset(keys)


# Computado uma vez no import: SUPPORTED_MEASURES e RUNTIME_AVAILABLE_METRICS
# são estáticos, não faz sentido recalcular a cada cálculo de medida.
RUNTIME_MEASURE_KEYS = _derive_runtime_measure_keys()


def parse_release_configuration(pre_config):
    # Parse configuracao de release para pegar chaves do que foi planejado
    characteristics = []
    subcharacteristics = []
    measures = []

    for characteristic in pre_config["data"]["characteristics"]:
        characteristics.append(characteristic["key"])
        for subcharacteristic in characteristic["subcharacteristics"]:
            subcharacteristics.append(subcharacteristic["key"])
            for measure in subcharacteristic["measures"]:
                measures.append(measure["key"])

    return characteristics, subcharacteristics, measures
