# flake8: noqa
# pylint: skip-file
SONARQUBE_AVAILABLE_METRICS = [
    {
        'key': 'functions', 
        'metric_type': 'FLOAT', 
        'name': 'number of functions'
    },
    {
        'key': 'test_execution_time', 
        'metric_type': 'FLOAT', 
        'name': 'average time to execute tests'
    },
    {
        'key': 'test_failures', 
        'metric_type': 'FLOAT', 
        'name': 'number of tests failuress'
    },
    {
        'key': 'test_errors', 
        'metric_type': 'FLOAT', 
        'name': 'number of tests errors'
    },
    {
        'key': 'security_rating', 
        'metric_type': 'FLOAT', 
        'name': 'rating of security'
    },
    {
        'key': 'tests', 
        'metric_type': 'FLOAT', 
        'name': 'Tests'
    },
    {
        'key': 'files', 
        'metric_type': 'FLOAT', 
        'name': 'Files'
    },
    {
        'key': 'complexity', 
        'metric_type': 'FLOAT', 
        'name': 'Cyclomatic Complexity'
    },
    {
        'key': 'ncloc', 
        'metric_type': 'FLOAT', 
        'name': 'Lines of Code'
    },
    {
        'key': 'coverage', 
        'metric_type': 'FLOAT', 
        'name': 'Coverage'
    },
    {
        'key': 'reliability_rating', 
        'metric_type': 'FLOAT', 
        'name': 'Reliabiity Rating'
    },
    {
        'key': 'comment_lines_density',
        'metric_type': 'FLOAT', 
        'name': 'Comments (%)'
    },
    {
        'key': 'test_success_density', 
        'metric_type': 'FLOAT', 
        'name': 'Test Success Density'
    }, 
    {
        'key': 'duplicated_lines_density', 
        'metric_type': 'FLOAT', 
        'name': 'Duplicated lines density'
    }
]
                