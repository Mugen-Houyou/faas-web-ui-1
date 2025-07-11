import asyncio
import json
import os

from pathlib import Path
import time
from dotenv import load_dotenv
import aio_pika
import logging
from prometheus_client import Counter, Histogram, start_http_server

# Load ../.env relative to this file so it works regardless of cwd
env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=env_path, override=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("worker")

JOB_COUNT = Counter('worker_jobs_total', 'Total jobs processed', ['result'])
JOB_DURATION = Histogram('worker_job_duration_seconds', 'Job processing time')

from .executor import execute_code_multiple, SupportedLanguage


async def main() -> None:
    start_http_server(8001)
    url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost/")
    logger.info("Connecting to RabbitMQ at %s ...", url)
    connection = await aio_pika.connect_robust(url)
    channel = await connection.channel()
    queue = await channel.declare_queue("execute", durable=True)

    logger.info("Connected to RabbitMQ. Waiting for messages...")
    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            async with message.process():
                data = None
                start_time = time.perf_counter()
                try:
                    data = json.loads(message.body)

                    logger.info("Received message: %s", data)
                    async def progress_cb(res, idx):
                        await channel.default_exchange.publish(
                            aio_pika.Message(
                                body=json.dumps({
                                    "type": "progress",
                                    "index": idx,
                                    "result": res.model_dump(),
                                }).encode(),
                                correlation_id=message.correlation_id,
                            ),
                            routing_key="progress",
                        )

                    time.sleep(1)
                    results = await execute_code_multiple(
                        lang=SupportedLanguage(data["language"]),
                        code=data["code"],
                        stdins=data.get("stdins", []),
                        time_limit=data.get("timeLimit", 30000),
                        memory_limit=data.get("memoryLimit", 256),
                        token=data.get("token"),
                        expected=data.get("expected"),
                        early_stop=data.get("earlyStop", False),
                        progress_cb=progress_cb,
                        wall_time_limit=data.get("wallTimeLimit"),
                    )
                    response = [r.model_dump() for r in results]
                    await channel.default_exchange.publish(
                        aio_pika.Message(
                            body=json.dumps({"type": "final", "results": response}).encode(),
                            correlation_id=message.correlation_id,
                        ),
                        routing_key="progress",
                    )
                    JOB_COUNT.labels(result="success").inc()
                except Exception as e:
                    response = {"error": str(e)}
                    await channel.default_exchange.publish(
                        aio_pika.Message(
                            body=json.dumps({
                                "type": "final",
                                "results": [],
                                "error": str(e),
                            }).encode(),
                            correlation_id=message.correlation_id,
                        ),
                        routing_key="progress",
                    )
                    JOB_COUNT.labels(result="error").inc()
                
                await channel.default_exchange.publish(
                    aio_pika.Message(
                        body=json.dumps(response).encode(),
                        correlation_id=message.correlation_id,
                    ),
                    routing_key=message.reply_to,
                )
                JOB_DURATION.observe(time.perf_counter() - start_time)
                logger.info("Processed message: %s", data)


if __name__ == "__main__":
    asyncio.run(main())
