from datetime import datetime

import pytest

from porpoise import Analytics, hourrange, dayrange, weekrange, bitset


TEST_REDIS_DB = 9


@pytest.fixture
def redis(request):
    import redis
    r = redis.Redis(db=TEST_REDIS_DB)
    assert not r.keys(), 'Expected DB slot %s to be empty for testing' % TEST_REDIS_DB
    request.addfinalizer(lambda: r.flushdb())
    return r


def test_dayrange():
    start = datetime(2013, 1, 1)
    end = datetime(2013, 1, 5)
    assert map(str, dayrange(start, end)) == ['20130101', '20130102', '20130103', '20130104']


def test_weekrange():
    start = datetime(2013, 1, 1)
    end = datetime(2013, 1, 7)
    assert map(str, weekrange(start, end)) == ['20130101', '20130102', '20130103', '20130104', '20130105', '20130106', '20130107']


def test_hourrange():
    start = datetime(2013, 1, 1, 0, 0)
    end = datetime(2013, 1, 1, 4, 0)
    assert map(str, hourrange(start, end)) == ['2013010100', '2013010101', '2013010102', '2013010103']
    assert len(list(hourrange(-4))) == 4


def test_minuterange():
    pass


def test_bitset():
    c = '\xc0\x80'
    b = bitset(c)
    assert 0 in b
    assert 1 in b
    for i in range(2, 8):
        assert i not in b
    assert 8 in b
    for i in range(9, 16):
        assert i not in b
    assert list(b) == [0, 1, 8]


def test_event_analysis(redis):
    analytics = Analytics(redis)
    period = hourrange(-4)
    event_ids = [('active', [1, 4, 5, 6, 7, 20]), ('played', [1, 5, 7])]
    for m in period:
        for key, ids in event_ids:
            for id in ids:
                analytics.event(key, id, time=m.dt)

    events = analytics.events

    analysis = events('active') & events('played')
    out = list(analysis(period))
    assert out == [set([1, 5, 7]), set([1, 5, 7]), set([1, 5, 7]), set([1, 5, 7])]


def test_counter_analysis(redis):
    analytics = Analytics(redis)
    period = hourrange(-4)
    counter_data = [('active', [2, 4, 0, 3]), ('played', [3, 4, 0, 1])]
    for key, ids in counter_data:
        for i, m in enumerate(period):
            for j in range(ids[i]):
                analytics.count(key, 1, time=m.dt)

    active = analytics.counters('active')
    assert list(active(period)) == [{'1': 2}, {'1': 4}, {}, {'1': 3}]

    played = analytics.counters('played')
    assert list(played(period)) == [{'1': 3}, {'1': 4}, {}, {'1': 1}]
