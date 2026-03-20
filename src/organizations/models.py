from uuid import uuid4
from django.contrib.auth import get_user_model
from django.db import models
from django.utils.text import slugify
from release_configuration.models import ReleaseConfiguration
from utils import staticfiles
from decimal import Decimal


class Organization(models.Model):

    name = models.CharField(max_length=128)
    key = models.SlugField(max_length=128, unique=True, blank=True)
    description = models.TextField(
        max_length=512,
        null=True,
        blank=True,
    )
    members = models.ManyToManyField(
        get_user_model(),
        related_name='organizations',
        blank=True,
    )
    admin = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name='admin_organizations',
        null=True,
        blank=True,
    )

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = slugify(self.name)
            while Organization.objects.filter(key=self.key).exists():
                random_num = uuid4().hex[:6]
                self.key = f'{self.key}-{random_num}'
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    class Meta:
        unique_together = (('key', 'organization'),)

    name = models.CharField(max_length=128)
    key = models.SlugField(max_length=128, unique=True)
    description = models.TextField(
        max_length=512,
        null=True,
        blank=True,
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='products',
    )
    gaugeRedLimit = models.DecimalField(
        max_digits=3, decimal_places=2, default=Decimal('0.33')
    )
    gaugeYellowLimit = models.DecimalField(
        max_digits=3, decimal_places=2, default=Decimal('0.66')
    )

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = slugify(self.name)
            self.key = f'{self.organization.key}-{self.key}'
            while Product.objects.filter(key=self.key).exists():
                random_num = uuid4().hex[:6]
                self.key = f'{self.key}-{random_num}'

        super().save(*args, **kwargs)

        ReleaseConfiguration.objects.get_or_create(
            name='Default pre-config',
            data=staticfiles.DEFAULT_PRE_CONFIG,
            product=self,
        )


class Repository(models.Model):
    class Meta:
        unique_together = (('key', 'product'),)
        verbose_name_plural = 'Repositories'

    name = models.CharField(max_length=128)
    key = models.SlugField(max_length=128, unique=False, blank=True)
    url = models.URLField(max_length=200, blank=True, null=True)

    PLATFORM_CHOICES = (
        ('github', 'GitHub'),
        ('gitlab', 'GitLab'),
        ('bitbucket', 'Bitbucket'),
        ('subversion (SVN)', 'Subversion (SVN)'),
        ('mercurial', 'Mercurial'),
        ('aws code commit', 'AWS CodeCommit'),
        ('azure repos', 'Azure Repos'),
        ('outros', 'Outros'),
    )

    platform = models.CharField(
        max_length=128, choices=PLATFORM_CHOICES, blank=True, null=True
    )

    description = models.TextField(
        max_length=512,
        null=True,
        blank=True,
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='repositories',
    )

    imported = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        self.key = slugify(self.name)
        self.key = f'{self.product.key}-{self.key}'
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name
