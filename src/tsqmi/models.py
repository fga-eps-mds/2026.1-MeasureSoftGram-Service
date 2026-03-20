from django.db import models
from django.utils import timezone


class TSQMI(models.Model):
    """
    Classe que abstrai um a nota final do modelo, também conhecida como TSQMI.
    """

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'TSQMI'
        verbose_name_plural = 'TSQMI'

    value = models.FloatField()
    created_at = models.DateTimeField(default=timezone.now)

    repository = models.ForeignKey(
        to='organizations.Repository',
        related_name='calculated_tsqmis',
        on_delete=models.CASCADE,
    )
