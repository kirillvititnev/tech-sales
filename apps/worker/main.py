import logging

from arq import cron
from arq.connections import RedisSettings

from apps.worker.config import get_worker_settings
from apps.worker.sync import run_parse_cycle

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("worker")


async def parse_supplier_channels(ctx: dict) -> None:
    logger.info("Starting supplier parse cycle (folder=Apple)")
    stats = await run_parse_cycle("Apple")
    logger.info("Parse cycle done: %s", stats)


async def startup(ctx: dict) -> None:
    settings = get_worker_settings()
    logger.info(
        "White Shop worker started (parse every %s min)",
        settings.parse_interval_minutes,
    )


async def shutdown(ctx: dict) -> None:
    logger.info("White Shop worker stopped")


def _redis_settings() -> RedisSettings:
    settings = get_worker_settings()
    return RedisSettings.from_dsn(settings.redis_url)


class WorkerSettings:
    functions = [parse_supplier_channels]
    cron_jobs = [
        cron(parse_supplier_channels, minute={0, 15, 30, 45}, run_at_startup=False)
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = _redis_settings()
