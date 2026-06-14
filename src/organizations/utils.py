import logging
import requests
from django.conf import settings
from math_model.services import MathModelServices
from release_configuration.serializers import ReleaseConfigurationSerializer
from math_model.utils import parse_release_configuration
from release_configuration.models import ReleaseConfiguration
from utils import staticfiles
from characteristics.models import CalculatedCharacteristic
from measures.models import CalculatedMeasure
from metrics.models import CollectedMetric
from subcharacteristics.models import CalculatedSubCharacteristic
from tsqmi.models import TSQMI

logger = logging.getLogger(__name__)

def get_default_mock_payload():
    return {
        'github': {
            'metrics': [
                {'name': 'total_issues', 'value': 1},
                {'name': 'resolved_issues', 'value': 0},
                {'name': 'sum_ci_feedback_times', 'value': 1},
                {'name': 'total_builds', 'value': 1},
            ],
        },
        'sonarqube': {
            'components': [
                {
                    'qualifier': 'FIL',
                    'path': 'src/foo.py',
                    'measures': [
                        {'metric': 'coverage', 'value': 0.0},
                        {'metric': 'complexity', 'value': 1},
                        {'metric': 'functions', 'value': 1},
                        {'metric': 'comment_lines_density', 'value': 0.0},
                        {'metric': 'duplicated_lines_density', 'value': 0.0},
                        {'metric': 'ncloc', 'value': 1},
                    ],
                },
                {
                    'qualifier': 'FIL',
                    'path': 'src/bar.py',
                    'measures': [
                        {'metric': 'coverage', 'value': 0.0},
                        {'metric': 'complexity', 'value': 1},
                        {'metric': 'functions', 'value': 1},
                        {'metric': 'comment_lines_density', 'value': 0.0},
                        {'metric': 'duplicated_lines_density', 'value': 0.0},
                        {'metric': 'ncloc', 'value': 1},
                    ],
                },
                {
                    'qualifier': 'UTS',
                    'path': 'tests/foo_test.py',
                    'measures': [
                        {'metric': 'tests', 'value': 1},
                        {'metric': 'test_execution_time', 'value': 1},
                    ],
                },
                {
                    'qualifier': 'UTS',
                    'path': 'tests/bar_test.py',
                    'measures': [
                        {'metric': 'tests', 'value': 1},
                        {'metric': 'test_execution_time', 'value': 1},
                    ],
                },
                {
                    'qualifier': 'TRK',
                    'path': '',
                    'measures': [
                        {'metric': 'test_failures', 'value': 0},
                        {'metric': 'test_errors', 'value': 0},
                    ],
                },
            ],
        },
    }

def onboard_repository_async(repository, user):
    token = getattr(user, 'github_access_token', None)
    repo_full_name = repository.github_full_name

    has_triggered_workflow = False

    if token and repo_full_name:
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        # 1. Fetch repository workflows
        url_workflows = f"https://api.github.com/repos/{repo_full_name}/actions/workflows"
        try:
            r = requests.get(url_workflows, headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json()
                workflows = data.get("workflows", [])
                
                # Find any workflow file
                if workflows:
                    selected_workflow = None
                    for wf in workflows:
                        name_lower = wf.get("name", "").lower()
                        if "measure" in name_lower or "sonar" in name_lower:
                            selected_workflow = wf
                            break
                    if not selected_workflow:
                        selected_workflow = workflows[0]
                    
                    wf_id = selected_workflow["id"]
                    
                    # Get repository default branch
                    r_repo = requests.get(f"https://api.github.com/repos/{repo_full_name}", headers=headers, timeout=10)
                    default_branch = "main"
                    if r_repo.status_code == 200:
                        default_branch = r_repo.json().get("default_branch", "main")
                    
                    # 2. Trigger workflow dispatch
                    url_trigger = f"https://api.github.com/repos/{repo_full_name}/actions/workflows/{wf_id}/dispatches"
                    r_dispatch = requests.post(
                        url_trigger,
                        headers=headers,
                        json={"ref": default_branch},
                        timeout=10
                    )
                    
                    if r_dispatch.status_code == 204:
                        logger.info(f"Successfully triggered workflow dispatch for {repo_full_name}")
                        has_triggered_workflow = True
        except Exception as exc:
            logger.error(f"Error checking/triggering GitHub Actions for {repo_full_name}: {exc}")

    if not has_triggered_workflow:
        logger.info(f"No GitHub Actions triggered. Generating mock metrics for {repository.name}...")
        try:
            product = repository.product
            release_configuration, _ = ReleaseConfiguration.objects.get_or_create(
                name='Default pre-config',
                product=product,
                defaults={
                    'data': staticfiles.DEFAULT_PRE_CONFIG,
                }
            )
            
            services = MathModelServices(repository, product)
            config_serializer = ReleaseConfigurationSerializer(release_configuration)
            char_keys, subchar_keys, measure_keys = parse_release_configuration(
                config_serializer.data,
            )

            mock_payload = get_default_mock_payload()
            collected_metrics = services.build_collected_metrics(mock_payload)
            measures, measure_values = services.build_calculated_measures(
                measure_keys, release_configuration, collected_metrics,
            )
            subchars, subchar_values = services.build_calculated_subcharacteristics(
                subchar_keys, release_configuration, measure_values,
            )
            chars, char_values = services.build_calculated_characteristics(
                char_keys, release_configuration, subchar_values,
            )
            tsqmi = services.build_tsqmi(release_configuration, char_values)

            services.persist_all(
                collected_metrics,
                measures,
                subchars,
                chars,
                tsqmi,
            )
            logger.info(f"Successfully populated mock math model calculations for {repository.name}")
        except Exception as exc:
            logger.error(f"Failed to populate mock calculations for {repository.name}: {exc}")
