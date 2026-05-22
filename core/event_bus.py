"""消息总线"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable
from uuid import uuid4

@dataclass
class Subscription:
    token: str
    topic: str
    handler: Callable[[dict[str, Any]], None]

class EventBus:
    def __init__(self):
        self._subscriptions: dict[str, list[Subscription]] = {}
        self._token_map: dict[str, Subscription] = {}
    def subscribe(self, topic: str, handler: Callable[[dict[str, Any]], None]) -> str:
        token = str(uuid4())
        sub = Subscription(token=token, topic=topic, handler=handler)
        if topic not in self._subscriptions:
            self._subscriptions[topic] = []
        self._subscriptions[topic].append(sub)
        self._token_map[token] = sub
        return token
    def unsubscribe(self, token: str) -> None:
        sub = self._token_map.pop(token, None)
        if sub and sub.topic in self._subscriptions:
            self._subscriptions[sub.topic] = [s for s in self._subscriptions[sub.topic] if s.token != token]
    def publish(self, topic: str, event: dict[str, Any]) -> None:
        for sub in self._subscriptions.get(topic, []):
            sub.handler(event)
