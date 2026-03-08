interface ThresholdInputProps {
  lthr: number | null
  thresholdPace: number | null
  onLthrChange: (val: number) => void
  onThresholdPaceChange: (val: number) => void
  onSave: () => void
}

export function ThresholdInput({
  lthr,
  thresholdPace,
  onLthrChange,
  onThresholdPaceChange,
  onSave,
}: ThresholdInputProps) {
  return (
    <div className="flex flex-wrap items-end gap-4">
      <div className="flex flex-col gap-1">
        <label htmlFor="lthr" className="text-sm font-medium text-gray-700">
          LTHR
        </label>
        <input
          id="lthr"
          type="number"
          value={lthr ?? ''}
          onChange={e => onLthrChange(Number(e.target.value))}
          className="border border-gray-300 rounded px-2 py-1 w-24 font-mono"
          placeholder="bpm"
        />
      </div>
      <div className="flex flex-col gap-1">
        <label htmlFor="threshold-pace" className="text-sm font-medium text-gray-700">
          Threshold Pace (sec/km)
        </label>
        <input
          id="threshold-pace"
          type="number"
          value={thresholdPace ?? ''}
          onChange={e => onThresholdPaceChange(Number(e.target.value))}
          className="border border-gray-300 rounded px-2 py-1 w-24 font-mono"
          placeholder="sec/km"
        />
      </div>
      <button
        onClick={onSave}
        className="px-4 py-1.5 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm font-medium"
      >
        Save
      </button>
    </div>
  )
}
