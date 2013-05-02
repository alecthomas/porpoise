import uuid
from copy import deepcopy
from datetime import datetime, timedelta

import redis


"""Porpoise - A Redis-based analytics framework.

    >>> analytics = Analytics()

To add events:

    >>> analytics.event('login', user.id)
    >>> analytics.event('active', user.id)
    >>> analytics.event('song:played', user.id)

To add counters:

    >>> analytics.count('signups')
    >>> analytics.count('song:played', song.id)
    >>> analytics.count('invalid_login', user.id)

To analyse the data:

    >>> events = analytics.events

    >>> active = events('active')
    >>> period = dayrange(-30)
    >>> daily_active = active(period)

Another example, showing how to compute weekly user retention:

    >>> retention = active(weekrange(-1)) & active(weekrange(0))

Or to compute hourly active users for the last week:

    >>> hourly_active = active(hourrange(-7 * 24))

To perform analysis on counters. The following will return the daily signups
for the last 100 days:

    >>> counters = analytics.counters
    >>> signups = counters('signups')
j    >>> daily_signups = signups(dayrange(-100))

"""


RESOLUTION_MAP = {'m': '%Y%m', 'd': '%Y%m%d', 'H': '%Y%m%d%H', 'M': '%Y%m%d%H%M'}


class Analytics(object):
    def __init__(self, client=None, resolutions='dmH'):
        self.client = client or redis.Redis()
        self.resolutions = resolutions

    def _prepare(self, prefix, key, time, tx):
        if time is None:
            time = datetime.utcnow()
        elif isinstance(time, (int, float, long)):
            time = datetime.fromtimestamp(time)
        keys = ['%s.%s.%s' % (prefix, key, time.strftime(RESOLUTION_MAP[r])) for r in self.resolutions]
        tx = tx or self.client.pipeline()
        return keys, tx

    def event(self, key, id, time=None, tx=None):
        """Mark an event as having occurred with the associated ID (eg. user ID) at a time.

        :param key: A symbolic key.
        :param id: A numeric identifier.
        :param time: A datetime instance (or UNIX timestamp).
        """
        keys, tx = self._prepare('e', key, time, tx)
        for key in keys:
            tx.setbit(key, id, 1)
        tx.execute()

    def count(self, key, id, count=1, time=None, tx=None):
        """Increment a counter associated with a key (and optionally an ID).

        :param key: A symbolic key.
        :param id: An identifier.
        :param count: The increment.
        :param time: A datetime instance.
        """
        keys, tx = self._prepare('c', key, time, tx)
        for key in keys:
            tx.hincrby(key, id, count)
        tx.execute()

    def events(self, key):
        return EventMetric(self.client, key)

    def counters(self, key, id=None):
        return CounterMetric(self.client, key, id)


class CounterMetric(object):
    def __init__(self, client, key, id=None):
        self.client = client
        self.key = key
        self.id = id

    def __call__(self, period):
        for suffix in period:
            key = 'c.%s.%s' % (self.key, suffix)
            yield self._retrieve(key)

    def _retrieve(self, key):
        if self.id is None:
            values = self.client.hgetall(key)
            values = dict((k, int(v)) for k, v in values.iteritems())
            return values
        else:
            return self.client.hget(key, self.id)


class EventMetric(object):
    def __init__(self, client, left, op=None, right=None):
        self.client = client
        self.left = left
        self.op = op
        self.right = right

    def __call__(self, period):
        for moment in period:
            cleanup = []
            try:
                tx = self.client.pipeline()
                key = self._retrieve(moment, cleanup, tx)
                tx.execute()
                value = self.client.get(key)
                yield bitset(value)
            finally:
                self.client.delete(*cleanup)

    def _retrieve(self, moment, cleanup, tx):
        if self.op is None:
            left = 'e.%s.%s' % (self.left, moment)
            return left
        dest = 't.%s' % (uuid.uuid4(),)
        cleanup.append(dest)
        left = self.left._retrieve(moment, cleanup, tx)
        if self.right:
            right = self.right._retrieve(moment, cleanup, tx)
        if self.op == 'NOT':
            tx.bitop('NOT', dest, left)
        elif self.op == 'OR':
            tx.bitop('OR', dest, left, right)
        elif self.op == 'AND':
            tx.bitop('AND', dest, left, right)
        elif self.op == 'XOR':
            tx.bitop('XOR', dest, left, right)
        else:
            raise ValueError('invalid bitop %s' % self.op)
        return dest

    def __or__(self, other):
        return EventMetric(self.client, self, 'OR', other)

    def __and__(self, other):
        return EventMetric(self.client, self, 'AND', other)

    def __xor__(self, other):
        return EventMetric(self.client, self, 'XOR', other)

    def __invert__(self):
        return EventMetric(self.client, self, 'NOT')

    def __repr__(self):
        if self.op:
            if self.right:
                return '(%r %s %r)' % (self.left, self.op, self.right)
            return '%s %r' % (self.op, self.left)
        return 'EventMetric(%r)' % self.left


def bitset(value):
    bits = set()
    if value is None:
        return bits
    i = 0
    for c in value:
        for j in range(8):
            if ord(c) & (1 << (7 - j)):
                bits.add(i)
            i += 1
    return bits


class moment(object):
    def __init__(self, dt, fmt):
        self.dt = dt
        self.fmt = fmt

    def __str__(self):
        return self.dt.strftime(self.fmt)

    def __repr__(self):
        return '<moment %s>' % self


class _datetimerange(object):
    resolution = None

    def __init__(self, start=-1, end=0):
        now = datetime.utcnow()
        if isinstance(start, (long, int, float)):
            start = now + self._delta(start)
            if end is None:
                end = start + self._delta(1)
        if isinstance(end, (long, int, float)):
            end = now + self._delta(end)
        self.start = start
        self.end = end

    def __iter__(self):
        cursor = deepcopy(self.start)
        while cursor < self.end:
            for suffix in self._suffixes(cursor):
                yield suffix
            cursor += self._delta(1)

    def _suffixes(self, t):
        return [moment(t, RESOLUTION_MAP[self.resolution])]


class minuterange(_datetimerange):
    resolution = 'M'

    def _delta(self, n):
        return timedelta(minutes=n)


class hourrange(_datetimerange):
    resolution = 'H'

    def _delta(self, n):
        return timedelta(hours=n)


class dayrange(_datetimerange):
    resolution = 'd'

    def _delta(self, n):
        return timedelta(days=n)


class weekrange(_datetimerange):
    def _delta(self, n):
        return timedelta(days=n * 7)

    def _suffixes(self, t):
        return dayrange(t, t + timedelta(days=7))
