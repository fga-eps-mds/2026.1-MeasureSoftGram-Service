from typing import Set, Union

from django.db import models
from django.utils import timezone
from datetime import timedelta


class SupportedMetric(models.Model):
    """
    Métricas suportadas pelo sistema.

    Somente é possível cadastrar o valor de uma métrica se
    ela estiver cadastrada nesta tabela.
    """

    class Meta:
        ordering = ['key']

    class SupportedMetricTypes(models.TextChoices):
        INT = ('INT', 'Integer')
        FLOAT = ('FLOAT', 'Float')
        PERCENT = ('PERCENT', 'Percent')
        BOOL = ('BOOL', 'Boolean')
        STRING = ('STRING', 'String')
        DATA = ('DATA', 'Data')
        LEVEL = ('LEVEL', 'Level')
        MILLISEC = ('MILLISEC', 'Milliseconds')
        WORK_DUR = ('WORK_DUR', 'Work Duration')
        DISTRIB = ('DISTRIB', 'Distribution')
        RATING = ('RATING', 'Rating')

    # Identificador único da métrica
    key = models.CharField(max_length=128, unique=True)

    metric_type = models.CharField(
        max_length=15,
        choices=SupportedMetricTypes.choices,
        default=SupportedMetricTypes.FLOAT,
    )
    name = models.CharField(max_length=128)
    description = models.TextField(max_length=512, null=True, blank=True)

    def __str__(self):
        return self.key

    def get_latest_metric_value(
        self,
        repository,
    ) -> Union[float, str, int, bool, list]:
        """
        Função que recupera o valor mais recente da métrica
        """
        # Métricas que o parâmetro é uma lista de valores
        listed_values: Set[str] = {
            'coverage',
            'complexity',
            'functions',
            'comment_lines_density',
            'duplicated_lines_density',
        }

        github_values = [
            'total_issues',
            'resolved_issues',
            'sum_ci_feedback_times',
            'total_builds',
        ]

        uts_values: Set[str] = {'test_execution_time', 'tests'}

        if self.key in listed_values:
            return self.get_latest_metric_values(repository, qualifier='FIL')
        elif self.key in uts_values:
            return self.get_latest_metric_values(repository, qualifier='UTS')
        elif self.key in github_values:
            latest_metric = self.collected_metrics.filter(
                repository=repository,
                qualifier='FIL',
            ).first()
            if latest_metric:
                return latest_metric.value
        elif self.key not in listed_values.union(uts_values):
            latest_metric = self.collected_metrics.filter(
                repository=repository,
                qualifier='TRK',
            ).first()

            if latest_metric:
                return latest_metric.value
        return None

    def get_latest_metric_values(self, repository, qualifier) -> list:
        """
        Função que recupera os valores mais recentes de uma métrica.

        Observe que aqui, diferentemente de `get_latest_metric_value`
        retornamos uma lista, pois queremos os valores dessa métrica para
        todos os arquivos do projeto.

        Existem algumas medidas que para calcular é preciso da lista de valores
        de uma métrica em todos os arquivos. Como por exemplo a medida
        test_coverage, que precisa da cobertura (metrica coverage) dos
        vários arquivos quem compõe o repositório.
        """
        latest_metric = self.collected_metrics.filter(
            repository=repository,
        ).first()

        if latest_metric:
            same_day = latest_metric.created_at

            # Remove hours, minutes and seconds
            begin = same_day - timedelta(minutes=20)
            end = same_day

            # Métrica de arquivos (inclusive de arquivos vazios)
            metrics_qs = self.collected_metrics.filter(
                qualifier=qualifier,
                created_at__gte=begin,
                created_at__lte=end,
                repository=repository,
            )

            # Métrica do número de linhas
            ncloc_metric = SupportedMetric.objects.get(key='ncloc')

            # Arquivos vazios (sem código relevante)
            qs = ncloc_metric.collected_metrics.filter(
                created_at__gte=begin,
                created_at__lte=end,
                qualifier=qualifier,
                value=0,
                repository=repository,
            ).values_list('path', flat=True)

            empty_files_set = set(qs)

            # Somente os valores dos arquivos que não são vazios
            return [
                m.value for m in metrics_qs if m.path not in empty_files_set
            ]

        return []


class CollectedMetric(models.Model):
    """
    Métricas é o maior grau de granualidade de dados.
    São os dados coletados de diversas fontes (SonarQube, GitHub, etc).

    O MeasureSoftGram permite a coleta de qualquer métrica. Desse modo, quando
    é perguntado o valor atual ou histórico das métricas de um projeto, além
    das métricas coletadas pelos usuários, também é retornado o valor das
    métricas famosas, e caso as métricas famosas não tenham sido coletadas, o
    valor da métrica é retornado como None.
    """

    class Meta:
        # Aqui estamos ordenando na ordem decrescente, ou seja, nos querysets
        # os registros mais recentes vem primeiro (qs.first() == mais recente)
        ordering = ['-created_at']

    metric = models.ForeignKey(
        SupportedMetric,
        related_name='collected_metrics',
        on_delete=models.CASCADE,
    )
    value = models.FloatField()

    # As métricas do SonarQube geralmente estão associadas a um arquivo ou diretório
    path = models.CharField(
        max_length=255,
        default=None,
        null=True,
        blank=True,
    )

    # Qualifer informar se essa métrica é de arquivo de teste, de diretório etc
    """
    BRC - Sub-projects
    DIR - Directories
    FIL - Files
    TRK - Projects
    UTS - Test Files
    https://python-sonarqube-api.readthedocs.io/en/latest/sonarqube.community.html#sonarqube.community.components.SonarQubeComponents
    """
    qualifier = models.CharField(
        max_length=5,
        default=None,
        null=True,
        blank=True,
    )

    # dynamic key é usado para especificar atributos dinâmicos de métricas genéricas
    dynamic_key = models.CharField(max_length=128, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    repository = models.ForeignKey(
        to='organizations.Repository',
        related_name='collected_metrics',
        on_delete=models.CASCADE,
    )
