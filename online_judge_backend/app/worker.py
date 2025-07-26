import asyncio
import json
import os
import time
from pathlib import Path
from dotenv import load_dotenv
import aio_pika
from .utils.logging_middleware_worker import (
    logger,
    start_metrics_server,
    JOB_COUNT,
    JOB_DURATION,
)

# Load ../.env relative to this file so it works regardless of cwd
env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=env_path, override=True)

from .executor import execute_code_multiple, SupportedLanguage


async def main() -> None:
    start_metrics_server()
    url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost/")
    logger.info("Connecting to RabbitMQ at %s ...", url)
    connection = await aio_pika.connect_robust(url)
    channel = await connection.channel()
    
    await channel.set_qos(prefetch_count=1)
    queue = await channel.declare_queue("execute", durable=True)

    logger.info("Connected to RabbitMQ. Waiting for messages...")
    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            async with message.process():
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

                    # 실제 실행 전 딜레이
                    # await asyncio.sleep(1) # TODO: 이건 나중에 적용합시다.
                    time.sleep(1)

                    results = await execute_code_multiple(
                        lang=SupportedLanguage(data["language"]),
                        code=data["code"],
                        stdins=data.get("stdins", []),
                        time_limit=int(data.get("timeLimit", 30000)*1.2),
                        memory_limit=data.get("memoryLimit", 256),
                        token=data.get("token"),
                        expected=data.get("expected"),
                        early_stop=data.get("earlyStop", False),
                        progress_cb=progress_cb,
                        wall_time_limit=int(data.get("wallTimeLimit")*1.2),
                    )

                    # 결과 처리
                    response = [r.model_dump() for r in results]

                    # 전체 테스트케이스를 다 돌았더라도, duration의 합산으로 time limit 초과 여부를 체크
                    durationTotal = sum(r.duration for r in results)
                    if durationTotal > data.get('timeLimit'):
                        response[-1]["timedOut"] = True

                    # 최종 결과 발행
                    await channel.default_exchange.publish(
                        aio_pika.Message(
                            body=json.dumps({"type": "final", "results": response}).encode(),
                            correlation_id=message.correlation_id,
                        ),
                        routing_key="progress",
                    )

                    JOB_COUNT.labels(result="success").inc()
                    logger.info("Job succeeded, results count: %d", len(results))

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
                    logger.error("Job failed: %s", e, exc_info=True)

                # reply queue로도 결과 전송
                await channel.default_exchange.publish(
                    aio_pika.Message(
                        body=json.dumps(response).encode(),
                        correlation_id=message.correlation_id,
                    ),
                    routing_key=message.reply_to,
                )

                duration = time.perf_counter() - start_time
                JOB_DURATION.observe(duration)
                logger.info("Processed message in %.3f seconds", duration)


if __name__ == "__main__":
    asyncio.run(main())
