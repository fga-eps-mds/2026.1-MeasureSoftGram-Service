from django.contrib import admin

from organizations.models import Organization, Product, Repository


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'key',
        'description',
    )
    search_fields = (
        'name',
        'key',
    )


@admin.register(Product)
class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'key',
        'description',
    )
    search_fields = ('name',)
    list_filter = ('organization',)


@admin.register(Repository)
class RepositoryAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'key',
        'description',
    )
    search_fields = ('name',)
    list_filter = (
        'product',
        'product__organization',
    )
