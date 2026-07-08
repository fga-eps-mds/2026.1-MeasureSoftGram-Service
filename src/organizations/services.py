import datetime as dt

from django.db.models import Count
from django.utils import timezone

from characteristics.models import CalculatedCharacteristic, SupportedCharacteristic
from goals.serializers import GoalSerializer
from measures.models import CalculatedMeasure, SupportedMeasure
from metrics.models import CollectedMetric, SupportedMetric
from organizations.management.commands.utils import get_random_changes
from organizations.models import Organization, Product, Repository
from releases.models import Release
from subcharacteristics.models import (
    CalculatedSubCharacteristic,
    SupportedSubCharacteristic,
)
from tsqmi.models import TSQMI
from utils import (
    get_random_datetime,
    get_random_path,
    get_random_qualifier,
    get_random_value,
)

MIN_CALCULATED_ENTITIES = 50
RELEASE_WINDOW_DAYS = 60
RELEASE_NAMES = ('v1.0.0', 'v2.0.0', 'v3.0.0')


def create_demo_organizations(owner):
    organizations = [
        {
            'name': 'fga-eps-mds',
            'description': (
                'Organização que agrupa os '
                'projetos de EPS e MDS da FGA.'
            ),
        },
        {
            'name': 'UnBArqDsw2021',
            'description': (
                'Organização que agrupa os '
                'projetos de Arquitetura e Desenvolvimento de '
                'Software do semestre 2021.01'
            ),
        },
        {
            'name': 'IHC-FGA-2020',
            'description': (
                'Organização que agrupa os projetos da disciplina de '
                'Interação Humano Computador'
            ),
        },
    ]

    for organization_data in organizations:
        organization, _ = Organization.objects.get_or_create(
            name=organization_data['name'],
            defaults={'description': organization_data['description']},
        )
        organization.admin = owner
        organization.save()
        organization.members.add(owner)


def create_demo_products():
    organizations = Organization.objects.all()

    organizations = {
        organization.name: organization for organization in organizations
    }

    products = [
        Product(
            name='Animalesco',
            description=(
                'Uma aplicação para realizar o controle e '
                'acompanhamento para com a saúde dos pets. '
                'Os usuários, após se registrarem, podem '
                'realizar o cadastro dos seus pets e a partir '
                'disso fazer o acompanhamento do bichinho de '
                'maneira digital.'
            ),
            organization=organizations['UnBArqDsw2021'],
        ),
        Product(
            name='BCE UnB',
            description=(
                'Este projeto possui o objetivo de analisar o '
                'site da BCE, se propondo a sugerir melhorias '
                'nos serviços de empréstimo de livros, '
                'com base nos conceitos aprendidos na '
                'discplina de IHC.'
            ),
            organization=organizations['IHC-FGA-2020'],
        ),
        Product(
            name='MeasureSoftGram',
            description=(
                'Este projeto que visa a construção de um '
                'sistema de análise quantitativa da qualidade '
                'de um sistema de software.'
            ),
            organization=organizations['fga-eps-mds'],
        ),
        Product(
            name='Acacia',
            description=(
                'Este projeto que visa a construção de um '
                'sistema de colaboração de colheita de '
                'árvores frutíferas em ambiente urbano.'
            ),
            organization=organizations['fga-eps-mds'],
        ),
    ]

    for product in products:
        if Product.objects.filter(
            name=product.name,
            organization=product.organization,
        ).exists():
            continue
        product.save()


