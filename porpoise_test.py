from datetime import datetime

import pytest

from porpoise import Analytics, hourrange, dayrange, weekrange, minuterange


@pytest.fixture(scope='module')
def redis(request):
    import redis
    r = redis.Redis(db=9)
    assert not r.keys(), 'Expected DB slot 9 to be empty for testing'
    request.addfinalizer(lambda: r.flushdb())
    return r


def test_dayrange():
    start = datetime(2013, 1, 1)
    end = datetime(2013, 1, 5)
    assert map(str, dayrange(start, end)) == ['20130101', '20130102', '20130103', '20130104']


def test_weekrange():
    start = datetime(2013, 1, 1)
    assert map(str, weekrange(start)) == ['20130101', '20130102', '20130103', '20130104', '20130105', '20130106', '20130107']


def test_hourrange():
    start = datetime(2013, 1, 1, 0, 0)
    end = datetime(2013, 1, 1, 4, 0)
    assert map(str, hourrange(start, end)) == ['2013010100', '2013010101', '2013010102', '2013010103']


def test_minuterange():
    pass


def test_analytics(redis):
    analytics = Analytics(redis)
    period = hourrange(-48)
    ids = [1, 4, 5, 6, 7, 20]
    for m in period:
        for id in ids:
            analytics.event('active', id, time=m.dt)
