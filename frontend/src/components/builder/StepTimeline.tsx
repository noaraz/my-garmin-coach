import {
  DndContext,
  PointerSensor,
  KeyboardSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core'
import {
  SortableContext,
  sortableKeyboardCoordinates,
  horizontalListSortingStrategy,
  arrayMove,
} from '@dnd-kit/sortable'
import type { BuilderStep, RepeatGroup as RepeatGroupType, WorkoutStep } from '../../api/types'
import { StepBar } from './StepBar'
import { RepeatGroup } from './RepeatGroup'

interface StepTimelineProps {
  steps: BuilderStep[]
  selectedId?: string | null
  onDelete: (index: number) => void
  onStepChange: (index: number, step: BuilderStep) => void
  onSelectStep: (index: number) => void
  onReorder: (oldIndex: number, newIndex: number) => void
}

function isRepeatGroup(step: BuilderStep): step is RepeatGroupType {
  return step.type === 'repeat'
}

export function StepTimeline({ steps, selectedId, onDelete, onStepChange, onSelectStep, onReorder }: StepTimelineProps) {
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  )

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event
    if (over && active.id !== over.id) {
      const oldIndex = steps.findIndex((s) => s.id === active.id)
      const newIndex = steps.findIndex((s) => s.id === over.id)
      if (oldIndex !== -1 && newIndex !== -1) {
        onReorder(oldIndex, newIndex)
      }
    }
  }

  if (steps.length === 0) {
    return (
      <div style={{
        color: 'var(--text-muted)',
        fontSize: '11px',
        fontFamily: "'Barlow Condensed', system-ui, sans-serif",
        letterSpacing: '0.08em',
        padding: '32px',
        textAlign: 'center',
        textTransform: 'uppercase',
      }}>
        Add a step to get started
      </div>
    )
  }

  return (
    <DndContext sensors={sensors} onDragEnd={handleDragEnd}>
      <SortableContext items={steps.map((s) => s.id)} strategy={horizontalListSortingStrategy}>
        <div style={{
          display: 'flex',
          gap: '8px',
          alignItems: 'flex-end',
          flexWrap: 'wrap',
          padding: '20px 18px 12px',
          minHeight: '120px',
        }}>
          {steps.map((step, index) => {
            if (isRepeatGroup(step)) {
              return (
                <RepeatGroup
                  key={step.id}
                  group={step}
                  groupIndex={index}
                  isSelected={selectedId === step.id}
                  onChange={(updated) => onStepChange(index, updated)}
                  onDelete={() => onDelete(index)}
                  onSelect={() => onSelectStep(index)}
                />
              )
            }
            return (
              <StepBar
                key={step.id}
                step={step as WorkoutStep}
                index={index}
                isSelected={selectedId === step.id}
                onDelete={() => onDelete(index)}
                onClick={() => onSelectStep(index)}
              />
            )
          })}
        </div>
      </SortableContext>
    </DndContext>
  )
}

export { arrayMove }
