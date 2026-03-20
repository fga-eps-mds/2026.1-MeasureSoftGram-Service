from typing import Dict, Iterable

from django.db import models
from django.utils import timezone


class Release(models.Model):
    """
    Tabela que armazena as releases de um produto
    """

    class Meta:
        db_table = 'releases'
        ordering = ('-created_at',)

    created_at = models.DateTimeField(default=timezone.now)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    release_name = models.CharField(max_length=255)
    created_by = models.ForeignKey(
        to='accounts.CustomUser',
        on_delete=models.CASCADE,
    )
    product = models.ForeignKey(
        to='organizations.Product',
        on_delete=models.CASCADE,
    )
    goal = models.ForeignKey(
        to='goals.Goal',
        on_delete=models.CASCADE,
    )
    description = models.TextField(max_length=512, null=True, blank=True)
