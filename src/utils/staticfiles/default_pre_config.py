# flake8: noqa
# pylint: skip-file
DEFAULT_PRE_CONFIG = {
    'characteristics': [
        {
            'key': 'reliability',
            'weight': 34,
            'subcharacteristics': [
                {
                    'key': 'testing_status',
                    'weight': 50,
                    'measures': [
                        {
                            'key': 'passed_tests',
                            'weight': 33,
                            'min_threshold': 0,
                            'max_threshold': 1,
                            'metrics': [
                                {'key': 'tests'},
                                {'key': 'test_failures'},
                                {'key': 'test_errors'},
                            ],
                        },
                        {
                            'key': 'test_builds',
                            'weight': 33,
                            'min_threshold': 0,
                            'max_threshold': 300000,
                            'metrics': [
                                {'key': 'test_execution_time'},
                                {'key': 'tests'},
                            ],
                        },
                        {
                            'key': 'test_coverage',
                            'weight': 34,
                            'min_threshold': 60,
                            'max_threshold': 100,
                            'metrics': [
                                {'key': 'coverage'},
                            ],
                        },
                    ],
                },
                {
                    "key": "maturity",
                    "weight": 50,
                    "measures": [
                        {
                            "key": "ci_feedback_time",
                            "weight": 100,
                            "min_threshold": 1,
                            "max_threshold": 900,
                            "metrics": [
                                {"key": "sum_ci_feedback_times"},
                                {"key": "total_builds"},
                            ],
                        }
                    ],
                },
            ],
        },
        {
            'key': 'maintainability',
            'weight': 33,
            'subcharacteristics': [
                {
                    'key': 'modifiability',
                    'weight': 100,
                    'measures': [
                        {
                            'key': 'non_complex_file_density',
                            'weight': 33,
                            'min_threshold': 0,
                            'max_threshold': 10,
                            'metrics': [
                                {'key': 'functions'},
                                {'key': 'complexity'},
                            ],
                        },
                        {
                            'key': 'commented_file_density',
                            'weight': 33,
                            'min_threshold': 10,
                            'max_threshold': 30,
                            'metrics': [
                                {'key': 'comment_lines_density'},
                            ],
                        },
                        {
                            'key': 'duplication_absense',
                            'weight': 34,
                            'min_threshold': 0,
                            'max_threshold': 5,
                            'metrics': [
                                {'key': 'duplicated_lines_density'},
                            ],
                        },
                    ],
                }
            ],
        },
        {
            "key": "functional_suitability",
            "weight": 33,
            "subcharacteristics": [
                {
                    "key": "functional_completeness",
                    "weight": 100,
                    "measures": [
                        {
                            "key": "team_throughput",
                            "weight": 100,
                            "min_threshold": 45,
                            "max_threshold": 100,
                            "metrics": [
                                {"key": "total_issues"},
                                {"key": "resolved_issues"},
                            ],
                        },
                    ],
                }
            ],
        },
    ]
}