def create_demo_repositories():
    products = Product.objects.all()

    products = {product.name: product for product in products}

    repositories = [
        Repository(
            name='2019.2-Acacia',
            description=('Repositório do backend do projeto Acacia.'),
            product=products['Acacia'],
        ),
        Repository(
            name='2019.2-Acacia-Frontend',
            description=('Repositório do frontend do projeto Acacia.'),
            product=products['Acacia'],
        ),
        Repository(
            name='2020.1-BCE',
            description=('Repositório do projeto BCE UnB.'),
            product=products['BCE UnB'],
        ),
        Repository(
            name='2021.1_G01_Animalesco_BackEnd',
            description=('Repositório do backend do projeto Animalesco.'),
            product=products['Animalesco'],
        ),
        Repository(
            name='2021.1_G01_Animalesco_FrontEnd',
            description=(
                'Repositório do frontend ' 'do projeto Animalesco.'
            ),
            product=products['Animalesco'],
        ),
        Repository(
            name='2022-1-MeasureSoftGram-Service',
            description=(
                'Repositório do backend do projeto ' 'MeasureSoftGram.'
            ),
            product=products['MeasureSoftGram'],
        ),
        Repository(
            name='2022-1-MeasureSoftGram-Core',
            description=(
                'Repositório da API do modelo matemático '
                'do projeto MeasureSoftGram'
            ),
            product=products['MeasureSoftGram'],
        ),
        Repository(
            name='2022-1-MeasureSoftGram-Front',
            description=(
                'Repositório do frontend da projeto ' 'MeasureSoftGram'
            ),
            product=products['MeasureSoftGram'],
        ),
        Repository(
            name='2022-1-MeasureSoftGram-CLI',
            description=('Repositório do CLI da projeto ' 'MeasureSoftGram'),
            product=products['MeasureSoftGram'],
        ),
    ]

    for repository in repositories:
        if Repository.objects.filter(
            name=repository.name,
            product=repository.product,
        ).exists():
            continue
        repository.save()


def _create_demo_calculated_entities(
    qs,
    calculated_entity_factory,
    bulk_create_klass,
    get_entity_qty,
):
    end_date = timezone.now()
    start_date = end_date - dt.timedelta(days=90)

    demo_calculated_entities = []

    for entity in qs:
        qty = get_entity_qty(entity)

        if qty < MIN_CALCULATED_ENTITIES:
            for _ in range(MIN_CALCULATED_ENTITIES - qty):
                created_at = get_random_datetime(start_date, end_date)
                demo_calculated_entities.append(
                    calculated_entity_factory(entity, created_at),
                )

    bulk_create_klass.objects.bulk_create(demo_calculated_entities)


def create_demo_collected_metrics(repository):
    qs = SupportedMetric.objects.all()

    def calculated_entity_factory(entity, created_at):
        metric_type = entity.metric_type
        value = get_random_value(metric_type)

        return CollectedMetric(
            metric=entity,
            path=get_random_path(),
            qualifier=get_random_qualifier(),
            value=value,
            created_at=created_at,
            repository=repository,
        )

    def get_entity_qty(entity):
        return entity.collected_metrics.filter(
            repository=repository,
        ).count()

    _create_demo_calculated_entities(
        qs,
        calculated_entity_factory,
        CollectedMetric,
        get_entity_qty,
    )


def create_demo_calculated_measures(repository):
    qs = SupportedMeasure.objects.all()

    def calculated_entity_factory(entity, created_at):
        return CalculatedMeasure(
            measure=entity,
            value=get_random_value('PERCENT'),
            created_at=created_at,
            repository=repository,
        )

    def get_entity_qty(entity):
        return entity.calculated_measures.filter(
            repository=repository,
        ).count()

    _create_demo_calculated_entities(
        qs,
        calculated_entity_factory,
        CalculatedMeasure,
        get_entity_qty,
    )


def create_demo_calculated_subcharacteristics(repository):
    qs = SupportedSubCharacteristic.objects.annotate(
        qty=Count('calculated_subcharacteristics'),
    )

    def calculated_entity_factory(entity, created_at):
        return CalculatedSubCharacteristic(
            subcharacteristic=entity,
            value=get_random_value('PERCENT'),
            created_at=created_at,
            repository=repository,
        )

    def get_entity_qty(entity):
        return entity.calculated_subcharacteristics.filter(
            repository=repository,
        ).count()

    _create_demo_calculated_entities(
        qs,
        calculated_entity_factory,
        CalculatedSubCharacteristic,
        get_entity_qty,
    )


