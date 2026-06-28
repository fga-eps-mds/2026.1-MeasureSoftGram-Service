"""
Management command: seed_grafana

Popula o banco com dados ricos para visualização no Grafana:
  - 180 dias de histórico diário para cada entidade do modelo
  - Tendências realistas (melhora/piora + ruído)
  - Releases trimestrais com datas reais
  - Goals por produto linkados ao admin
  - TSQMI com timestamps corretos e evolução coerente
  - Métricas por arquivo para análise de distribuição estatística
  - Garante que TODAS as características sejam criadas para CADA data (evita NULL)

IMPORTANTE: Este seed popula dados para os seguintes dashboards:
  1. Visão Geral de Qualidade (dashboard-visao-geral.json)
  2. ECG TSQMI - Pulso de Qualidade (dashboard-ecg-tsqmi.json)
  3. Evolução Temporal (dashboard-evolucao.json)
  4. Saúde de Qualidade por Repositório (dashboard-saude-qualidade-repositorio.json)

Uso:
    python manage.py seed_grafana
    python manage.py seed_grafana --days 365
    python manage.py seed_grafana --repos "MeasureSoftGram-Service,MeasureSoftGram-Front"
    python manage.py seed_grafana --clean-all  # Limpa e recria todos os dados
"""

import json
import math
import random
import datetime as dt
import urllib.request
import urllib.error

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from characteristics.models import CalculatedCharacteristic, SupportedCharacteristic
from goals.models import Goal
from measures.models import CalculatedMeasure, SupportedMeasure
from metrics.models import CollectedMetric, SupportedMetric
from organizations.models import Product, Repository
from release_configuration.models import ReleaseConfiguration
from releases.models import Release
from subcharacteristics.models import CalculatedSubCharacteristic, SupportedSubCharacteristic
from tsqmi.models import TSQMI

User = get_user_model()

# Perfis de tendência: (slope_per_day, noise_amplitude, baseline)
# slope positivo = melhora ao longo do tempo
TREND_PROFILES = {
    'improving':  dict(slope=0.0008,  noise=0.06, base=0.45),
    'declining':  dict(slope=-0.0006, noise=0.06, base=0.75),
    'stable':     dict(slope=0.0001,  noise=0.04, base=0.60),
    'volatile':   dict(slope=0.0002,  noise=0.12, base=0.55),
    'recovering': dict(slope=0.0010,  noise=0.07, base=0.30),
}

REPO_PROFILES = {
    '2022-1-MeasureSoftGram-Service':  'improving',
    '2022-1-MeasureSoftGram-Front':    'volatile',
    '2022-1-MeasureSoftGram-Core':     'stable',
    '2022-1-MeasureSoftGram-CLI':      'declining',
    '2021.1_G01_Animalesco_BackEnd':   'recovering',
    '2021.1_G01_Animalesco_FrontEnd':  'stable',
    '2019.2-Acacia':                   'improving',
    '2019.2-Acacia-Frontend':          'declining',
    '2020.1-BCE':                      'volatile',
}


def _clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


def _trend_value(day_idx: int, profile_name: str, char_offset: float = 0.0) -> float:
    p = TREND_PROFILES[profile_name]
    base = _clamp(p['base'] + char_offset)
    linear = p['slope'] * day_idx
    wave = 0.03 * math.sin(2 * math.pi * day_idx / 30)  # ciclo mensal
    noise = random.gauss(0, p['noise'])
    return _clamp(base + linear + wave + noise)


def _make_timestamps(days: int, end: dt.datetime) -> list[dt.datetime]:
    """Gera um timestamp por dia (com hora aleatória)."""
    return [
        end - dt.timedelta(days=days - i, hours=random.randint(0, 8), minutes=random.randint(0, 59))
        for i in range(days)
    ]


