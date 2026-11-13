"""
Celery application factory.

Configures Celery with Redis broker/backend, task routing,
and beat schedule for periodic tasks.
"""

from __future__ import annotations

from celery import Celery
from celery.signals import worker_ready, worker_shutdown
from kombu import Exchange, Queue

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger

logger = get_logger(__name__, component="celery")


def create_celery_app() -> Celery:
    """Create and configure the Celery application."""
    settings = get_settings()
    celery_cfg = settings.celery

    app = Celery(
        "enterpriseit_rag",
        include=["app.workers.tasks.ingestion_tasks"],
    )

    # ── Broker / Backend ─────────────────────────────────────────────────────
    app.conf.broker_url = celery_cfg.broker_url
    app.conf.result_backend = celery_cfg.result_backend

    # ── Serialization ─────────────────────────────────────────────────────────
    app.conf.task_serializer = celery_cfg.task_serializer
    app.conf.result_serializer = celery_cfg.result_serializer
    app.conf.accept_content = ["json"]
    app.conf.result_accept_content = ["json"]

    # ── Task Timeouts ─────────────────────────────────────────────────────────
    app.conf.task_time_limit = celery_cfg.task_time_limit
    app.conf.task_soft_time_limit = celery_cfg.task_soft_time_limit

    # ── Concurrency ───────────────────────────────────────────────────────────
    app.conf.worker_prefetch_multiplier = 1   # Fair scheduling
    app.conf.task_acks_late = True            # Acknowledge after completion
    app.conf.worker_max_tasks_per_child = 100  # Prevent memory leaks

    # ── Queues ────────────────────────────────────────────────────────────────
    default_exchange = Exchange("default", type="direct")
    ingestion_exchange = Exchange("ingestion", type="direct")
    evaluation_exchange = Exchange("evaluation", type="direct")

    app.conf.task_queues = (
        Queue("default", default_exchange, routing_key="default"),
        Queue("ingestion", ingestion_exchange, routing_key="ingestion"),
        Queue("evaluation", evaluation_exchange, routing_key="evaluation"),
    )
    app.conf.task_default_queue = "default"
    app.conf.task_default_exchange = "default"
    app.conf.task_default_routing_key = "default"

    # ── Task Routing ──────────────────────────────────────────────────────────
    app.conf.task_routes = {
        "app.workers.tasks.ingestion_tasks.*": {"queue": "ingestion"},
        "app.workers.tasks.evaluation_tasks.*": {"queue": "evaluation"},
    }

    # ── Result Expiry ─────────────────────────────────────────────────────────
    app.conf.result_expires = 86400  # 24 hours

    # ── Beat Schedule (periodic tasks) ───────────────────────────────────────
    app.conf.beat_schedule = {
        "cleanup-stale-jobs": {
            "task": "app.workers.tasks.ingestion_tasks.cleanup_stale_jobs",
            "schedule": 3600.0,  # Every hour
        },
    }

    return app


# Singleton Celery app instance
celery_app = create_celery_app()


@worker_ready.connect
def on_worker_ready(**kwargs) -> None:
    """Called when Celery worker starts."""
    settings = get_settings()
    configure_logging(
        log_level=settings.app.app_log_level,
        is_production=settings.app.is_production,
    )
    logger.info("celery_worker_ready")


@worker_shutdown.connect
def on_worker_shutdown(**kwargs) -> None:
    """Called when Celery worker shuts down."""
    logger.info("celery_worker_shutdown")
