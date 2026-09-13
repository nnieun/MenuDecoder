from unittest.mock import Mock
from backend.config import Settings
from backend.observability import Telemetry


def test_tracing_failure_does_not_skip_or_duplicate_work():
    telemetry = Telemetry(Settings(langfuse_enabled=False))
    telemetry.client = Mock()
    telemetry.client.start_as_current_observation.side_effect = RuntimeError('offline')
    performed = []
    with telemetry.span('step', {'version': 1}):
        performed.append(True)
    assert performed == [True]


def test_application_exception_is_not_swallowed():
    import pytest
    telemetry = Telemetry(Settings(langfuse_enabled=False))
    with pytest.raises(ValueError):
        with telemetry.span('step'):
            raise ValueError('failure')
