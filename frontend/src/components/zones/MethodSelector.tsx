interface MethodSelectorProps {
  value: string
  onChange: (method: string) => void
}

export function MethodSelector({ value, onChange }: MethodSelectorProps) {
  return (
    <div className="flex items-center gap-2">
      <label htmlFor="method-select" className="text-sm font-medium text-gray-700">
        Method
      </label>
      <select
        id="method-select"
        role="combobox"
        aria-label="Method"
        value={value}
        onChange={e => onChange(e.target.value)}
        className="border border-gray-300 rounded px-2 py-1 text-sm"
      >
        <option value="coggan">Coggan</option>
        <option value="friel">Friel</option>
        <option value="daniels">Daniels</option>
        <option value="custom">Custom</option>
      </select>
    </div>
  )
}
