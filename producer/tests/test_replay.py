import json
from producer import replay

def make_event(index, minute, second, period=1, team="Argentina"):
    return {"index": index, "minute": minute, "second": second,
            "period": period, "possession_team": {"name": team},
            "type": {"name": "Pass"}}

def test_match_seconds_is_cumulative():
    assert replay.match_seconds(make_event(1, 0, 0)) == 0
    assert replay.match_seconds(make_event(2, 1, 30)) == 90
    assert replay.match_seconds(make_event(3, 105, 10, period=4)) == 6310

def test_order_events_sorts_by_index():
    events = [make_event(3, 2, 0), make_event(1, 0, 0), make_event(2, 1, 0)]
    assert [e["index"] for e in replay.order_events(events)] == [1, 2, 3]

def test_replay_delays_first_is_zero_and_scaled():
    events = [make_event(1, 0, 0), make_event(2, 0, 10), make_event(3, 0, 70)]
    delays = list(replay.replay_delays(events, speed=10, max_sleep=100))
    assert delays[0] == 0.0
    assert delays[1] == 1.0
    assert delays[2] == 6.0

def test_replay_delays_are_capped():
    events = [make_event(1, 0, 0), make_event(2, 45, 0)]
    delays = list(replay.replay_delays(events, speed=1, max_sleep=3))
    assert delays[1] == 3.0

class FakeProducer:
    def __init__(self): self.messages = []; self.flushed = False
    def produce(self, topic, key, value): self.messages.append((topic, key, value))
    def poll(self, _): pass
    def flush(self): self.flushed = True

def test_stream_match_emits_all_in_order():
    events = [make_event(3, 2, 0), make_event(1, 0, 0), make_event(2, 1, 0)]
    fake = FakeProducer()
    count = replay.stream_match(events, producer=fake, topic="t",
                                speed=1000, sleep_fn=lambda _: None)
    assert count == 3
    assert fake.flushed
    indexes = [json.loads(v)["index"] for _, _, v in fake.messages]
    assert indexes == [1, 2, 3]
