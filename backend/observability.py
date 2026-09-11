"""Opt-in, metadata-only tracing. Telemetry failures cannot fail user work."""
import logging
import time
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class Telemetry:
    def __init__(self, settings):
        self.client = None
        if settings.langfuse_enabled:
            try:
                from langfuse import Langfuse
                self.client = Langfuse(public_key=settings.langfuse_public_key,
                                       secret_key=settings.langfuse_secret_key,
                                       base_url=settings.langfuse_base_url, timeout=3)
            except Exception:
                logger.warning('telemetry_initialization_failed')

    @contextmanager
    def span(self, name, metadata=None):
        context, observation = None, None
        started = time.monotonic()
        try:
            if self.client:
                context = self.client.start_as_current_observation(name=name, metadata=metadata or {})
                observation = context.__enter__()
        except Exception:
            logger.warning('telemetry_start_failed')
            context = None
        try:
            yield observation
        finally:
            if context:
                try:
                    observation.update(metadata={**(metadata or {}), 'elapsed_ms': round((time.monotonic() - started) * 1000)})
                    context.__exit__(None, None, None)
                except Exception:
                    logger.warning('telemetry_finish_failed')

    def usage(self, observation, response):
        if observation is None:
            return
        try:
            usage = getattr(response, 'usage', None)
            observation.update(metadata={'usage': usage.model_dump() if usage else None,
                                         'usage_status': 'reported' if usage else 'unknown',
                                         'cost_status': 'unverified'})
        except Exception:
            logger.warning('telemetry_usage_failed')

    def flush(self):
        if self.client:
            try:
                self.client.flush()
            except Exception:
                logger.warning('telemetry_flush_failed')
