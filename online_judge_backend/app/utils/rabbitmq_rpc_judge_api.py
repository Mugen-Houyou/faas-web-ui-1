import asyncio
import json
import os
import uuid

from pathlib import Path
from dotenv import load_dotenv
import aio_pika
from typing import Callable, Awaitable, Dict

# Load ../.env relative to this file so it works regardless of cwd
env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=env_path, override=False)


class RpcClient:
    def __init__(self, url: str):
        self.url = url
        self.connection: aio_pika.RobustConnection | None = None
        self.channel: aio_pika.abc.AbstractChannel | None = None
        self.callback_queue: aio_pika.abc.AbstractQueue | None = None
        self.futures: dict[str, asyncio.Future] = {}
        self.callbacks: Dict[str, Callable[[dict], Awaitable[None]]] = {}

    async def connect(self) -> None:
        self.connection = await aio_pika.connect_robust(self.url)
        self.channel = await self.connection.channel()
        self.callback_queue = await self.channel.declare_queue(exclusive=True)
        await self.callback_queue.consume(self._on_response)

    async def close(self) -> None:
        if self.channel:
            await self.channel.close()
        if self.connection:
            await self.connection.close()

    async def _on_response(self, message: aio_pika.IncomingMessage) -> None:
        """Handle RPC responses from the worker and acknowledge them."""
        correlation_id = message.correlation_id
        if correlation_id and correlation_id in self.futures:
            future = self.futures.pop(correlation_id)
            future.set_result(message.body)
        elif correlation_id and correlation_id in self.callbacks:
            callback = self.callbacks.pop(correlation_id)
            await callback(json.loads(message.body))
        await message.ack()

    async def call(self, payload: dict) -> dict:
        if not self.channel or not self.callback_queue:
            raise RuntimeError("RPC client is not connected")
        correlation_id = str(uuid.uuid4())
        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self.futures[correlation_id] = future
        message = aio_pika.Message(
            body=json.dumps(payload).encode(),
            correlation_id=correlation_id,
            reply_to=self.callback_queue.name,
        )
        await self.channel.default_exchange.publish(message, routing_key="execute")
        body = await future
        return json.loads(body)

    async def send(self, payload: dict, on_response: Callable[[dict], Awaitable[None]] | None = None) -> str:
        """Publish a request and optionally register a callback for the response."""
        if not self.channel or not self.callback_queue:
            raise RuntimeError("RPC client is not connected")
        correlation_id = str(uuid.uuid4())
        if on_response:
            self.callbacks[correlation_id] = on_response
        message = aio_pika.Message(
            body=json.dumps(payload).encode(),
            correlation_id=correlation_id,
            reply_to=self.callback_queue.name,
        )
        await self.channel.default_exchange.publish(message, routing_key="execute")
        return correlation_id


async def get_rpc_client() -> RpcClient:
    url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost/")
    client = RpcClient(url)
    await client.connect()
    return client
