class RandomMetricTypeException(Exception):
    pass


class GithubCollectorParamsException(Exception):
    pass


class MissingSupportedMetricException(Exception):
    pass


class MissingSupportedMeasureException(Exception):
    pass


class MissingSupportedSubCharacteristicError(Exception):
    pass


class EntityNotDefinedInReleaseConfigurationuration(ValueError):
    """
    Exceção criada quando uma entidade é procurada em uma pré-configuração,
    mas esta entidade não foi selecionada na pré-configuração.
    """
    pass


class MeasureNotDefinedInReleaseConfigurationuration(
    EntityNotDefinedInReleaseConfigurationuration,
):
    pass


class SubCharacteristicNotDefinedInReleaseConfigurationuration(
    EntityNotDefinedInReleaseConfigurationuration
):
    pass


class CharacteristicNotDefinedInReleaseConfigurationuration(
    EntityNotDefinedInReleaseConfigurationuration
):
    pass


class InvalidReleaseConfigurationException(ValueError):
    pass


class CalculateModelException(
    Exception
):
    pass
