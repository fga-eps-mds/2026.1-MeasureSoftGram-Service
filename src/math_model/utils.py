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
