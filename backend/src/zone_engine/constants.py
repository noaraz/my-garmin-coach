from __future__ import annotations

# Coggan HR zone percentages of LTHR
# Each tuple is (pct_lower, pct_upper)
COGGAN_HR_ZONES: list[tuple[float, float]] = [
    (0.00, 0.68),   # Zone 1: Active Recovery — < 68%
    (0.68, 0.83),   # Zone 2: Aerobic — 68–83%
    (0.83, 0.94),   # Zone 3: Tempo — 83–94%
    (0.94, 1.05),   # Zone 4: Threshold — 94–105%
    (1.05, 1.21),   # Zone 5: VO2max — 105–121%
]

COGGAN_HR_ZONE_NAMES: list[str] = [
    "Active Recovery",
    "Aerobic",
    "Tempo",
    "Threshold",
    "VO2max",
]

# Friel HR zone percentages of LTHR
FRIEL_HR_ZONES: list[tuple[float, float]] = [
    (0.00, 0.81),   # Zone 1
    (0.82, 0.89),   # Zone 2
    (0.90, 0.93),   # Zone 3
    (0.94, 0.99),   # Zone 4
    (1.00, 1.10),   # Zone 5
]

FRIEL_HR_ZONE_NAMES: list[str] = [
    "Zone 1",
    "Zone 2",
    "Zone 3",
    "Zone 4",
    "Zone 5",
]

# Max HR zone percentages
# Each tuple is (pct_lower, pct_upper)
PCT_MAX_HR_ZONES: list[tuple[float, float]] = [
    (0.50, 0.60),   # Zone 1
    (0.60, 0.70),   # Zone 2
    (0.70, 0.80),   # Zone 3
    (0.80, 0.90),   # Zone 4
    (0.90, 1.00),   # Zone 5
]

PCT_MAX_HR_ZONE_NAMES: list[str] = [
    "Zone 1",
    "Zone 2",
    "Zone 3",
    "Zone 4",
    "Zone 5",
]

# Karvonen (% HRR) zone percentages applied to heart rate reserve
PCT_HRR_ZONES: list[tuple[float, float]] = [
    (0.50, 0.60),   # Zone 1
    (0.60, 0.70),   # Zone 2
    (0.70, 0.80),   # Zone 3
    (0.80, 0.90),   # Zone 4
    (0.90, 1.00),   # Zone 5
]

PCT_HRR_ZONE_NAMES: list[str] = [
    "Zone 1",
    "Zone 2",
    "Zone 3",
    "Zone 4",
    "Zone 5",
]

# Daniels-style pace zone percentages of threshold pace (sec/km)
# Higher percentage = slower pace = higher sec/km
# Each tuple is (pct_lower, pct_upper) where lower = slower boundary, upper = faster boundary
DANIELS_PACE_ZONES: list[tuple[float, float]] = [
    (1.29, 1.14),   # Zone 1: Easy — 129–114% of threshold pace
    (1.14, 1.06),   # Zone 2: Moderate — 114–106%
    (1.06, 1.00),   # Zone 3: Tempo — 106–100%
    (1.00, 0.97),   # Zone 4: Threshold — 100–97%
    (0.97, 0.90),   # Zone 5: Interval — 97–90%
]

DANIELS_PACE_ZONE_NAMES: list[str] = [
    "Easy",
    "Moderate",
    "Tempo",
    "Threshold",
    "Interval",
]
