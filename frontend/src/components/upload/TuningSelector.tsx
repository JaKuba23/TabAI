"use client"

import type { Tuning } from "@/lib/types"
import { TUNING_LABELS } from "@/lib/types"

interface TuningSelectorProps {
  readonly value: Tuning
  readonly onChange: (tuning: Tuning) => void
}

const TUNING_OPTIONS = Object.entries(TUNING_LABELS) as ReadonlyArray<[Tuning, string]>

export default function TuningSelector({ value, onChange }: TuningSelectorProps) {
  return (
    <div className="space-y-1">
      <label htmlFor="tuning-select" className="block text-sm font-medium text-gray-400">
        Guitar Tuning
      </label>
      <select
        id="tuning-select"
        value={value}
        onChange={(e) => onChange(e.target.value as Tuning)}
        className="w-full rounded-lg border border-white/20 bg-white/5 px-4 py-2.5 text-white outline-none transition-colors focus:border-accent"
      >
        {TUNING_OPTIONS.map(([key, label]) => (
          <option key={key} value={key}>
            {label}
          </option>
        ))}
      </select>
    </div>
  )
}
