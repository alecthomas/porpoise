# Porpoise - A Redis-based analytics framework

Porpoise implements two analytics primitives: counters and events.


## Recording

### Events

The following example records that two users (ids 1 and 2) were active at the
current time, and user 1 played a song:

```python
from porpoise import Analytics

porpoise = Analytics()

porpoise.event('active', 1)
porpoise.event('active', 2)
porpoise.event('login', 1)
porpoise.event('song:played', 1)
```


### Counters

A couple of examples of incrementing counters:

```python
porpoise.count('signups', 'all')
porpoise.count('song:played', song.id)
```

## Analysis

There are two steps to analysing Porpoise data:

1. Specify time ranges to analyse.
2. Specify which metrics to analyse.

### Time ranges

Porpoise exposes a set of classes that make dealing with time ranges more
convenient: `{minute,hour,day,week,month}range`.

Each class accepts a start and end time. These times can be specified as
negative offsets from the current time, in the base unit (day, week, etc.):

```python
last_24_hours = hourrange(-24)
last_four_days = dayrange(-4)
last_seven_days = weekrange(-1)
previous_week = weekrange(-2, -1)
```

They can also be specified as absolute datetime start/end times:

```python
first_seven_days_of_2010 = dayrange(datetime(2010, 1, 1), datetime(2010, 1, 8))
```

### Analysing events

Queries across multiple events can be expressed as bit-wise expressions. For
example, to find all users who logged in and played a song in the same hour:

```python
events = porpoise.events
loggedin_and_played = events('login') & events('song:played')
for users in loggedin_and_played(last_24_hours):
  print users
```


### Analysing counters

Each counter key has a number of IDs associated with it. When analysing
counters, the returned data is a dictionary mapping these IDs to their count.

For example, to print the top 10 songs played in each hour for the last 24 hours:

```python
counters = porpoise.counters

songs_played = counters('song:played')

for songs in songs_played(last_24_hours):
  top10 = sorted(songs.iteritems(), lambda s: -s[1])[:5]
  for song, played in top10:
    print song, played
```
