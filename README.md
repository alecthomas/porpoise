# Porpoise - A Redis-based analytics framework

Porpoise implements two analytics primitives: counters and events.


## Recording events

The following example records that two users (ids 1 and 2) were active at the current time:

```python
from porpoise import Analytics

porpoise.event('active', 1)
porpoise.event('active', 2)
```


### Recording counters

A couple of examples of incrementing counters:

```python
porpoise.count('signups')
analytics.count('song:played', song.id)
```
