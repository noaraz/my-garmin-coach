import { createPortal } from 'react-dom'
import type { WorkoutTemplate } from '../../api/types'

interface WorkoutPickerProps {
  templates: WorkoutTemplate[]
  onSchedule: (templateId: number) => void
  onClose: () => void
}

export function WorkoutPicker({ templates, onSchedule, onClose }: WorkoutPickerProps) {
  return createPortal(
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      onClick={e => { if (e.target === e.currentTarget) onClose() }}
    >
      <div
        role="dialog"
        aria-label="Pick a workout"
        aria-modal="true"
        className="bg-white rounded-lg shadow-xl p-6 w-96 max-h-[80vh] overflow-y-auto"
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">Pick a workout</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
            aria-label="Close"
          >
            ✕
          </button>
        </div>
        <ul className="space-y-2">
          {templates.map(template => (
            <li key={template.id}>
              <button
                onClick={() => { onSchedule(template.id); onClose() }}
                className="w-full text-left px-4 py-3 rounded-lg hover:bg-gray-50 border border-gray-200 transition-colors"
              >
                <div className="font-medium text-gray-900">{template.name}</div>
                {template.sport_type && (
                  <div className="text-xs text-gray-500 mt-0.5">{template.sport_type}</div>
                )}
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>,
    document.body
  )
}
