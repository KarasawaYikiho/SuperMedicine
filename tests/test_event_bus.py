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

    def test_handler_exception_isolation(self):
        """验证一个 Handler 异常不影响其他 Handler"""
        bus = EventBus()
        received = []

        def good_handler(event):
            received.append("good")

        def bad_handler(event):
            raise RuntimeError("Handler Error")

        bus.subscribe("test", good_handler)
        bus.subscribe("test", bad_handler)
        bus.subscribe("test", good_handler)

        bus.publish("test", {"data": 1})
        assert len(received) == 2
