# Zone Engine — CLAUDE

## Zone Percentage Constants

HR Zones (Coggan, % of LTHR):
```
Zone 1 (Active Recovery): < 68%
Zone 2 (Aerobic):         69-83%
Zone 3 (Tempo):           84-94%
Zone 4 (Threshold):       95-105%
Zone 5 (VO2max):          > 106%
```

HR Zones (Friel, 5-zone, % of LTHR):
```
Zone 1: 0-81%    Zone 2: 82-89%    Zone 3: 90-93%
Zone 4: 94-99%   Zone 5: 100-110%
```

Pace Zones (Daniels-style, % of threshold speed):
```
Zone 1 (Easy):      70-79%    (= 127-141% of threshold pace)
Zone 2 (Moderate):  80-87%
Zone 3 (Tempo):     88-95%
Zone 4 (Threshold): 96-103%
Zone 5 (Interval):  104-115%
```

## Gotchas

- **Pace direction**: Slower pace = HIGHER sec/km. Zone 1 (recovery) has
  higher sec/km than Zone 5 (interval). Don't confuse lower/upper.
- **Pace formatting**: 270 sec/km → "4:30". Use `divmod(seconds, 60)`.
