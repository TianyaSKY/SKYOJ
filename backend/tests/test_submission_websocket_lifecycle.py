"""Redis 等待不阻塞事件循环，订阅失败或断开时仍释放连接。"""

import asyncio
from threading import Event
import time
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from redis import ConnectionError

from app.api import submission


class Socket:
    def __init__(self):
        self.closed = []
        self.messages = []
        self.disconnected = asyncio.Event()

    async def accept(self):
        pass

    async def send_text(self, message):
        self.messages.append(message)

    async def close(self, code=1000, reason=''):
        self.closed.append(code)

    async def receive(self):
        await self.disconnected.wait()
        return {'type': 'websocket.disconnect'}


def setup_subscription(monkeypatch):
    monkeypatch.setattr(submission, 'get_current_auth', lambda **kw: SimpleNamespace(
        user=SimpleNamespace(id=1, role='student'),
    ))
    pubsub = MagicMock()
    pubsub.get_message.return_value = {'type': 'message', 'data': 'result'}
    client = MagicMock()
    client.pubsub.return_value = pubsub
    monkeypatch.setattr(submission.redis_client, 'get_client', lambda: client)
    return pubsub


def call_socket(socket):
    return submission.submission_websocket(socket, 1, 'token', db=object(), service=MagicMock())


def test_redis_wait_allows_other_coroutines_to_progress(monkeypatch):
    pubsub = setup_subscription(monkeypatch)
    released = Event()
    heartbeat_seen = []

    def blocking_read(**kwargs):
        heartbeat_seen.append(released.wait(0.3))
        return {'type': 'message', 'data': 'result'}

    pubsub.get_message.side_effect = blocking_read

    async def scenario():
        async def heartbeat():
            await asyncio.sleep(0.01)
            released.set()
        await asyncio.gather(call_socket(Socket()), heartbeat())

    asyncio.run(scenario())
    assert heartbeat_seen == [True]
    pubsub.close.assert_called_once()


@pytest.mark.parametrize('phase', ['subscribe', 'get_message'])
def test_redis_failure_closes_socket_and_subscription(monkeypatch, phase):
    pubsub = setup_subscription(monkeypatch)
    getattr(pubsub, phase).side_effect = ConnectionError('Redis 不可用')

    async def scenario():
        socket = Socket()
        await call_socket(socket)
        assert socket.closed == [1011]

    asyncio.run(scenario())
    pubsub.close.assert_called_once()


def test_unsubscribe_failure_does_not_skip_close(monkeypatch):
    pubsub = setup_subscription(monkeypatch)
    pubsub.unsubscribe.side_effect = ConnectionError('取消订阅失败')

    async def scenario():
        socket = Socket()
        await call_socket(socket)
        assert socket.messages == ['result']

    asyncio.run(scenario())
    pubsub.close.assert_called_once()


def test_client_disconnect_stops_waiting_and_releases_subscription(monkeypatch):
    pubsub = setup_subscription(monkeypatch)
    poll_started = Event()

    def poll(**kwargs):
        poll_started.set()
        time.sleep(0.01)
        return None

    pubsub.get_message.side_effect = poll

    async def scenario():
        socket = Socket()
        task = asyncio.create_task(call_socket(socket))
        while not poll_started.is_set():
            await asyncio.sleep(0.001)
        socket.disconnected.set()
        await asyncio.wait_for(task, timeout=1)
        assert socket.messages == []
        assert socket.closed == []

    asyncio.run(scenario())
    pubsub.close.assert_called_once()


def test_subscription_timeout_closes_and_releases_connection(monkeypatch):
    pubsub = setup_subscription(monkeypatch)

    def poll(**kwargs):
        time.sleep(0.01)
        return None

    pubsub.get_message.side_effect = poll
    original_timeout = submission.anyio.move_on_after
    requested_timeouts = []

    def short_timeout(seconds):
        requested_timeouts.append(seconds)
        return original_timeout(0.03)

    monkeypatch.setattr(submission.anyio, 'move_on_after', short_timeout)

    async def scenario():
        socket = Socket()
        await asyncio.wait_for(call_socket(socket), timeout=1)
        assert socket.closed == [1000]
        assert socket.messages == []

    asyncio.run(scenario())
    assert requested_timeouts == [300]
    pubsub.close.assert_called_once()
