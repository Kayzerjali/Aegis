"""Default configuration values for Aegis projects."""

DEFAULT_CONFIG = {
    "engines": {
        "default": "mock",
        "planning_advisor": "mock",
        "test_agent": "mock",
        "impl_agent": "mock",
        "debug_agent": "mock",
        "fresh_agent": "mock",
        "code_reviewer": "mock",
        "doc_generator": "mock",
    },
    "loop_limits": {
        "debug_retries": 3,
        "mutation_rounds": 3,
        "readiness_attempts": 3,
        "fresh_agent_attempts": 2,
    },
    "thresholds": {
        "mutation_score": 0.8,
    },
}

_DEFAULT_LOOP_LIMIT_FALLBACK = 3
