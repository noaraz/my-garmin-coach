# Workout Builder — PLAN

## Description

Visual drag-and-drop structured workout builder — the centerpiece UI.
Athletes create workouts by adding step blocks (warmup, interval, recovery,
cooldown, repeat groups), configuring duration/distance and zone targets,
and arranging them via drag-and-drop. Steps are visualized as colored bars
where height = intensity and width = duration.

Also includes the Workout Library for saving, searching, and reusing templates.

Track progress in **STATUS.md**.

---

## Tasks

### Workout Builder
- [ ] Write all tests in `WorkoutBuilder.test.tsx` (see test table)
- [ ] Run tests → RED
- [ ] Implement `StepTimeline.tsx` + `StepBar.tsx` (display only)
- [ ] Implement `StepPalette.tsx` (add step buttons)
- [ ] Implement `StepConfigPanel.tsx` (step editor)
- [ ] Implement `RepeatGroup.tsx` (visual container)
- [ ] Implement `DurationInput.tsx` + `ZoneSelector.tsx`
- [ ] Implement `WorkoutSummary.tsx` (total duration/distance)
- [ ] Add drag-and-drop with @dnd-kit/core + @dnd-kit/sortable
- [ ] Run tests → GREEN

### Step Config Panel
- [ ] Write all tests in `StepConfigPanel.test.tsx` (see test table)
- [ ] Run tests → RED
- [ ] Implement config panel
- [ ] Run tests → GREEN

### Workout Library
- [ ] Write all tests in `WorkoutLibrary.test.tsx` (see test table)
- [ ] Run tests → RED
- [ ] Implement `WorkoutLibrary.tsx`, `TemplateCard.tsx`, `TemplateSearch.tsx`
- [ ] Add save-to-library and schedule-on-calendar integration
- [ ] Run tests → GREEN

---

## Tests

### WorkoutBuilder.test.tsx

| Test | Scenario |
|------|----------|
| `test_empty_shows_add_prompt` | no steps → "Add a step" |
| `test_add_warmup` | click → appears in timeline |
| `test_add_interval_hr_zone` | add interval, set HR zone 4 |
| `test_add_recovery_open` | add recovery, open target |
| `test_add_cooldown` | appears at end |
| `test_add_repeat_group` | group container shown |
| `test_add_steps_inside_repeat` | interval+recovery inside repeat |
| `test_drag_reorder` | drag step 3 to position 1 |
| `test_delete_step` | click delete → removed |
| `test_bar_height_reflects_zone` | zone 4 taller than zone 1 |
| `test_bar_width_reflects_duration` | 600s wider than 300s |
| `test_bar_color_reflects_zone` | zone 1=blue, zone 5=red |
| `test_total_duration_live` | add steps → total recalculated |
| `test_save_to_library` | click save → POST |
| `test_save_and_schedule` | → POST workout + POST calendar |

### StepConfigPanel.test.tsx

| Test | Scenario |
|------|----------|
| `test_duration_toggle` | time ↔ distance |
| `test_time_input_mm_ss` | "5:00" → 300s |
| `test_distance_input_km` | "1.5" → 1500m |
| `test_target_type_dropdown` | HR zone, Pace zone, Open |
| `test_zone_selector_hr` | zones 1-5 dropdown |
| `test_repeat_count_input` | type 4 |
| `test_notes_field` | text saved |

### WorkoutLibrary.test.tsx

| Test | Scenario |
|------|----------|
| `test_renders_list` | 3 templates → 3 cards |
| `test_search_filters` | "interval" → filtered |
| `test_click_opens_builder` | template → builder with steps |
| `test_schedule_opens_picker` | date picker shown |
| `test_delete` | removed |
| `test_duplicate` | new copy created |

---

## Builder UX Spec

- Timeline: horizontal row of colored bars
- Bar HEIGHT = zone intensity level (1=short, 5=tall)
- Bar WIDTH = duration proportionally
- Click bar → config panel opens below/right
- Step palette = toolbar above timeline
- Repeat groups show bracket/container around children
- Summary panel: total time, distance, zone distribution pie

---

## Implementation Files

```
frontend/src/
  components/builder/ — WorkoutBuilder, StepTimeline, StepBar, StepPalette,
    StepConfigPanel, RepeatGroup, DurationInput, ZoneSelector, WorkoutSummary
  components/library/ — WorkoutLibrary, TemplateCard, TemplateSearch
  pages/ — BuilderPage, LibraryPage
  utils/ — colors.ts, stepDefaults.ts
```
