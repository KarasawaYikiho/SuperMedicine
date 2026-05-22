from core.event_bus import EventBus

class TestEventBus:
    def test_subscribe_and_publish(self):
        bus = EventBus()
        received = []
        bus.subscribe("test.topic", lambda e: received.append(e))
        bus.publish("test.topic", {"data": "hello"})
        assert len(received) == 1 and received[0]["data"] == "hello"
    def test_multiple_subscribers(self):
        bus = EventBus()
        a, b = [], []
        bus.subscribe("t", lambda e: a.append(e))
        bus.subscribe("t", lambda e: b.append(e))
        bus.publish("t", {"data": "x"})
        assert len(a) == 1 and len(b) == 1
    def test_unsubscribe(self):
        bus = EventBus()
        received = []
        token = bus.subscribe("t", lambda e: received.append(e))
        bus.unsubscribe(token)
        bus.publish("t", {"data": "x"})
        assert len(received) == 0