class Command(BaseCommand):
    help = 'Popula banco com dados ricos para visualização no Grafana'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=180, help='Dias de histórico')
        parser.add_argument(
            '--repos',
            type=str,
            default='',
            help='Nomes de repositórios separados por vírgula (vazio = todos)',
        )
        parser.add_argument(
            '--clean-tsqmi',
            action='store_true',
            default=False,
            help='Apaga os TSQMI sem timestamps corretos antes de recriar',
        )
        parser.add_argument(
            '--clean-all',
            action='store_true',
            default=False,
            help='Apaga TODOS os dados de características calculadas antes de recriar (corrige valores NULL)',
        )
        parser.add_argument(
            '--grafana-url',
            type=str,
            default='http://localhost:5000',
            help='URL base do Grafana (default: http://localhost:5000)',
        )
        parser.add_argument(
            '--grafana-user',
            type=str,
            default='admin',
            help='Usuário do Grafana (default: admin)',
        )
        parser.add_argument(
            '--grafana-password',
            type=str,
            default='admin123',
            help='Senha do Grafana (default: admin123)',
        )

    def handle(self, *args, **kwargs):
        self.days = kwargs['days']
        self.clean_tsqmi = kwargs['clean_tsqmi']
        self.clean_all = kwargs['clean_all']
        repo_filter = [r.strip() for r in kwargs['repos'].split(',') if r.strip()]

        self.admin = User.objects.filter(is_superuser=True).first()
        if not self.admin:
            self.stderr.write('Nenhum superuser encontrado. Rode load_initial_data primeiro.')
            return

        self.end_date = timezone.now()
        self.start_date = self.end_date - dt.timedelta(days=self.days)

        repos = Repository.objects.all()
        if repo_filter:
            repos = repos.filter(name__in=repo_filter)

        # Limpeza global se solicitado
        if self.clean_all:
            self.stdout.write(self.style.WARNING('Limpando TODOS os dados de características calculadas...'))
            deleted = CalculatedCharacteristic.objects.filter(repository__in=repos).delete()
            self.stdout.write(f'  → {deleted[0]} características calculadas removidas')

            deleted_measures = CalculatedMeasure.objects.filter(repository__in=repos).delete()
            self.stdout.write(f'  → {deleted_measures[0]} medidas calculadas removidas')

            deleted_subchars = CalculatedSubCharacteristic.objects.filter(repository__in=repos).delete()
            self.stdout.write(f'  → {deleted_subchars[0]} subcaracterísticas calculadas removidas')

            deleted_metrics = CollectedMetric.objects.filter(repository__in=repos).delete()
            self.stdout.write(f'  → {deleted_metrics[0]} métricas coletadas removidas')
            self.stdout.write('')

        self.stdout.write(f'Populando {repos.count()} repositórios com {self.days} dias de histórico...')

        for repo in repos:
            profile = REPO_PROFILES.get(repo.name, 'stable')
            self.stdout.write(f'  → {repo.name} [{profile}]')
            self._seed_repo(repo, profile)

        self.stdout.write('')
        self._seed_goals_and_releases()

        self.stdout.write('')
        self._seed_grafana_panel(
            grafana_url=kwargs['grafana_url'],
            user=kwargs['grafana_user'],
            password=kwargs['grafana_password'],
        )

        self.stdout.write(self.style.SUCCESS('✓ seed_grafana concluído.'))

    # ------------------------------------------------------------------
    # Por repositório
    # ------------------------------------------------------------------

    def _seed_repo(self, repo: Repository, profile: str):
        # Gera timestamps para todo o período
        all_timestamps = _make_timestamps(self.days, self.end_date)

        # IMPORTANTE: Para o pulso ECG funcionar, características e TSQMI devem estar nas MESMAS datas
        # Seleciona 10 timestamps espaçados uniformemente para TSQMI e características
        TSQMI_MEASUREMENTS = 10
        step = max(1, len(all_timestamps) // TSQMI_MEASUREMENTS)
        tsqmi_timestamps = [all_timestamps[i * step] for i in range(TSQMI_MEASUREMENTS)]

        if self.clean_tsqmi:
            TSQMI.objects.filter(repository=repo).delete()

        self._seed_collected_metrics(repo, all_timestamps)
        self._seed_calculated_measures(repo, profile, all_timestamps)
        self._seed_calculated_subchars(repo, profile, all_timestamps)
        # Criar características APENAS nas datas dos TSQMIs (10 datas)
        self._seed_calculated_chars(repo, profile, tsqmi_timestamps)
        self._seed_tsqmi(repo, profile, tsqmi_timestamps)

    def _seed_collected_metrics(self, repo: Repository, timestamps: list):
        """
        Cria métricas coletadas por arquivo, um conjunto por dia.
        Gera ~10 arquivos por dia para ter distribuição estatística.
        """
        metrics = list(SupportedMetric.objects.all())
        if not metrics:
            return

        # Limita a geração de métricas de arquivo para não explodir o banco
        DAYS_TO_SEED = min(len(timestamps), 30)
        sampled_timestamps = timestamps[-DAYS_TO_SEED:]

        FILE_PATHS = [
            f'src/{module}/{fname}'
            for module in ['api', 'models', 'services', 'utils', 'tests']
            for fname in ['main.py', 'helper.py', 'core.py']
        ]

        to_create = []
        for ts in sampled_timestamps:
            for metric in metrics[:8]:  # métricas principais
                for path in random.sample(FILE_PATHS, k=min(8, len(FILE_PATHS))):
                    qualifier = 'FIL' if 'test' not in path else 'UTS'
                    to_create.append(CollectedMetric(
                        metric=metric,
                        value=random.uniform(0, 1) if metric.metric_type == 'PERCENT' else random.uniform(0, 100),
                        path=path,
                        qualifier=qualifier,
                        created_at=ts,
                        repository=repo,
                    ))

        if to_create:
            CollectedMetric.objects.bulk_create(to_create, batch_size=500, ignore_conflicts=False)
            self.stdout.write(f'    CollectedMetric: +{len(to_create)}')

    def _seed_calculated_measures(self, repo: Repository, profile: str, timestamps: list):
        measures = list(SupportedMeasure.objects.all())
        if not measures:
            return

        to_create = []
        for i, ts in enumerate(timestamps):
            for j, measure in enumerate(measures):
                offset = (j - len(measures) / 2) * 0.05
                to_create.append(CalculatedMeasure(
                    measure=measure,
                    value=_trend_value(i, profile, char_offset=offset),
                    created_at=ts,
                    repository=repo,
                ))

        CalculatedMeasure.objects.bulk_create(to_create, batch_size=1000)
        self.stdout.write(f'    CalculatedMeasure: +{len(to_create)}')

    def _seed_calculated_subchars(self, repo: Repository, profile: str, timestamps: list):
        subchars = list(SupportedSubCharacteristic.objects.all())
        if not subchars:
            return

        to_create = []
        for i, ts in enumerate(timestamps):
            for j, subchar in enumerate(subchars):
                offset = (j - len(subchars) / 2) * 0.04
                to_create.append(CalculatedSubCharacteristic(
                    subcharacteristic=subchar,
                    value=_trend_value(i, profile, char_offset=offset),
                    created_at=ts,
                    repository=repo,
                ))

        CalculatedSubCharacteristic.objects.bulk_create(to_create, batch_size=1000)
        self.stdout.write(f'    CalculatedSubChar: +{len(to_create)}')

    def _seed_calculated_chars(self, repo: Repository, profile: str, timestamps: list):
        """
        Cria características calculadas usando exatamente os timestamps fornecidos.

        IMPORTANTE: Os timestamps devem ser os mesmos usados para criar os TSQMIs,
        garantindo que o dashboard de pulso ECG funcione corretamente (sem valores NULL).
        """
        chars = list(SupportedCharacteristic.objects.all())
        if not chars:
            return

        # IMPORTANTE: Garantir que temos exatamente 3 características
        # Se não tivermos, o dashboard terá valores NULL
        if len(chars) != 3:
            self.stderr.write(
                f'AVISO: Esperado 3 características, mas encontrado {len(chars)}. '
                f'Isso pode causar valores NULL no dashboard!'
            )

        # Cada característica tem sua própria "personalidade" de tendência
        char_profiles = {
            'reliability':           ('improving', 0.0),
            'maintainability':       ('declining', 0.05),
            'functional_suitability': ('stable',   -0.05),
        }

        to_create = []
        for i, ts in enumerate(timestamps):
            # Usar índice proporcional para manter a progressão da tendência
            # Mapeia o índice atual para o intervalo completo de dias
            day_idx = int((i / len(timestamps)) * self.days)

            # Criar TODAS as características para CADA timestamp
            # Isso evita valores NULL no dashboard quando agrupamos por data
            for char in chars:
                sub_profile, offset = char_profiles.get(char.key, (profile, 0.0))
                to_create.append(CalculatedCharacteristic(
                    characteristic=char,
                    value=_trend_value(day_idx, sub_profile, char_offset=offset),
                    created_at=ts,
                    repository=repo,
                ))

        CalculatedCharacteristic.objects.bulk_create(to_create, batch_size=1000)
        expected = len(timestamps) * len(chars)
        actual = len(to_create)
        if expected != actual:
            self.stderr.write(
                f'AVISO: Esperado criar {expected} registros ({len(timestamps)} datas × {len(chars)} chars), '
                f'mas criou {actual}!'
            )
        self.stdout.write(f'    CalculatedChar: +{len(to_create)} ({len(timestamps)} datas × {len(chars)} chars = PAREADO COM TSQMI)')

    def _seed_tsqmi(self, repo: Repository, profile: str, timestamps: list):
        """
        Cria TSQMIs usando exatamente os timestamps fornecidos.

        IMPORTANTE: Os timestamps devem ser os mesmos usados para criar as características
        calculadas, garantindo que o dashboard de pulso ECG funcione corretamente.
        """
        if self.clean_tsqmi:
            existing = 0
        else:
            existing = TSQMI.objects.filter(repository=repo).count()

        TSQMI_MEASUREMENTS = len(timestamps)  # Usar exatamente os timestamps fornecidos

        if existing >= TSQMI_MEASUREMENTS:
            self.stdout.write(f'    TSQMI: já tem {existing} registros, pulando')
            return

        to_create = []
        for i, ts in enumerate(timestamps):
            # Usar índice proporcional para manter a progressão da tendência
            # Mapeia o índice atual para o intervalo completo de dias
            day_idx = int((i / len(timestamps)) * self.days)
            to_create.append(TSQMI(
                value=_trend_value(day_idx, profile),
                created_at=ts,
                repository=repo,
            ))

        TSQMI.objects.bulk_create(to_create, batch_size=500)
        self.stdout.write(f'    TSQMI: +{len(to_create)} ({TSQMI_MEASUREMENTS} medições nas MESMAS datas das características)')

    # ------------------------------------------------------------------
    # Goals e Releases
    # ------------------------------------------------------------------

    def _seed_goals_and_releases(self):
        self.stdout.write('Criando Goals e Releases...')

        products = Product.objects.all()
        chars = list(SupportedCharacteristic.objects.values_list('key', flat=True))

        for product in products:
            pre_config = product.release_configuration.first()
            if not pre_config:
                continue

            # 4 releases trimestrais cobrindo os últimos `self.days` dias
            quarter = self.days // 4
            for q in range(4):
                start_at = self.end_date - dt.timedelta(days=self.days - q * quarter)
                end_at = start_at + dt.timedelta(days=quarter)
                release_name = f'v{2025 + q // 4}.{q % 4 + 1}.0'

                # Goal com pesos aleatórios para este release
                goal_data = self._build_goal_data(pre_config)
                goal = Goal.objects.create(
                    data=goal_data,
                    created_by=self.admin,
                    product=product,
                )

                Release.objects.get_or_create(
                    release_name=release_name,
                    product=product,
                    defaults=dict(
                        start_at=start_at,
                        end_at=end_at,
                        created_by=self.admin,
                        goal=goal,
                        description=f'Release trimestral {release_name} do produto {product.name}',
                    ),
                )

        goals_count = Goal.objects.count()
        releases_count = Release.objects.count()
        self.stdout.write(f'  Goals: {goals_count}  |  Releases: {releases_count}')

    def _build_goal_data(self, pre_config: ReleaseConfiguration) -> dict:
        """Gera um dicionário de pesos aleatórios válido para o equalizador."""
        from goals.models import Equalizer

        chars_keys = pre_config.get_characteristics_keys()
        equalizer = Equalizer(chars_keys)

        # Aplica entre 3 e 8 mudanças aleatórias de delta
        for _ in range(random.randint(3, 8)):
            key = random.choice(chars_keys)
            delta = random.randint(-20, 20)
            try:
                equalizer.update(key, delta)
            except Exception:
                pass

        return equalizer.get_goal()

    # ------------------------------------------------------------------
    # Painel Grafana — Planejado vs Realizado (ECharts)
    # ------------------------------------------------------------------

    _ECHARTS_GET_OPTION = r"""
try {
  const series = context.panel.data.series;
  if (!series || series.length === 0) {
    return { title: { text: 'Sem dados', left: 'center', top: 'center' } };
  }

  const frame = series[0];

  function toArr(field) {
    if (!field) return [];
    const v = field.values;
    if (!v) return [];
    if (v.buffer) return Array.from(new Float64Array(v.buffer));
    if (Array.isArray(v)) return v;
    if (typeof v.toArray === 'function') return v.toArray();
    return Array.from(v);
  }

  const chars = toArr(frame.fields[0]);
  const plan  = toArr(frame.fields[1]);
  const real  = toArr(frame.fields[2]);
  const disp  = toArr(frame.fields[3]);

  const rc    = plan.map((v, i) => +Math.max(0, v - real[i]).toFixed(3));
  const rdiff = plan.map((v, i) => +(v - real[i]).toFixed(3));

  const fmt = arr => '[ ' + arr.map(v => v.toFixed(2)).join(' | ') + ' ]';

  const realLow = real.map((v, i) => +Math.max(0, v - disp[i]).toFixed(3));
  const band    = real.map((v, i) => +Math.min(1, (v + disp[i]) - Math.max(0, v - disp[i])).toFixed(3));

  return {
    grid: { left: '18%', right: '18%', bottom: '42%', containLabel: true },
    legend: { data: ['Planejado', 'Realizado', 'Dispersão'], top: 0 },
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: chars,
      axisLabel: {
        interval: 0,
        formatter: function(value) { return value.split(' ').join('\n'); }
      }
    },
    yAxis: { type: 'value', min: 0, max: 1 },
    series: [
      {
        name: 'Dispersão', type: 'line', smooth: true, symbol: 'none',
        stack: 'disp', data: realLow,
        lineStyle: { opacity: 0 }, areaStyle: { color: 'transparent' }
      },
      {
        name: 'Dispersão', type: 'line', smooth: true, symbol: 'none',
        stack: 'disp', data: band,
        lineStyle: { opacity: 0 },
        areaStyle: { color: 'rgba(255, 140, 0, 0.18)' }
      },
      {
        name: 'Planejado', type: 'line', smooth: true,
        symbol: 'circle', symbolSize: 6, z: 3,
        lineStyle: { color: '#1F60C4', width: 3 },
        itemStyle: { color: '#1F60C4' },
        data: plan
      },
      {
        name: 'Realizado', type: 'line', smooth: true,
        symbol: 'circle', symbolSize: 6, z: 3,
        lineStyle: { color: '#FF8C00', width: 3 },
        itemStyle: { color: '#FF8C00' },
        data: real
      }
    ],
    graphic: [
      {
        type: 'text', bottom: 130, left: 'center',
        style: { text: '⃗Rp = ' + fmt(plan), fill: '#1F60C4', fontSize: 13, fontWeight: 'bold', fontFamily: 'monospace' }
      },
      {
        type: 'text', bottom: 100, left: 'center',
        style: { text: '⃗Rd = ' + fmt(real), fill: '#FF8C00', fontSize: 13, fontWeight: 'bold', fontFamily: 'monospace' }
      },
      {
        type: 'text', bottom: 65, left: 'center',
        style: { text: '⃗Rc = ' + fmt(rc) + '  ← max(0, Rp−Rd)', fill: '#999', fontSize: 12, fontWeight: 'bold', fontFamily: 'monospace' }
      },
      {
        type: 'text', bottom: 35, left: 'center',
        style: { text: 'Rp−Rd = ' + fmt(rdiff) + '  ← bruto', fill: '#666', fontSize: 12, fontFamily: 'monospace' }
      }
    ]
  };
} catch(e) {
  return { title: { text: 'Erro: ' + e.message, left: 'center', top: 'center' } };
}
"""

    _PANEL_SQL = """WITH realizados AS (
    SELECT sc.name AS char_name, sc.key AS char_key,
           ROUND(AVG(cc.value)::numeric, 3)    AS realizado,
           ROUND(STDDEV(cc.value)::numeric, 3) AS dispersao
    FROM characteristics_calculatedcharacteristic cc
    JOIN characteristics_supportedcharacteristic sc ON sc.id = cc.characteristic_id
    WHERE cc.created_at >= NOW() - INTERVAL '7 days'
    GROUP BY sc.name, sc.key
),
planejados AS (
    SELECT elem.key AS char_key,
           ROUND((elem.value::numeric / 100), 3) AS planejado
    FROM goals_goal g
    CROSS JOIN LATERAL jsonb_each_text(g.data::jsonb) AS elem(key, value)
    WHERE g.id = (SELECT id FROM goals_goal ORDER BY created_at DESC LIMIT 1)
)
SELECT r.char_name                AS char_name,
       COALESCE(p.planejado, 0.5) AS planejado,
       r.realizado                AS realizado,
       COALESCE(r.dispersao, 0)   AS dispersao
FROM realizados r
LEFT JOIN planejados p ON p.char_key = r.char_key
ORDER BY r.char_name"""

    def _seed_grafana_panel(self, grafana_url: str, user: str, password: str):
        """Cria ou atualiza o painel ECharts no dashboard '1. Visão Geral de Qualidade'."""
        import base64
        self.stdout.write('Atualizando painel Grafana (Planejado vs Realizado)...')

        auth = base64.b64encode(f'{user}:{password}'.encode()).decode()
        headers = {'Authorization': f'Basic {auth}', 'Content-Type': 'application/json'}

        def grafana_get(path):
            req = urllib.request.Request(f'{grafana_url}{path}', headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=5) as r:
                    return json.load(r)
            except urllib.error.URLError as exc:
                self.stderr.write(f'  Grafana inacessível ({exc}). Pulando atualização do painel.')
                return None

        def grafana_post(path, payload):
            data = json.dumps(payload).encode()
            req = urllib.request.Request(f'{grafana_url}{path}', data=data, headers=headers, method='POST')
            with urllib.request.urlopen(req, timeout=5) as r:
                return json.load(r)

        # UID fixo definido no provisioning (grafana/provisioning/datasources/measuresoftgram.yml)
        ds_uid = 'measuresoftgram-db'

        # Busca o dashboard pelo slug/tag measuresoftgram
        search = grafana_get('/api/search?tag=measuresoftgram&type=dash-db')
        if not search:
            self.stderr.write('  Nenhum dashboard com tag "measuresoftgram" encontrado.')
            return

        target = next((d for d in search if 'Visão Geral' in d.get('title', '')), None)
        if not target:
            self.stderr.write('  Dashboard "Visão Geral de Qualidade" não encontrado.')
            return

        raw = grafana_get(f'/api/dashboards/uid/{target["uid"]}')
        if not raw:
            return

        dashboard = raw['dashboard']

        new_panel = {
            'id': 8,
            'title': 'Planejado vs Realizado (por Característica)',
            'type': 'volkovlabs-echarts-panel',
            'gridPos': next(
                (p['gridPos'] for p in dashboard['panels'] if p.get('id') == 8),
                {'h': 16, 'w': 10, 'x': 8, 'y': 8},
            ),
            'fieldConfig': {'defaults': {}, 'overrides': []},
            'options': {
                'renderer': 'canvas',
                'getOption': self._ECHARTS_GET_OPTION,
            },
            'targets': [{
                'datasource': {'type': 'grafana-postgresql-datasource', 'uid': ds_uid},
                'format': 'table',
                'rawSql': self._PANEL_SQL,
                'refId': 'A',
            }],
        }

        dashboard['panels'] = [
            new_panel if p.get('id') == 8 else p
            for p in dashboard['panels']
        ]

        result = grafana_post('/api/dashboards/db', {
            'dashboard': dashboard,
            'folderId': 0,
            'overwrite': True,
            'message': 'seed_grafana: painel Planejado vs Realizado atualizado',
        })
        self.stdout.write(f'  Painel atualizado → versão {result.get("version")} ({result.get("status")})')