def create_demo_calculated_characteristics(repository):
    qs = SupportedCharacteristic.objects.annotate(
        qty=Count('calculated_characteristics'),
    )

    def calculated_entity_factory(entity, created_at):
        return CalculatedCharacteristic(
            characteristic=entity,
            value=get_random_value('PERCENT'),
            created_at=created_at,
            repository=repository,
        )

    def get_entity_qty(entity):
        return entity.calculated_characteristics.filter(
            repository=repository,
        ).count()

    _create_demo_calculated_entities(
        qs,
        calculated_entity_factory,
        CalculatedCharacteristic,
        get_entity_qty,
    )


def create_demo_tsqmi_data(repository):
    qs = TSQMI.objects.filter(repository=repository)

    if qs.count() >= MIN_CALCULATED_ENTITIES:
        return

    TSQMI.objects.bulk_create(
        [
            TSQMI(
                value=get_random_value('PERCENT'),
                repository=repository,
            )
            for _ in range(MIN_CALCULATED_ENTITIES - qs.count())
        ]
    )


def create_demo_goal(product, owner, pre_config=None):
    """
    Cria um Goal (meta de qualidade) aleatório para `product`, atribuído a
    `owner`. Reaproveita o GoalSerializer para computar `data` a partir de
    `changes` via o Equalizer, exatamente como a criação de goal pela API.
    """
    pre_config = pre_config or product.release_configuration.first()
    characteristics_keys = [
        characteristic['key']
        for characteristic in pre_config.data['characteristics']
    ]

    serializer = GoalSerializer(
        data={
            'changes': get_random_changes(characteristics_keys),
            'allow_dynamic': False,
        }
    )

    class MockView:
        @staticmethod
        def get_product():
            return product

    serializer.context['view'] = MockView
    serializer.is_valid(raise_exception=True)
    return serializer.save(product=product, created_by=owner)


def create_demo_releases(product, owner):
    """
    Cria um pequeno histórico de releases (com seus respectivos goals) para
    `product`, com janelas de datas sequenciais e não sobrepostas. A última
    release fica com `end_at` no futuro, simulando uma release em andamento.
    """
    pre_config = product.release_configuration.first()
    now = timezone.now()
    releases_count = len(RELEASE_NAMES)

    for index, release_name in enumerate(RELEASE_NAMES):
        if Release.objects.filter(
            product=product,
            release_name=release_name,
        ).exists():
            continue

        start_at = now - dt.timedelta(
            days=(releases_count - index) * RELEASE_WINDOW_DAYS,
        )
        end_at = start_at + dt.timedelta(days=RELEASE_WINDOW_DAYS)

        goal = create_demo_goal(product, owner, pre_config)

        Release.objects.create(
            release_name=release_name,
            start_at=start_at,
            end_at=end_at,
            created_by=owner,
            product=product,
            goal=goal,
            description=f'Release {release_name} do produto {product.name}.',
        )


def seed_demo_data(owner):
    """
    Cria o catálogo de organizações/produtos/repositórios de demonstração,
    vinculando `owner` como admin/membro das organizações criadas, e povoa
    métricas, medidas, características, TSQMI, goals e releases de exemplo
    para que a conta demo veja o software funcionando com dados reais.
    """
    create_demo_organizations(owner)
    create_demo_products()
    create_demo_repositories()

    repositories = Repository.objects.filter(
        product__organization__admin=owner,
    )

    for repository in repositories:
        create_demo_collected_metrics(repository)
        create_demo_calculated_measures(repository)
        create_demo_calculated_subcharacteristics(repository)
        create_demo_calculated_characteristics(repository)
        create_demo_tsqmi_data(repository)

    products = Product.objects.filter(organization__admin=owner)

    for product in products:
        create_demo_releases(product, owner)
