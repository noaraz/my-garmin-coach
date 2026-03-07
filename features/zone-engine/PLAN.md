# Zone Engine — PLAN

## Description

The mathematical core of the platform. Calculates HR and pace training zones
from threshold values using standard methodologies (Coggan, Friel, Daniels).
When a threshold changes, all zones recalculate automatically.

Pure functions with zero I/O — no database, no API, no file reads.

Track progress in **STATUS.md**.

---

## Tasks

- [ ] Write `zone_engine/models.py` — Zone, ZoneConfig, ZoneSet dataclasses
- [ ] Write all tests in `test_hr_zones.py` (see test table below)
- [ ] Run tests → confirm all RED
- [ ] Implement `zone_engine/hr_zones.py` — HRZoneCalculator
- [ ] Run tests → confirm all GREEN
- [ ] Write all tests in `test_pace_zones.py` (see test table below)
- [ ] Run tests → confirm all RED
- [ ] Implement `zone_engine/pace_zones.py` — PaceZoneCalculator
- [ ] Run tests → confirm all GREEN
- [ ] Write `zone_engine/constants.py` — percentage tables
- [ ] Run `pytest tests/unit/ -v --cov=src/zone_engine` → verify >95% coverage

---

## Data Model

### Zone
```
zone_number     int (1-5)
name            str ("Easy", "Aerobic", "Tempo", "Threshold", "VO2max")
lower           float (bpm or sec/km)
upper           float
pct_lower       float (for recalculation)
pct_upper       float
```

### ZoneConfig
```
threshold       float (LTHR or threshold_pace)
max_value       float (max_hr, optional)
resting_value   float (resting_hr, optional)
method          str ("coggan", "friel", "daniels", "pct_max_hr", "pct_hrr", "custom")
```

---

## Tests

### test_hr_zones.py

| Test | Given | Expect |
|------|-------|--------|
| `test_from_lthr_coggan` | LTHR=170, method=coggan | 5 zones with Coggan % boundaries |
| `test_from_max_hr` | maxHR=190, method=pct_max_hr | 5 zones as % of max HR |
| `test_from_hrr_karvonen` | maxHR=190, restHR=48, method=pct_hrr | 5 zones Karvonen |
| `test_custom` | explicit bpm boundaries | stored as-is |
| `test_recalculate_on_lthr_change` | LTHR 170→175 | all 5 zones shift |
| `test_lookup_by_number` | zones 1-5 | zone 3 correct |
| `test_rejects_zero_lthr` | LTHR=0 | ValidationError |
| `test_rejects_negative` | LTHR=-5 | ValidationError |
| `test_rejects_out_of_range` | zone_number=6 | ValidationError |

### test_pace_zones.py

| Test | Given | Expect |
|------|-------|--------|
| `test_from_threshold` | 270s/km, method=pct_threshold | 5 zones correct |
| `test_custom` | explicit boundaries | stored as-is |
| `test_recalculate_on_change` | threshold 270→265 | all zones shift |
| `test_slower_means_higher_seconds` | zone 1 vs zone 5 | zone 1 higher sec/km |
| `test_rejects_zero` | threshold=0 | ValidationError |
| `test_formatting_helper` | 270 sec/km | "4:30" string |

---

## Implementation Files

```
backend/src/zone_engine/
  __init__.py
  models.py        # Zone, ZoneSet, ZoneConfig
  hr_zones.py      # HRZoneCalculator
  pace_zones.py    # PaceZoneCalculator
  constants.py     # percentage tables (Coggan, Friel, Daniels)
  exceptions.py    # ZoneValidationError
```
